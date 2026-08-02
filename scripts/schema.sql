-- Table backing the dashboard's history view.
-- Run once in the Supabase SQL editor.

create table if not exists predictions (
    id             bigint generated always as identity primary key,
    created_at     timestamptz not null default now(),
    source         text,
    probability    double precision,
    flagged        boolean,
    heart_rate_bpm double precision,
    rr_cv          double precision
);

create index if not exists predictions_created_at_idx
    on predictions (created_at desc);
