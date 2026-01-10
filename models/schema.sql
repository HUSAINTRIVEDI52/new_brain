-- Second Brain Database Schema
-- Optimized for Hybrid Search & Forgetting Curve

-- Use pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- Memories table: Core content and metadata
CREATE TABLE IF NOT EXISTS memories (
  id bigint primary key generated always as identity,
  user_id uuid not null,
  raw_text text not null,
  summary text not null,
  embedding vector(1536), -- OpenRouter/OpenAI embedding dimension
  importance float default 1.0 not null,
  access_count int default 0 not null,
  summary_count int default 0 not null,
  created_at timestamptz default now() not null,
  last_accessed_at timestamptz default now() not null
);

-- Enable Row Level Security (RLS)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own memories
CREATE POLICY user_isolation_policy ON memories
  FOR ALL
  USING (auth.uid() = user_id);

-- Migration: Add dynamic ranking columns if they don't exist
-- DO $$ BEGIN
--   IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='importance') THEN
--     ALTER TABLE memories ADD COLUMN importance float DEFAULT 1.0 NOT NULL;
--   END IF;
-- END $$;

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION match_memories (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  p_user_id uuid
)
RETURNS TABLE (
  id bigint,
  user_id uuid,
  raw_text text,
  summary text,
  importance float,
  created_at timestamptz,
  last_accessed_at timestamptz,
  access_count int,
  summary_count int,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.user_id,
    m.raw_text,
    m.summary,
    m.importance,
    m.created_at,
    m.last_accessed_at,
    m.access_count,
    m.summary_count,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM memories m
  WHERE m.user_id = p_user_id
    AND 1 - (m.embedding <=> query_embedding) > match_threshold
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories (user_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories (created_at DESC);
