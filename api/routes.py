import asyncio
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from models.schemas import MemoryCreate, Memory, MemoryUpdate, QueryRequest, QueryResponse
from api.deps import get_current_user
from utils.memory_store import memory_store
from utils.ai import ai_client
from utils.cache import cache_manager
from utils.logger import log_event
import logging
import time

router = APIRouter()

@router.post("/upload", response_model=Memory, status_code=status.HTTP_201_CREATED)
async def upload_memory(memory: MemoryCreate, user_id: str = Depends(get_current_user)):
    """
    Uploads a memory, generates summary/embedding in parallel, and persists to DB.
    """
    start_time = time.time()
    if not memory.content.strip():
        log_event(logging.WARNING, "upload_rejected", "Empty memory content", user_id=user_id, status="bad_request")
        raise HTTPException(status_code=400, detail="Memory content cannot be empty")

    try:
        
        # Parallelize AI tasks for performance
        embedding_task = ai_client.get_embedding(memory.content)
        summary_task = ai_client.summarize_text(memory.content)
        topics_task = ai_client.extract_topics(memory.content)
        
        embedding, summary, extracted_topics = await asyncio.gather(
            embedding_task, summary_task, topics_task
        )
        
        # Merge extracted topics with any provided metadata topics
        final_topics = sorted(list(set((memory.metadata or {}).get("topics", []) + extracted_topics)))
        
        new_record = await memory_store.add_memory(
            content=memory.content,
            user_id=user_id,
            summary=summary,
            embedding=embedding,
            importance=memory.importance or 1.0,
            metadata={**(memory.metadata or {}), "topics": final_topics},
            summary_count=1
        )
        
        duration = int((time.time() - start_time) * 1000)
        log_event(logging.INFO, "memory_uploaded", "Successfully uploaded memory", user_id=user_id, duration_ms=duration, status="success")
        
        return Memory(
            id=new_record['id'],
            content=new_record['raw_text'],
            summary=summary,
            memory_state=new_record.get('memory_state', 'strong'),
            importance=new_record.get('importance', 1.0),
            created_at=new_record['created_at'],
            topics=final_topics,
            metadata=memory.metadata
        )
    except ValueError as ve:
        log_event(logging.WARNING, "upload_failed", str(ve), user_id=user_id, status="error")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        log_event(logging.ERROR, "upload_error", "Internal upload failure", user_id=user_id, status="error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while uploading your memory. Please try again later."
        )

@router.post("/query", response_model=QueryResponse)
async def query_memories(query: QueryRequest, user_id: str = Depends(get_current_user)):
    """
    Performs semantic search and optionally generates a RAG summary.
    """
    start_time = time.time()
    if not query.query.strip():
        log_event(logging.INFO, "query_empty", "Empty search query", user_id=user_id)
        return QueryResponse(results=[], summary="Please provide a search query.")

    try:
        # 0. Upstream Cache Check (Skip AI if repeated query)
        cached_results = cache_manager.get_semantic(user_id, query.query, query.top_k)
        
        if cached_results and not query.include_summary:
            log_event(logging.INFO, "query_cache_fast_path", "Bypassed AI via upstream cache", user_id=user_id, cache_hit=True)
            return QueryResponse(results=cached_results, summary=None)

        # 1. Refine Query (Expansion for abstract search)
        refined_query = await ai_client.refine_query(query.query)
        if refined_query != query.query:
            log_event(logging.INFO, "query_refined", f"Expanded query: {refined_query}", user_id=user_id)

        # 2. Generate Query Embedding
        ai_start = time.time()
        query_embedding = await ai_client.get_embedding(refined_query)
        ai_duration = int((time.time() - ai_start) * 1000)
        
        # 3. Perform Semantic Search
        search_start = time.time()
        results = await memory_store.search(
            query_text=query.query,
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=query.top_k
        )
        search_duration = int((time.time() - search_start) * 1000)
        
        memory_results = [
            Memory(
                id=record['id'],
                content=record['raw_text'],
                summary=record.get('summary', ''),
                memory_state=record.get('memory_state', 'strong'),
                importance=record.get('importance', 1.0),
                created_at=record['created_at'],
                topics=record.get('metadata', {}).get('topics', []),
                metadata=record.get('metadata', {})
            ) for record in results
        ]
        
        # 4. Generate RAG Summary if requested
        summary = None
        rag_duration = 0
        if query.include_summary and memory_results:
            rag_start = time.time()
            memory_texts = [m.content for m in memory_results]
            summary = await ai_client.generate_search_summary(query.query, memory_texts)
            rag_duration = int((time.time() - rag_start) * 1000)
            
            # Record summary usage for dynamic importance
            memory_ids = [m.id for m in memory_results]
            asyncio.create_task(memory_store.increment_summary_counts(memory_ids, user_id))
            
        total_duration = int((time.time() - start_time) * 1000)
        log_event(logging.INFO, "query_completed", "Search completed", 
                  user_id=user_id, 
                  duration_ms=total_duration,
                  ai_ms=ai_duration,
                  search_ms=search_duration,
                  rag_ms=rag_duration,
                  top_k=query.top_k, 
                  status="success")
        
        return QueryResponse(
            results=memory_results,
            summary=summary
        )
    except Exception as e:
        log_event(logging.ERROR, "query_error", f"Search failure: {str(e)}", user_id=user_id, status="error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve memories. Our search system is having a temporary issue."
        )

