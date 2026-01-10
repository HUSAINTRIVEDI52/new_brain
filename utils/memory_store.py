from collections import deque
import math
import datetime
import faiss
import numpy as np
import logging
import asyncio
from typing import List, Optional, Dict, Any, Literal
from utils.db import supabase
from utils.logger import log_event
from utils.vector_store import get_vector_store
from utils.cache import cache_manager

logger = logging.getLogger(__name__)

class MemoryStore:
    def __init__(self, dimension: int = 1536, max_cached_users: int = 100):
        self.dimension = dimension
        self.vector_store = get_vector_store(dimension)
        self.max_cached_users = max_cached_users
        
        # User-partitioned storage (Lazy Loaded)
        self.user_records: Dict[str, List[Dict[str, Any]]] = {}
        self.user_record_maps: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self.user_query_history: Dict[str, deque] = {}
        
        # Memory Management: Track last access for LRU eviction
        self.user_last_active: Dict[str, datetime.datetime] = {}

    async def _ensure_user_hydrated(self, user_id: str):
        """
        Loads user data from DB only if not already in memory.
        Implements LRU eviction if max_cached_users is reached.
        """
        self.user_last_active[user_id] = datetime.datetime.now(datetime.timezone.utc)
        
        if user_id in self.user_records:
            return

        # 1. LRU Eviction Check
        if len(self.user_records) >= self.max_cached_users:
            # Evict the least recently used user
            lru_user = min(self.user_last_active, key=self.user_last_active.get)
            if lru_user != user_id:
                logger.info(f"OOM Prevention: Evicting data for inactive user {lru_user}")
                self.user_records.pop(lru_user, None)
                self.user_record_maps.pop(lru_user, None)
                self.user_query_history.pop(lru_user, None)
                self.user_last_active.pop(lru_user, None)
                cache_manager.invalidate_user_semantic(lru_user)

        # 2. Hydrate User from DB
        try:
            log_event(logging.INFO, "user_hydration_started", "Hydrating specific user", user_id=user_id)
            response = supabase.table("memories").select("*").eq("user_id", user_id).execute()
            
            self.user_records[user_id] = []
            self.user_record_maps[user_id] = {}
            self.user_query_history[user_id] = deque(maxlen=20)

            if response.data:
                embeddings = []
                ids = []
                for record in response.data:
                    emb = record.get("embedding")
                    if emb and isinstance(emb, list) and len(emb) == self.dimension:
                        embeddings.append(emb)
                        ids.append(record["id"])
                        
                        # Cache record locally
                        self.user_records[user_id].append(record)
                        self.user_record_maps[user_id][record["id"]] = record

                if embeddings:
                    # Non-blocking add to vector store (bridge handles sync/async internally)
                    await self.vector_store.add_vectors(user_id, embeddings, ids)
                
                log_event(logging.INFO, "user_hydration_completed", f"Loaded {len(response.data)} memories", user_id=user_id)
            else:
                log_event(logging.INFO, "user_hydration_empty", "New user initialized with empty brain", user_id=user_id)
        except Exception as e:
            log_event(logging.ERROR, "user_hydration_failed", str(e), user_id=user_id, status="error")

    def _calculate_effective_importance(self, record: Dict[str, Any], user_id: str) -> float:
        try:
            # Signal 1: Access Frequency (Logarithmic scale)
            access_count = record.get("access_count", 0)
            freq_score = min(1.0, math.log1p(access_count) / 4.0) 
            
            # Signal 2: AI Summary Inclusion (Linear scale)
            summary_count = record.get("summary_count", 0)
            ai_score = min(1.0, summary_count / 5.0)

            # Signal 3: Semantic Reuse (Contextual relevance to recent history)
            history = self.user_query_history.get(user_id, [])
            relevance_score = 0.0
            if history and "embedding" in record:
                mem_emb = np.array(record["embedding"]).astype('float32')
                # Check similarity against last 10 queries
                recent_history = list(history)[-10:]
                similarities = []
                for q_emb in recent_history:
                    # Euclidean distance to similarity (steeper decay for precision)
                    dist = np.linalg.norm(mem_emb - q_emb)
                    similarities.append(math.exp(-1.5 * dist))
                relevance_score = sum(similarities) / len(similarities)

            # Combination: Balanced weight with high priority on semantic reuse
            # 25% Freq + 35% AI + 40% Reuse
            combined = (0.25 * freq_score + 0.35 * ai_score + 0.40 * relevance_score)
            
            # Base importance multiplier (provided by user/system on creation)
            base_imp = record.get("importance", 1.0) 
            final_imp = max(0.0, min(1.0, combined * base_imp))
            
            return round(final_imp, 3)
        except Exception as e:
            logger.error(f"Error calculating dynamic importance: {e}")
            return record.get("importance", 0.1)

    def _invalidate_user_cache(self, user_id: str):
        cache_manager.invalidate_user_semantic(user_id)

    def _calculate_retention_score(self, record: Dict[str, Any], now: Optional[datetime.datetime] = None) -> float:
        try:
            created_at = datetime.datetime.fromisoformat(record["created_at"])
            last_accessed = datetime.datetime.fromisoformat(record.get("last_accessed_at", record["created_at"]))
            
            if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=datetime.timezone.utc)
            if last_accessed.tzinfo is None: last_accessed = last_accessed.replace(tzinfo=datetime.timezone.utc)
            
            if now is None:
                now = datetime.datetime.now(datetime.timezone.utc)
            elif now.tzinfo is None:
                now = now.replace(tzinfo=datetime.timezone.utc)
                
            t_last_access = max(0, (now - last_accessed).total_seconds() / (24 * 3600))
            t_total = max(0, (now - created_at).total_seconds() / (24 * 3600))
            
            importance = record.get("importance", 1.0)
            access_count = record.get("access_count", 0)
            
            # Strength reinforced by accesses (Logarithmic gain)
            # Higher importance leads to significantly stronger base and slower decay
            strength = importance * (1.0 + math.log(access_count + 1) * 0.5)
            
            # Decay rate: base decay (0.05) reduced by memory strength
            # A strength of 1.0 (importance 1, count 0) gives a half-life of ~14 days
            decay_rate = 0.05 / strength
            
            # Retention combines short-term decay (since last access) 
            # and a very slow long-term decay (since creation)
            short_term = math.exp(-decay_rate * t_last_access)
            long_term = math.exp(-0.005 * t_total / importance)
            
            return short_term * long_term
        except Exception as e:
            logger.error(f"Error calculating retention: {e}")
            return 1.0

    def _calculate_memory_state(self, record: Dict[str, Any], now: Optional[datetime.datetime] = None) -> Literal["strong", "fading", "resurfaced"]:
        retention = self._calculate_retention_score(record, now)
        if retention > 0.7: return "strong"
        return "fading"

    async def _update_access_metrics(self, record: Dict[str, Any], now: Optional[datetime.datetime] = None) -> str:
        user_id = record["user_id"]
        memory_id = record["id"]
        
        # Determine state BEFORE update
        old_state = self._calculate_memory_state(record, now=now)
        
        new_count = record.get("access_count", 0) + 1
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        new_last_access = now.isoformat()
        
        try:
            supabase.table("memories").update({
                "access_count": new_count,
                "last_accessed_at": new_last_access
            }).eq("id", memory_id).eq("user_id", user_id).execute()
        except Exception as e:
            logger.error(f"Failed to update access metrics in DB: {e}")

        record["access_count"] = new_count
        record["last_accessed_at"] = new_last_access
        
        # Cache metadata update
        cache_manager.set_metadata(user_id, memory_id, record)
        self._invalidate_user_cache(user_id)
        
        # Return resurfaced if it was fading, else strong
        return "resurfaced" if old_state == "fading" else "strong"

    async def increment_summary_counts(self, memory_ids: List[int], user_id: str):
        """
        Increments summary_count for memories used in RAG summaries.
        """
        if not memory_ids: return
        try:
            # Update in Supabase
            # We use RPC or raw query if increment is not available directly
            # For simplicity with the current setup, we'll fetch and update or use an RPC if available.
            # Here we'll do individual updates in a gather for now, 
            # or better: we'll just update the local records and trigger a deferred sync if needed.
            # Since we want durability, let's do a batch update if possible.
            
            # Note: Supabase/PostgREST doesn't support easy "increment" without RPC.
            # We'll fetch current counts and update them in batch.
            res = supabase.table("memories").select("id", "summary_count").in_("id", memory_ids).eq("user_id", user_id).execute()
            if res.data:
                updates = []
                for rec in res.data:
                    new_val = (rec.get("summary_count") or 0) + 1
                    updates.append(
                        supabase.table("memories").update({"summary_count": new_val}).eq("id", rec["id"]).execute()
                    )
                    # Update local cache
                    if user_id in self.user_record_maps and rec["id"] in self.user_record_maps[user_id]:
                        self.user_record_maps[user_id][rec["id"]]["summary_count"] = new_val
                
                if updates:
                    await asyncio.gather(*[asyncio.to_thread(lambda: u) for u in []]) # Updates already executed synchronously in loop above
            
            self._invalidate_user_cache(user_id)
        except Exception as e:
            logger.error(f"Failed to increment summary counts: {e}")

    async def add_memory(self, content: str, user_id: str, summary: str, embedding: List[float], importance: float = 1.0, metadata: Optional[Dict[str, Any]] = None, summary_count: int = 0) -> Dict[str, Any]:
        await self._ensure_user_hydrated(user_id)
        if not content or not content.strip(): raise ValueError("Memory content cannot be empty")
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            data = {
                "user_id": user_id, "raw_text": content, "summary": summary,
                "embedding": embedding, "importance": importance, "summary_count": summary_count,
                "created_at": now, "last_accessed_at": now, "access_count": 0,
                "metadata": metadata or {}
            }
            response = supabase.table("memories").insert(data).execute()
            if not response.data: raise Exception("Supabase insert failed")
            new_record = response.data[0]
            await self.vector_store.add_vectors(user_id, [embedding], [new_record['id']])
            
            self.user_records[user_id].append(new_record)
            self.user_record_maps[user_id][new_record['id']] = new_record
            self._invalidate_user_cache(user_id)
            return new_record
        except Exception as e:
            log_event(logging.ERROR, "memory_add_failed", f"Error adding memory: {str(e)}", user_id=user_id, status="error")
            raise

    async def search(self, query_text: str, query_embedding: List[float], user_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        await self._ensure_user_hydrated(user_id)
        
        # Defensive initialization for robustness
        if user_id not in self.user_query_history:
            self.user_query_history[user_id] = deque(maxlen=20)
            
        self.user_query_history[user_id].append(np.array(query_embedding).astype('float32'))
        
        cached_results = cache_manager.get_semantic(user_id, query_text, top_k)
        if cached_results:
            log_event(logging.INFO, "cache_hit_search", "Semantic cache hit during search", user_id=user_id, cache_hit=True)
            return cached_results

        search_results = await self.vector_store.search_vectors(user_id, query_embedding, top_k * 3)
        if not search_results: return []

        # 3. Resolve records (Batch DB calls for cache misses)
        candidate_ids = [res[0] for res in search_results]
        missing_ids = [cid for cid in candidate_ids if cid not in self.user_record_maps.get(user_id, {})]
        
        if missing_ids:
            try:
                res = supabase.table("memories").select("*").in_("id", missing_ids).execute()
                if res.data:
                    for rec in res.data:
                        self.user_record_maps.setdefault(user_id, {})[rec["id"]] = rec
            except Exception as e:
                logger.error(f"Batch record resolution failed: {e}")

        scored_results = []
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 4. Contextual Parameter Tuning
        # Recency bias boost if query has temporal intent
        temporal_keywords = ["recent", "newest", "latest", "today", "yesterday", "week", "month"]
        temporal_boost = any(kw in query_text.lower() for kw in temporal_keywords)
        recency_weight = 0.8 if temporal_boost else 0.5
        
        # Semantic Cut-off (Reduce false positives)
        # FAISS Euclidean distance: lower is better. 1.0 is very distant.
        # 0.3-0.4 is usually a decent cut-off for 'related'.
        SEMANTIC_THRESHOLD = 0.45 

        for mem_id, dist in search_results:
            if dist > SEMANTIC_THRESHOLD:
                continue # Skip weak matches (False Positives)

            memory = self.user_record_maps.get(user_id, {}).get(mem_id)
            if not memory: continue
            
            # --- Signal 1: Semantic (Distance to Score) ---
            semantic_sim = 1.0 / (1.0 + float(dist))
            
            # --- Signal 2: Importance ---
            eff_imp = self._calculate_effective_importance(memory, user_id)
            
            # --- Signal 3: Recency ---
            created_at = datetime.datetime.fromisoformat(memory["created_at"])
            if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=datetime.timezone.utc)
            age_days = max(0, (now - created_at).total_seconds() / (24 * 3600))
            recency_score = 1.0 / (1.0 + (age_days / 30.0))
            
            # --- Signal 4: Retention (Forgetting Curve) ---
            ret_score = self._calculate_retention_score(memory, now=now)
            
            # --- Unified Hybrid Formula ---
            master_score = (
                (semantic_sim ** 1.5) * 
                (1.0 + (0.2 * eff_imp)) * 
                (1.0 + (recency_weight * recency_score)) * 
                (1.0 + (0.15 * (1.0 - ret_score)))
            )
            
            scored_results.append({
                "record": memory, 
                "internal_score": master_score, 
                "importance_val": eff_imp
            })
        
        # Sort by master_score descending (higher is better)
        scored_results.sort(key=lambda x: x["internal_score"], reverse=True)
        top_candidates = scored_results[:top_k]

        # Calculate max possible score in this set for normalization
        max_score = scored_results[0]["internal_score"] if scored_results else 1.0

        # 4. Parallel Metric Updates & Formatting
        async def _process_result(item):
            memory = item["record"]
            state = await self._update_access_metrics(memory)
            result = memory.copy()
            result["memory_state"] = state
            result["importance"] = item["importance_val"]
            
            # Normalize relevance to 0.0 - 1.0
            relevance = min(1.0, item["internal_score"] / max_score) if max_score > 0 else 0.0
            
            if "metadata" not in result: result["metadata"] = {}
            result["metadata"]["relevance"] = round(relevance, 3)
            return result

        results = await asyncio.gather(*[_process_result(item) for item in top_candidates])
        
        cache_manager.set_semantic(user_id, query_text, top_k, results)
        return results

    async def get_memory(self, memory_id: int, user_id: str, now: Optional[datetime.datetime] = None) -> Optional[Dict[str, Any]]:
        await self._ensure_user_hydrated(user_id)
        record = self.user_record_maps.get(user_id, {}).get(memory_id)
        if not record:
            res = supabase.table("memories").select("*").eq("id", memory_id).eq("user_id", user_id).execute()
            if res.data:
                record = res.data[0]
                self.user_record_maps[user_id][memory_id] = record
        if record:
            state = await self._update_access_metrics(record, now=now)
            result = record.copy()
            result["memory_state"] = state
            return result
        return None

    async def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        await self._ensure_user_hydrated(user_id)
        records = self.user_records.get(user_id, [])
        return [{**r.copy(), "memory_state": self._calculate_memory_state(r)} for r in records]

    async def delete_memory(self, memory_id: int, user_id: str) -> bool:
        await self._ensure_user_hydrated(user_id)
        if memory_id in self.user_record_maps.get(user_id, {}):
            try:
                # 1. Delete from DB
                supabase.table("memories").delete().eq("id", memory_id).eq("user_id", user_id).execute()
                
                # 2. Local Cleanup
                record = self.user_record_maps[user_id][memory_id]
                self.user_records[user_id].remove(record)
                del self.user_record_maps[user_id][memory_id]
                
                self._invalidate_user_cache(user_id)
                return True
            except Exception as e:
                logger.error(f"Failed to delete memory {memory_id}: {e}")
                return False
        return False

    async def update_memory(self, memory_id: int, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await self._ensure_user_hydrated(user_id)
        if memory_id in self.user_record_maps.get(user_id, {}):
            try:
                # 1. Update DB
                supabase.table("memories").update(updates).eq("id", memory_id).eq("user_id", user_id).execute()
                
                # 2. Sync local record
                record = self.user_record_maps[user_id][memory_id]
                for k, v in updates.items():
                    record[k] = v
                
                if "content" in updates:
                    record["raw_text"] = updates["content"]
                
                self._invalidate_user_cache(user_id)
                return {**record, "memory_state": self._calculate_memory_state(record)}
            except Exception as e:
                logger.error(f"Failed to update memory {memory_id}: {e}")
                return None
        return None

memory_store = MemoryStore()
