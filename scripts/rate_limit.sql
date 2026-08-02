-- Rate limiting for the predictions table.
--
-- The publishable key is embedded in the application and must be assumed
-- public. Row-level security already prevents it reading anything back, but it
-- can still INSERT — so anyone who extracts it could script unlimited writes,
-- exhausting the free tier and running up a bill.
--
-- This is not a data breach: nothing leaks. It is a denial-of-service and a
-- cost problem, and it is worth closing before the project accepts real user
-- uploads.
--
-- Run in the Supabase SQL editor, after schema.sql and lockdown.sql.

-- ---------------------------------------------------------------------------
-- 1. Cap the rate of inserts
-- ---------------------------------------------------------------------------
-- A person screening recordings does a handful a minute. Sixty an hour is
-- generous for legitimate use and useless for flooding.

create or replace function check_insert_rate()
returns trigger
language plpgsql
security definer
as $$
declare
    recent_count integer;
begin
    select count(*) into recent_count
    from predictions
    where created_at > now() - interval '1 hour';

    if recent_count >= 60 then
        raise exception 'Rate limit reached. Try again later.'
            using errcode = 'check_violation';
    end if;

    return new;
end;
$$;

drop trigger if exists enforce_insert_rate on predictions;

create trigger enforce_insert_rate
    before insert on predictions
    for each row
    execute function check_insert_rate();

-- ---------------------------------------------------------------------------
-- 2. Reject values that cannot come from this application
-- ---------------------------------------------------------------------------
-- The app only ever writes a probability between zero and one, a plausible
-- heart rate, and a non-negative variability. Anything else was not produced
-- by the model, so refuse it at the database rather than storing junk.

alter table predictions
    drop constraint if exists predictions_plausible_values;

alter table predictions
    add constraint predictions_plausible_values check (
        (probability is null or (probability >= 0 and probability <= 1))
        and (heart_rate_bpm is null or (heart_rate_bpm > 0 and heart_rate_bpm < 400))
        and (rr_cv is null or (rr_cv >= 0 and rr_cv < 10))
        and (source is null or length(source) <= 100)
    );

-- ---------------------------------------------------------------------------
-- 3. Discard old rows automatically
-- ---------------------------------------------------------------------------
-- The history view exists to show recent activity, not to accumulate forever.
-- Keeping thirty days bounds the table's size whatever happens.

create or replace function prune_old_predictions()
returns void
language sql
security definer
as $$
    delete from predictions where created_at < now() - interval '30 days';
$$;

-- ---------------------------------------------------------------------------
-- 4. Confirm the result
-- ---------------------------------------------------------------------------

select tgname as trigger_name
from pg_trigger
where tgrelid = 'predictions'::regclass
  and not tgisinternal;

select conname as constraint_name
from pg_constraint
where conrelid = 'predictions'::regclass
  and contype = 'c';
