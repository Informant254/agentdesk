-- Persistent storage for per-user AI provider API keys (encrypted).
-- Self-contained: creates the updated_at trigger function too, in case
-- it wasn't already created by the original schema.sql.

CREATE TABLE IF NOT EXISTS public.provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_provider_keys_user_id
    ON public.provider_keys (user_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_provider_keys_updated_at ON public.provider_keys;

CREATE TRIGGER update_provider_keys_updated_at
BEFORE UPDATE ON public.provider_keys
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
