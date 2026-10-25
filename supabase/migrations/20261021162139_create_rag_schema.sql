
-- Omogućuje generiranje UUID identifikatora.
create extension if not exists pgcrypto;

-- pgvector je možda već uključen u Supabaseu.
-- Ako je instaliran u drugoj shemi, ne treba ga ponovno instalirati.
create extension if not exists vector with schema extensions;

-- 1. Kolegiji
create table public.courses (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    created_at timestamptz not null default now()
);

-- 2. Dokumenti
create table public.documents (
    id uuid primary key default gen_random_uuid(),
    course_id uuid not null
      references public.courses(id) on delete cascade,
    filename text not null,
    storage_path text,
    status text not null default 'pending'
      check (status in ('pending', 'processing', 'ready', 'failed')),
    created_at timestamptz not null default now()
);

-- 3. Odlomci iz dokumenata
create table public.document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null
        references public.documents(id) on delete cascade,
    chunk_index integer not null,
    page_number integer not null,
    content text not null,
    embedding extensions.vector(1536),
    created_at timestamptz not null default now(),

    unique (document_id, chunk_index)
);

-- Indeksi za povezivanje tablica i filtriranje.
create index documents_course_id_idx
    on public.documents(course_id);

create index document_chunks_document_id_idx
    on public.document_chunks(document_id);
