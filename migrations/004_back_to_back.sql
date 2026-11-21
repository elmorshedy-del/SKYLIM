-- Back-to-back scheduling (app/services/availability.fit): each reservation now covers only the trip's
-- own time, and records where it starts and ends and what could make it run late, so the next trip can
-- start from the previous drop-off with the right buffer. NULL places mean the home base (owner blocks).
ALTER TABLE reservations
    ADD COLUMN IF NOT EXISTS start_place text,
    ADD COLUMN IF NOT EXISTS end_place   text,
    ADD COLUMN IF NOT EXISTS risk        text;
