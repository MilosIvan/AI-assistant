CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding extensions.vector(1536),
    match_count integer DEFAULT 5,
    filter_course_id uuid DEFAULT NULL
)
RETURNS TABLE (
    chunk_id uuid,
    content text,
    page_number integer,
    filename text,
    document_id uuid,
    similarity double precision
)
LANGUAGE sql
STABLE
AS $$
SELECT
    dc.id AS chunk_id,
    dc.content,
    dc.page_number,
    d.filename,
    d.id AS document_id,
    1 - (
        dc.embedding OPERATOR(extensions.<=>) query_embedding
        ) AS similarity
FROM public.document_chunks dc
         JOIN public.documents d ON d.id = dc.document_id
WHERE
    d.status = 'ready'
  AND (
    filter_course_id IS NULL
        OR d.course_id = filter_course_id
    )
ORDER BY
    dc.embedding OPERATOR(extensions.<=>) query_embedding
    LIMIT match_count;
$$;