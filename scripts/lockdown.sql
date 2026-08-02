-- Tighten access to the predictions table.
-- Run in the Supabase SQL editor, after the original schema.
--
-- The dashboard writes with the publishable key, which is embedded in the
-- application and must be assumed public. It should therefore be able to
-- INSERT and nothing else. Reading is done with the secret key, which stays
-- on the server and never reaches a browser.

-- Remove public read access.
drop policy if exists "anon can read screening results" on predictions;

-- Keep insert, so screenings can still be recorded.
-- (Already created by schema.sql; repeated here only if it is missing.)
do $$
begin
    if not exists (
        select 1 from pg_policies
        where tablename = 'predictions'
          and policyname = 'anon can insert screening results'
    ) then
        create policy "anon can insert screening results"
            on predictions for insert
            to anon
            with check (true);
    end if;
end $$;

-- Confirm the result: one INSERT policy, no SELECT policy.
select policyname, cmd, roles from pg_policies where tablename = 'predictions';
