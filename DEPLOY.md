# ArtyFex — Production Deployment Guide

Stack: **Vercel** (frontend) + **Render** (backend) + **MongoDB Atlas** (database).

All three services have a **free tier**. Estimated setup time: ~40 minutes.

---

## Phase 0 — Prepare production credentials (do this first)

Before starting, gather these:

1. **Razorpay LIVE keys** — log into your Razorpay dashboard → Settings → API Keys → Generate Live Keys. Requires completed KYC. You'll get:
   - `RAZORPAY_KEY_ID` (starts with `rzp_live_`)
   - `RAZORPAY_KEY_SECRET`
2. **Resend API key** + **verified sending domain** — log into resend.com → Domains → add `artyfex.in` and complete the DNS records. Then Domains → verified. API key from Settings → API Keys.
3. **A strong admin password** for `admin@artyfex.in` (min 12 chars).
4. **A random JWT secret** — generate one at https://generate-secret.vercel.app/64 or run `openssl rand -hex 32` locally.

Keep them in a password manager. You'll paste them into Render + Vercel dashboards.

---

## Phase 1 — MongoDB Atlas (5 min)

1. Go to https://www.mongodb.com/cloud/atlas/register and sign up (free).
2. Create a **new project** → name it "artyfex".
3. Click **Build a Database** → choose **M0 (Free)** → pick a region close to your customers (e.g. Mumbai) → Create.
4. **Database Access** (left sidebar) → **Add New Database User**:
   - Username: `artyfex_app`
   - Password: click **Autogenerate** → copy and save it
   - Built-in Role: `Read and write to any database` → Add User
5. **Network Access** (left sidebar) → **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`) → Confirm.
   > Render's IPs are dynamic on the free tier, so this is the pragmatic choice. Upgrade to a static-IP plan later if you want to lock it down.
6. **Database** (left sidebar) → your cluster → **Connect** button → **Drivers** → copy the connection string. It looks like:
   ```
   mongodb+srv://artyfex_app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Replace `<password>` with the real password from step 4. **This is your `MONGO_URL`.**

---

## Phase 2 — Render backend (10 min)

1. Push the latest code to GitHub (your repo `blvckstone/artyfex_emergent`). Use the "Save to GitHub" button in Emergent — the new `render.yaml`, `frontend/vercel.json`, and `frontend/.npmrc` must be included.
2. Go to https://render.com and sign up with your GitHub account.
3. Dashboard → **New** → **Blueprint**.
4. Connect your GitHub → select `blvckstone/artyfex_emergent`.
5. Render auto-reads `render.yaml` → shows one service "artyfex-backend" → asks you to fill env vars.
6. Fill these (one at a time):
   ```
   MONGO_URL           = <the mongodb+srv URI from Phase 1>
   DB_NAME             = artyfex_prod
   CORS_ORIGINS        = *          (temporary — you'll tighten this in Phase 4)
   JWT_SECRET          = <the 64-char random hex string>
   ADMIN_EMAIL         = admin@artyfex.in
   ADMIN_PASSWORD      = <your strong password>
   RAZORPAY_KEY_ID     = rzp_live_xxx
   RAZORPAY_KEY_SECRET = xxx
   RESEND_API_KEY      = re_xxx
   SENDER_EMAIL        = no-reply@artyfex.in
   SENDER_NAME         = ArtyFex Atelier
   ```
7. Click **Apply** → Render builds & deploys (~5–10 min).
8. When it's live, copy the URL Render gives you — something like `https://artyfex-backend.onrender.com`.
9. Test in browser: open `https://artyfex-backend.onrender.com/api/products` — you should see a JSON array (may be empty if products weren't seeded; that's fine).
10. Test admin login: on your computer terminal (or Postman):
    ```
    curl -X POST https://artyfex-backend.onrender.com/api/admin/login \
      -H "Content-Type: application/json" \
      -d '{"email":"admin@artyfex.in","password":"<your password>"}'
    ```
    You should get back `{"token":"...","email":"admin@artyfex.in"}`. If yes, backend is good.

### ⚠️ Render free tier note
Free services **spin down after 15 minutes of inactivity** and take ~50s to wake on the next request. For production, upgrade to the **Starter plan ($7/mo)** for always-on. Update `plan: starter` in `render.yaml` when you're ready.

