-- Persist test intent at quote time; a browser cannot turn a $1 quote into a live booking.
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS is_test boolean NOT NULL DEFAULT false;
UPDATE quotes SET is_test = true WHERE attribution->>'source' = 'test_trip';
