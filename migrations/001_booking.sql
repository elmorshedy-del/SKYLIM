-- 001_booking.sql — Meridian booking core.
--
-- Design rules enforced HERE, in the database, not in application code:
--   * money is integer cents; every timestamp is timestamptz (stored UTC)
--   * one vehicle / one driver can never hold two overlapping live reservations
--     (GiST exclusion constraints — two concurrent approvals cannot both win)
--   * a quote can back at most one booking; a Stripe event is processed once
--   * customer links are stored only as SHA-256 hashes of opaque random tokens

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------ resources
CREATE TABLE vehicles (
    id              uuid PRIMARY KEY,
    code            text NOT NULL UNIQUE,
    display_name    text NOT NULL,
    plate           text,                      -- set in admin; shown only to a confirmed passenger
    color           text,
    max_passengers  smallint NOT NULL CHECK (max_passengers BETWEEN 1 AND 20),
    active          boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE drivers (
    id              uuid PRIMARY KEY,
    code            text NOT NULL UNIQUE,
    display_name    text NOT NULL,             -- first name / public name only
    photo_url       text,                      -- real photo shown to a confirmed rider
    active          boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE customers (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email               text NOT NULL UNIQUE,  -- stored lower-case
    full_name           text NOT NULL,
    phone               text NOT NULL,
    saved_preferences   jsonb,                 -- only when the rider opted in
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------- quotes
-- A quote is an immutable server-side price snapshot. Browsers only ever send
-- the quote id back; they never send an amount.
CREATE TABLE quotes (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          timestamptz NOT NULL DEFAULT now(),
    expires_at          timestamptz NOT NULL,
    service             text NOT NULL CHECK (service IN ('transfer', 'hourly')),
    origin              text NOT NULL,              -- place code (data.PLACES)
    destination         text,                       -- NULL for hourly
    hours               numeric(4,1) CHECK (hours IS NULL OR hours > 0),
    route_class         text NOT NULL,              -- nj_intrastate | interstate | other_intrastate
    pickup_at           timestamptz NOT NULL,
    passengers          smallint NOT NULL CHECK (passengers BETWEEN 1 AND 20),
    large_bags          smallint NOT NULL CHECK (large_bags BETWEEN 0 AND 20),
    vehicle_code        text NOT NULL,
    amount_cents        integer CHECK (amount_cents IS NULL OR amount_cents > 0),
    currency            text NOT NULL DEFAULT 'usd' CHECK (currency = 'usd'),
    price_status        text NOT NULL CHECK (price_status IN ('firm', 'estimate', 'custom')),
    service_start       timestamptz NOT NULL,
    service_end         timestamptz NOT NULL,
    eligible            boolean NOT NULL,
    needs_review        boolean NOT NULL DEFAULT false,
    decision_reasons    text[] NOT NULL DEFAULT '{}',
    pricing_version     text NOT NULL,
    availability        text,                       -- available | unavailable | day_full (lost-demand analysis)
    session_id          text,                       -- first-party analytics session (no PII)
    attribution         jsonb,
    snapshot            jsonb NOT NULL,
    CHECK (service_end > service_start)
);

-- ------------------------------------------------------------------- bookings
CREATE TABLE bookings (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ref                 text NOT NULL UNIQUE,
    quote_id            uuid NOT NULL UNIQUE REFERENCES quotes(id),
    customer_id         uuid NOT NULL REFERENCES customers(id),
    -- contact snapshot as given for THIS trip (a later booking can't rewrite it)
    contact_name        text NOT NULL,
    contact_email       text NOT NULL,
    contact_phone       text NOT NULL,
    status              text NOT NULL CHECK (status IN (
                            'requested', 'payment_pending', 'confirmed', 'en_route',
                            'arrived', 'in_vehicle', 'completed', 'cancelled',
                            'declined', 'expired')),
    service             text NOT NULL,
    hours               numeric(4,1),
    pickup_at           timestamptz NOT NULL,
    service_start       timestamptz NOT NULL,
    service_end         timestamptz NOT NULL,
    pickup_address      text NOT NULL,
    dropoff_address     text NOT NULL,
    flight_number       text,
    passengers          smallint NOT NULL,
    large_bags          smallint NOT NULL,
    notes               text,
    preferences         jsonb NOT NULL DEFAULT '{}'::jsonb,
    remember_preferences boolean NOT NULL DEFAULT false,
    policy_version      text NOT NULL,          -- terms the rider accepted; never rewritten
    amount_cents        integer NOT NULL CHECK (amount_cents > 0),
    currency            text NOT NULL DEFAULT 'usd' CHECK (currency = 'usd'),
    price_adjust_reason text,
    vehicle_id          uuid REFERENCES vehicles(id),
    driver_id           uuid REFERENCES drivers(id),
    access_token_hash   text NOT NULL UNIQUE,
    share_token_hash    text UNIQUE,
    share_expires_at    timestamptz,
    review_flag         text,                   -- e.g. late_payment, cancellation_request
    instant             boolean NOT NULL DEFAULT false,   -- reserved and paid without owner approval
    source              text,                   -- channel summary for the 30-day review
    attribution         jsonb,                  -- utm_*, gclid/gbraid/wbraid, referrer, landing page, GA client id
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    approved_at         timestamptz,
    confirmed_at        timestamptz,
    trip_started_at     timestamptz,                -- En route pressed; no location before this
    completed_at        timestamptz,
    cancelled_at        timestamptz,
    cancel_reason       text,
    CHECK (service_end > service_start)
);
CREATE INDEX bookings_status_idx ON bookings (status, pickup_at);
CREATE INDEX bookings_driver_active_idx ON bookings (driver_id)
    WHERE status IN ('en_route', 'arrived', 'in_vehicle');

CREATE TABLE booking_events (
    id          bigserial PRIMARY KEY,
    booking_id  uuid NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    at          timestamptz NOT NULL DEFAULT now(),
    actor       text NOT NULL,                  -- 'customer' | 'admin' | 'stripe' | 'system'
    from_status text,
    to_status   text,
    note        text
);
CREATE INDEX booking_events_booking_idx ON booking_events (booking_id, at);

-- --------------------------------------------------------------- reservations
-- The calendar. A row blocks its vehicle and its driver for [service_start,
-- service_end) until released. Holds carry an expiry; a confirmed reservation
-- does not. Expired holds are released inside the same transaction that tries
-- to take the slot, so a stale hold can never block a paying rider.
CREATE TABLE reservations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id  uuid REFERENCES bookings(id) ON DELETE CASCADE,   -- NULL for an owner time block
    vehicle_id  uuid NOT NULL REFERENCES vehicles(id),
    driver_id   uuid NOT NULL REFERENCES drivers(id),
    during      tstzrange NOT NULL CHECK (NOT isempty(during)),
    kind        text NOT NULL CHECK (kind IN ('hold', 'confirmed', 'block')),
    expires_at  timestamptz,
    note        text,                          -- e.g. "personal", "service appointment"
    created_at  timestamptz NOT NULL DEFAULT now(),
    released_at timestamptz,
    release_reason text,
    CHECK ((kind = 'hold') = (expires_at IS NOT NULL)),
    CHECK ((kind = 'block') = (booking_id IS NULL)),
    CONSTRAINT reservations_vehicle_no_overlap
        EXCLUDE USING gist (vehicle_id WITH =, during WITH &&) WHERE (released_at IS NULL),
    CONSTRAINT reservations_driver_no_overlap
        EXCLUDE USING gist (driver_id WITH =, during WITH &&) WHERE (released_at IS NULL)
);
CREATE UNIQUE INDEX reservations_one_live_per_booking
    ON reservations (booking_id) WHERE released_at IS NULL;
CREATE INDEX reservations_hold_expiry_idx
    ON reservations (expires_at) WHERE released_at IS NULL AND kind = 'hold';

-- ------------------------------------------------------------------- payments
CREATE TABLE payments (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id          uuid NOT NULL REFERENCES bookings(id),
    provider            text NOT NULL DEFAULT 'stripe',
    livemode            boolean NOT NULL,
    checkout_session_id text NOT NULL UNIQUE,
    payment_intent_id   text UNIQUE,
    amount_cents        integer NOT NULL CHECK (amount_cents > 0),
    currency            text NOT NULL CHECK (currency = 'usd'),
    status              text NOT NULL CHECK (status IN (
                            'open', 'paid', 'failed', 'expired', 'refunded', 'partially_refunded')),
    refunded_cents      integer NOT NULL DEFAULT 0 CHECK (refunded_cents >= 0),
    checkout_url        text,
    expires_at          timestamptz NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    paid_at             timestamptz,
    updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX payments_booking_idx ON payments (booking_id);
CREATE UNIQUE INDEX payments_one_paid_per_booking
    ON payments (booking_id) WHERE status IN ('paid', 'partially_refunded');

CREATE TABLE stripe_events (
    id              text PRIMARY KEY,           -- evt_... ; duplicates are no-ops
    type            text NOT NULL,
    livemode        boolean NOT NULL,
    received_at     timestamptz NOT NULL DEFAULT now(),
    outcome         text
);

-- ------------------------------------------------------------------- tracking
-- A tracker is anything that reports positions: the chauffeur's phone (Traccar
-- Client, follows the driver) or a unit installed in the car (follows the
-- vehicle, forwarded by a Traccar server). Riders see the freshest fix from any
-- tracker attached to their trip's driver or vehicle.
CREATE TABLE trackers (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_hash text NOT NULL UNIQUE,           -- SHA-256 of the device identifier (treated as a secret)
    kind        text NOT NULL CHECK (kind IN ('phone', 'vehicle')),
    driver_id   uuid REFERENCES drivers(id),
    vehicle_id  uuid REFERENCES vehicles(id),
    label       text NOT NULL,
    active      boolean NOT NULL DEFAULT true,
    last_seen_at timestamptz,                   -- health check shown in admin
    created_at  timestamptz NOT NULL DEFAULT now(),
    CHECK ((kind = 'phone' AND driver_id IS NOT NULL) OR (kind = 'vehicle' AND vehicle_id IS NOT NULL))
);

-- Positions are accepted only while the driver's booking is en route / arrived /
-- in vehicle, and are deleted when the trip ends (see TRACKING_RETENTION_HOURS).
CREATE TABLE positions (
    id          bigserial PRIMARY KEY,
    booking_id  uuid NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    tracker_id  uuid NOT NULL REFERENCES trackers(id),
    lat         double precision NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lon         double precision NOT NULL CHECK (lon BETWEEN -180 AND 180),
    accuracy_m  real,
    speed_mps   real,
    heading     real,
    reported_at timestamptz NOT NULL,           -- device fix time
    received_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX positions_booking_latest_idx ON positions (booking_id, reported_at DESC);

-- ------------------------------------------------------------- notifications
CREATE TABLE outbox (
    id          bigserial PRIMARY KEY,
    dedupe_key  text NOT NULL UNIQUE,           -- e.g. receipt:<booking>; prevents duplicate mail
    booking_id  uuid REFERENCES bookings(id) ON DELETE SET NULL,
    kind        text NOT NULL,
    to_email    text NOT NULL,
    subject     text NOT NULL,
    body_text   text NOT NULL,
    status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'manual', 'suppressed')),
    attempts    smallint NOT NULL DEFAULT 0,
    last_error  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    sent_at     timestamptz
);
CREATE INDEX outbox_pending_idx ON outbox (created_at) WHERE status = 'pending';

-- --------------------------------------------------------- analytics outbox
-- Server-side conversion events (GA4 Measurement Protocol), written in the same
-- transaction as the payment that caused them and delivered by the sweeper.
CREATE TABLE analytics_outbox (
    id          bigserial PRIMARY KEY,
    dedupe_key  text NOT NULL UNIQUE,           -- purchase:<booking>, refund:<payment>:<cents>
    destination text NOT NULL,                  -- ga4
    payload     jsonb NOT NULL,
    status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'skipped')),
    attempts    smallint NOT NULL DEFAULT 0,
    last_error  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    sent_at     timestamptz
);
CREATE INDEX analytics_outbox_pending_idx ON analytics_outbox (created_at) WHERE status = 'pending';

-- --------------------------------------------------------- inquiries / waitlist
CREATE TABLE inquiries (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind        text NOT NULL CHECK (kind IN ('custom_quote', 'waitlist', 'corporate')),
    email       text NOT NULL,
    name        text,
    phone       text,
    message     text,
    source      text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    handled_at  timestamptz
);

-- -------------------------------------------------------------- runtime flags
-- Owner switches that must change without a deploy (e.g. pause instant booking at peak).
CREATE TABLE flags (
    key         text PRIMARY KEY,
    enabled     boolean NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);
INSERT INTO flags (key, enabled) VALUES ('instant_booking', true);
