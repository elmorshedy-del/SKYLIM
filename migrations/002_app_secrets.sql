-- Secrets the application provisions for itself — today the Stripe webhook signing secret, which
-- Stripe reveals only once, when the site registers its endpoint. Stored encrypted with a key
-- derived from SECRET_KEY (app/services/stripe_setup.py). Never written by hand.
CREATE TABLE IF NOT EXISTS app_secrets (
    name        text PRIMARY KEY,
    ciphertext  text NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);
