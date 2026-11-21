-- The owner's $1 test trips (app/services/test_trip.py) are real bookings, flagged so they never
-- count as revenue or demand: excluded from analytics, Google Ads conversions and the funnel.
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_test boolean NOT NULL DEFAULT false;
