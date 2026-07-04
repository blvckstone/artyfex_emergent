# ArtyFex Auth Testing Playbook — Emergent Google Auth

**Integration:** Emergent Google Auth Integration (managed) + existing email/password + JWT.

Existing app stores its own JWT in `localStorage['artyfex_user_token']` and uses `Authorization: Bearer <jwt>` header. Google Auth was bridged into this same JWT so downstream endpoints (/api/me/*, /api/auth/me, wishlist, orders, review prompts, etc.) work identically for both login methods.

## Backend endpoints
- `POST /api/auth/signup`, `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/me` — existing email/password + JWT
- **NEW** `POST /api/auth/google/session` `{"session_id": "<from emergent auth redirect>"}` → exchanges session_id server-side with `https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data`, upserts user in `db.users` collection (by email), issues our own JWT, and returns `{token, user: {name, email, phone, picture}}`
- **NEW** `POST /api/auth/logout` — clears session_token cookie (no-op for JWT; frontend just discards it)
- **NEW** `GET /api/me/review-prompts` (authed) — returns products this user hasn't reviewed but which were delivered ≥ `review_prompt_days` ago
- **NEW** `GET /api/admin/settings`, `PATCH /api/admin/settings` — read/update `review_prompt_days` (default 7)

## Frontend flow (Emergent Auth)
1. User clicks "Continue with Google" → we redirect to `https://auth.emergentagent.com/?redirect=<origin>/auth/callback`
2. Emergent handles Google OAuth → redirects back to `<origin>/auth/callback#session_id=XXX`
3. The `AuthCallback` route detects `session_id` in URL fragment synchronously during render (via a top-level check in `AppRouter`)
4. Frontend calls `POST /api/auth/google/session {session_id}` — receives our JWT
5. JWT stored in `localStorage['artyfex_user_token']`; user context populated; router navigates to `/account`
6. All subsequent requests use the same `Authorization: Bearer <jwt>` interceptor already configured in `frontend/src/lib/api.js`

## Test users (must be manually created in a real Google OAuth flow — Emergent uses real Google accounts)
Existing password-based test user (email/password login):
- Any account signed up via /signup on the storefront

Google Auth test path:
- Requires a real Google account. Click "Continue with Google" → complete Google consent → land back at /auth/callback → auto-navigate to /account. Cross-check that `/api/auth/me` returns the Google-linked user.

## Regression checklist for testing agent
- [ ] Email/password signup still works
- [ ] Email/password login still works
- [ ] `POST /api/auth/google/session` with valid session_id creates/upserts user and returns JWT
- [ ] `POST /api/auth/google/session` with invalid/empty session_id returns 400
- [ ] Existing endpoints (/api/me/wishlist, /api/me/orders, /api/auth/me) work with the JWT issued via Google
- [ ] Google-linked user with no password can still call PATCH /api/auth/me to update name/phone

## Review-prompt tests
- [ ] Admin PATCH /api/admin/settings {"review_prompt_days": 7} → 200 with updated setting
- [ ] Public GET /api/admin/settings without admin token → 401
- [ ] GET /api/me/review-prompts returns empty list for user with no delivered orders
- [ ] Backdate an order (delivered_at = 10 days ago) — GET /api/me/review-prompts returns that product
- [ ] After user submits review on the product, GET /api/me/review-prompts no longer includes it
