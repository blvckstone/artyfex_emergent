# ArtyFex — Production Deployment Guide

**Stack:** Vercel (frontend) + **Northflank** (backend) + MongoDB Atlas (database) + Cloudinary (images) + Razorpay (payments) + Resend (email) + Google OAuth (sign-in).

The backend already runs on Northflank at `https://api.artyfex.in` (custom domain) with CI/CD from `main` on GitHub. This document is the single source of truth after the Render → Northflank migration.

---

## 1. What lives where

| Component | Hosted at | Custom domain |
|---|---|---|
| Frontend (React) | Vercel | `https://www.artyfex.in` |
| Backend (FastAPI) | Northflank | `https://api.artyfex.in` |
| Database | MongoDB Atlas (M0 free) | — |
| Images CDN | Cloudinary | — |
| Payments | Razorpay LIVE | — |
| Email | Resend + verified `artyfex.in` domain | — |
| Google Sign-In | Google Cloud OAuth 2.0 client | — |

CI/CD flow: `git push origin main` → **Vercel** rebuilds frontend + **Northflank** rebuilds backend automatically. You do not touch the servers.

---

## 2. Files in this repo that make deploys deterministic

| File | Purpose |
|---|---|
| `backend/Dockerfile` | Reproducible Python 3.11 build. Northflank uses this if you pick "Dockerfile" as the build type. |
| `backend/nixpacks.toml` | Alternative: buildpack config, used when Northflank build type is "Buildpack (Nixpacks)". |
| `backend/Procfile` | Start command hint for the Heroku-style buildpack (which Northflank uses by default in Combined services). |
| `backend/.python-version` | Pins Python to major version **3.11** (Heroku Python buildpack v6+ requires major-only). |
| `backend/.dockerignore` | Keeps the image slim. |
| `backend/.env.example` | Reference list of every backend env var. **Never** commit the real `.env`. |
| `frontend/vercel.json` | Tells Vercel to use `yarn`, build with `yarn build`, output `build/`, and SPA-rewrite everything to `index.html`. |
| `frontend/.npmrc` | Forces `legacy-peer-deps=true` so an accidental npm run won't ERESOLVE. |
| `frontend/.env.example` | Reference for `REACT_APP_BACKEND_URL`. |

---

## 3. Backend env vars — set these in Northflank → Secrets

Copy from `backend/.env.example`. The critical ones after the Render → Northflank migration are:

```
MONGO_URL              = mongodb+srv://... (from MongoDB Atlas)
DB_NAME                = artyfex_prod
APP_ENV                = production
JWT_SECRET             = 64-char random hex   (openssl rand -hex 32)
CORS_ORIGINS           = https://www.artyfex.in,https://artyfex.in
BACKEND_PUBLIC_URL     = https://api.artyfex.in          ← MUST match Northflank custom domain
FRONTEND_PUBLIC_URL    = https://www.artyfex.in
SITE_URL               = https://www.artyfex.in
ADMIN_EMAIL            = admin@artyfex.in
ADMIN_PASSWORD         = <strong password, min 12 chars>
RAZORPAY_KEY_ID        = rzp_live_xxx
RAZORPAY_KEY_SECRET    = xxx
RAZORPAY_WEBHOOK_SECRET= xxx   (optional but recommended)
RESEND_API_KEY         = re_xxx
SENDER_EMAIL           = no-reply@artyfex.in
SENDER_NAME            = ArtyFex Atelier
GOOGLE_CLIENT_ID       = xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET   = xxx
CLOUDINARY_CLOUD_NAME  = xxx
CLOUDINARY_API_KEY     = xxx
CLOUDINARY_API_SECRET  = xxx

# NimbusPost courier (Task 7 / Batch 4)
NIMBUSPOST_EMAIL          = artyfex.in+xxxx@gmail.com   # created in NimbusPost → Settings → API
NIMBUSPOST_PASSWORD       = xxxxxxxxxxxx                # ditto
NIMBUSPOST_LEGACY_KEY     = xxx                         # fallback old API key
NIMBUSPOST_WAREHOUSE_NAME =                             # OPTIONAL — leave blank and set in Admin → Shipping
```

After changing any secret in Northflank, click **Restart** on the service. Environment variables are only re-read on process boot.

---

## 4. Frontend env var — set in Vercel → Project → Settings → Environment Variables