@router.get("/memory/{memory_id}", response_model=Memory)
async def get_memory(memory_id: int, user_id: str = Depends(get_current_user)):
    """
    Retrieves a single memory by ID.
    """
    try:
        record = await memory_store.get_memory(memory_id, user_id)
        if not record:
            log_event(logging.INFO, "memory_not_found", "Memory ID not found", user_id=user_id, status="404")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Memory not found"
            )
        
        log_event(logging.INFO, "memory_retrieved", "Retrieved single memory", user_id=user_id, status="success")
        return Memory(
            id=record['id'],
            content=record['raw_text'],
            summary=record.get('summary', ''),
            memory_state=record.get('memory_state', 'strong'),
            importance=record.get('importance', 1.0),
            created_at=record['created_at'],
            topics=record.get('metadata', {}).get('topics', []),
            metadata=record.get('metadata', {})
        )
    except HTTPException:
        raise
    except Exception as e:
        log_event(logging.ERROR, "memory_get_error", str(e), user_id=user_id, status="error")
        raise HTTPException(status_code=500, detail="Could not retrieve the requested memory.")

@router.get("/memories", response_model=List[Memory])
async def get_all_memories(user_id: str = Depends(get_current_user)):
    """
    Lists all memories for the authenticated user.
    """
    try:
        records = memory_store.get_all_memories(user_id)
        log_event(logging.INFO, "memories_listed", "Listed all memories", user_id=user_id, memories_count=len(records), status="success")
        
        return [
            Memory(
                id=record['id'],
                content=record['raw_text'],
                summary=record.get('summary', ''),
                memory_state=record.get('memory_state', 'strong'),
                importance=record.get('importance', 1.0),
                created_at=record['created_at'],
                topics=record.get('metadata', {}).get('topics', []),
                metadata=record.get('metadata', {})
            ) for record in records
        ]
    except Exception as e:
        log_event(logging.ERROR, "memories_list_error", str(e), user_id=user_id, status="error")
        raise HTTPException(status_code=500, detail="Failed to list memories.")

@router.put("/memory/{memory_id}", response_model=Memory)
async def update_memory(memory_id: int, updates: MemoryUpdate, user_id: str = Depends(get_current_user)):
    """
    Updates an existing memory's content, metadata, or importance.
    """
    try:
        update_dict = updates.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="No updates provided")
            
        record = await memory_store.update_memory(memory_id, user_id, update_dict)
        if not record:
            raise HTTPException(status_code=404, detail="Memory not found")
            
        log_event(logging.INFO, "memory_updated", "Updated memory", user_id=user_id, memory_id=memory_id)
        return Memory(
            id=record['id'],
            content=record['raw_text'],
            summary=record.get('summary', ''),
            memory_state=record.get('memory_state', 'strong'),
            importance=record.get('importance', 1.0),
            created_at=record['created_at'],
            topics=record.get('metadata', {}).get('topics', []),
            metadata=record.get('metadata', {})
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update memory")

@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: int, user_id: str = Depends(get_current_user)):
    """
    Deletes a memory permanently.
    """
    success = await memory_store.delete_memory(memory_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    log_event(logging.INFO, "memory_deleted", "Deleted memory", user_id=user_id, memory_id=memory_id)
    return None