---

## Phase 3 — Vercel frontend (5 min)

1. Go to https://vercel.com and sign up with GitHub.
2. Dashboard → **Add New** → **Project** → select `blvckstone/artyfex_emergent`.
3. Configure Project screen — fill exactly:
   - **Root Directory:** `frontend`
   - Framework Preset: `Create React App` (auto-detected)
   - Build Command: leave as-is (comes from `vercel.json` → `yarn build`)
   - Output Directory: leave as-is (`build`)
   - Install Command: leave as-is (`yarn install --frozen-lockfile`)
4. Expand **Environment Variables** → add:
   ```
   Name:  REACT_APP_BACKEND_URL
   Value: https://artyfex-backend.onrender.com     ← URL from Phase 2 step 8, NO trailing slash
   ```
5. Click **Deploy** → Vercel builds (~2 min) → you get a URL like `https://artyfex-emergent.vercel.app`.
6. Open the URL → the storefront should load with products.

---

## Phase 4 — Tighten CORS + connect custom domain

### 4a. Tighten CORS
Go back to Render → artyfex-backend → Environment → edit `CORS_ORIGINS`:

```
https://artyfex-emergent.vercel.app,https://artyfex.in,https://www.artyfex.in
```

Save → Render auto-redeploys.

### 4b. Custom domain on Vercel (optional)
1. Vercel → your project → **Settings** → **Domains** → Add → type `artyfex.in`.
2. Vercel shows you DNS records → add them at your domain registrar (GoDaddy / Namecheap / whoever).
3. Repeat for `www.artyfex.in`.
4. Wait ~10–30 min for DNS to propagate. Vercel auto-issues SSL cert.

### 4c. Razorpay webhook (optional but recommended)
Razorpay dashboard → Settings → Webhooks → Add →
- URL: `https://artyfex-backend.onrender.com/api/orders/webhook` (only if we later add a webhook endpoint; not required for MVP because we verify payments on the client-callback path).

---

## Phase 5 — Verify end-to-end

1. Open your Vercel URL.
2. Try to place an order with a Razorpay LIVE test payment (small amount, e.g. ₹1). If it succeeds and you see the order in `/admin` → Orders, you're LIVE.
3. Admin login → dashboard → all analytics load.
4. Try one email flow (e.g. review-request trigger) → confirm Resend logs show the send.

---

## Troubleshooting quick-reference

| Symptom | Fix |
|---|---|
| Vercel build fails with `ERESOLVE` npm error | The `frontend/.npmrc` file (with `legacy-peer-deps=true`) + `frontend/vercel.json` (with `yarn install`) already fix this. Ensure both files are committed. |
| Frontend loads but API calls fail with CORS error | Add your Vercel URL to `CORS_ORIGINS` on Render → save → wait for redeploy. |
| Backend `502` from Vercel | Render service is spinning up (free tier). Wait 50s and retry, or upgrade to Starter. |
| MongoDB timeout | Network Access in Atlas is not set to `0.0.0.0/0`. Fix that. |
| Admin can't log in | Re-check `ADMIN_EMAIL` / `ADMIN_PASSWORD` in Render env. Restart the Render service after any env change. |
| Razorpay checkout fails | Make sure you're using **LIVE** keys and your Razorpay account is **activated** (KYC complete). Test keys don't work on live domains. |

---

## Files added for deployment

- `frontend/.npmrc` — forces `legacy-peer-deps=true` so any residual npm run won't ERESOLVE.
- `frontend/vercel.json` — tells Vercel to use `yarn`, build with `yarn build`, output `build/`, and SPA-rewrite everything to `index.html`.
- `render.yaml` — Render Blueprint for a one-click backend deploy.
- `frontend/.env.example` — template of the env var Vercel needs.
- `backend/.env.example` — template of the env vars Render needs.

All env-var VALUES stay in the respective platform dashboards. The `.env.example` files are just documentation — safe to commit.

---

**Do not commit real `backend/.env` or `frontend/.env` files** — the repo already has them gitignored. Keep your production secrets only in Render / Vercel / Atlas dashboards.