```
REACT_APP_BACKEND_URL = https://api.artyfex.in
```

No trailing slash. Apply to **Production**, **Preview**, and **Development** scopes. Redeploy after saving.

---

## 5. Google OAuth — critical after backend URL change

Google Sign-In will silently break if the OAuth redirect URI on Google's side still points at the old Render URL.

1. Go to https://console.cloud.google.com/apis/credentials → your OAuth 2.0 Client ID (Web application).
2. Under **Authorized redirect URIs**, ensure this exact string is present:
   ```
   https://api.artyfex.in/api/auth/google/callback
   ```
3. Under **Authorized JavaScript origins**, ensure both are present:
   ```
   https://www.artyfex.in
   https://artyfex.in
   ```
4. Save. Google propagates the change in ~1 minute.

You can safely leave the old Render URLs in the list too, but they are no longer used.

---

## 6. Razorpay — does it need anything after the move?

**No client-side change needed.** Payment verification happens on the backend using `RAZORPAY_KEY_SECRET`; the browser never talks to Razorpay's dashboard with a redirect URL. Just make sure both keys are set in Northflank.

If you use the webhook (recommended), update the webhook URL in Razorpay Dashboard → Settings → Webhooks to:
```
https://api.artyfex.in/api/razorpay/webhook
```

---

## 7. Resend email — does it need anything after the move?

**No.** Resend uses API-key auth; there's no callback URL. Verify these once:
- `artyfex.in` domain is verified in resend.com/domains (DNS SPF + DKIM records set).
- `SENDER_EMAIL` in Northflank matches a verified sending identity (e.g. `no-reply@artyfex.in`).

---

## 8. Post-deploy verification (run these after any deploy)

Open in a browser (or curl) — each should return `200 OK`:

```
https://api.artyfex.in/api/products      → JSON list of products (or [])
https://api.artyfex.in/api/health        → deep readiness report (see below)
https://www.artyfex.in                   → the storefront loads
```

**The `/api/health` endpoint is your best friend.** It returns:
```json
{
  "app": "ok",
  "env": "production",
  "mongo": "ok",
  "razorpay_configured": true,
  "resend_configured": true,
  "google_oauth_configured": true,
  "cloudinary_configured": true,
  "backend_public_url": "https://api.artyfex.in",
  "cors_allow_origins": ["https://www.artyfex.in","https://artyfex.in"],
  "jwt_secret_strength": "strong"
}
```

Any `false` or `weak` = the corresponding feature is broken in production. Fix the env var in Northflank and restart.

---

## 9. Troubleshooting quick-reference

| Symptom | Root cause | Fix |
|---|---|---|
| Frontend loads but every API call CORS-fails | `CORS_ORIGINS` in Northflank does not include your Vercel/custom domain | Set `CORS_ORIGINS=https://www.artyfex.in,https://artyfex.in` in Northflank → restart |
| Google Sign-In pops "redirect_uri_mismatch" | Google Cloud Console still has old Render redirect URI | Add `https://api.artyfex.in/api/auth/google/callback` in Google Console (see §5) |
| Razorpay checkout opens but "Signature verification failed" after payment | `RAZORPAY_KEY_SECRET` in Northflank is wrong or from test-mode | Copy LIVE secret from Razorpay dashboard → set in Northflank → restart |
| Order emails don't arrive | `RESEND_API_KEY` missing, or `SENDER_EMAIL` not from a verified domain | Fix env in Northflank → restart. Test at `resend.com/logs` |
| Admin can't log in | `ADMIN_EMAIL` / `ADMIN_PASSWORD` mismatched | Update env in Northflank → restart (the seed re-syncs on next boot) |
| Health returns `mongo: fail: ...` | Atlas Network Access blocks Northflank IPs | Atlas → Network Access → Add IP `0.0.0.0/0` (allow anywhere) |
| PWA install icon shows old / cropped image | Browser cached the old manifest icons | Uninstall the PWA and reinstall, or hard-refresh (`Ctrl+Shift+R`) |

---

## 10. Local development

Backend:
```
cd backend
cp .env.example .env       # then fill real values
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

Frontend:
```
cd frontend
cp .env.example .env       # REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn start
```

---

**Never commit real `.env` files.** The repo has them gitignored. Secrets live only in Northflank + Vercel + Atlas dashboards.
