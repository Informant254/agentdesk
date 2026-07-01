-- Persistent storage for per-user AI provider API keys (encrypted).
-- Fixes: keys used to live only in memory and were wiped whenever Render
-- spun the service down on idle and restarted it.

CREATE TABLE IF NOT EXISTS public.provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,        -- matches JWT "sub" (e.g. user_email_at_domain.com), not a Supabase auth UUID
    provider TEXT NOT NULL,       -- 'anthropic', 'openai', 'google', etc.
    encrypted_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_provider_keys_user_id ON public.provider_keys(user_id);

CREATE TRIGGER update_provider_keys_updated_at
    BEFORE UPDATE ON public.provider_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Note: RLS is intentionally left disabled here. user_id is a JWT subject
-- string (not a Supabase auth.uid()), and all access goes through the
-- backend's own JWT-verified /api/opencode/providers routes, which already
-- scope every query by user_id. The service-role key used by the backend
-- bypasses RLS anyway.
