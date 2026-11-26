---
name: supabase-postgres-rls
description: >-
  Designs high-performance PostgreSQL schemas, indexes, triggers, Edge Functions, and
  Row Level Security (RLS) policies on Supabase. Inspired by supabase/postgres-best-practices.
  Use whenever designing databases, writing SQL migrations, or configuring Supabase backends.
---

# Supabase & PostgreSQL Architecture + RLS Security

Inspired by `supabase/postgres-best-practices` and pairs directly with your installed `supabase` MCP server.

## 1. Schema & Indexing Best Practices
1. **Primary Keys & Timestamps**:
   - Use `uuid default gen_random_uuid()` or `bigint generated always as identity` for primary keys.
   - Include `created_at timestamptz not null default now()` and `updated_at timestamptz not null default now()` on all core tables.
2. **Index Every Foreign Key & RLS Filter Column**:
   - PostgreSQL does **not** automatically index foreign key columns. Always create explicit B-Tree indexes on `user_id`, `tenant_id`, and any column used in `JOIN` or `WHERE` clauses.
3. **Use `jsonb` Wisely**:
   - Use relational columns for fields queried/sorted frequently; use `jsonb` with a `GIN` index for flexible metadata.

## 2. Row Level Security (RLS) Rules
1. **Enable RLS on Every Table in `public`**:
   ```sql
   alter table public.documents enable row level security;
   ```
2. **Optimize `auth.uid()` Calls in Policies**:
   - Wrap `auth.uid()` in `(select auth.uid())` so Postgres caches the result per query instead of re-evaluating it per row:
   ```sql
   create policy "Users can view own documents"
     on public.documents for select
     to authenticated
     using ( (select auth.uid()) = user_id );
   ```
3. **Separate `INSERT`, `UPDATE`, `DELETE` Policies**:
   - Always include both `using (...)` and `with check (...)` on `UPDATE` policies so users cannot reassign row ownership to another user.
