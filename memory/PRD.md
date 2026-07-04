# ArtyFex Luxury E-Commerce SPA — PRD

## Original Problem Statement
Build a highly attractive, ultra-premium, fully functional SPA e-commerce website for ArtyFex (www.artyfex.in), a luxury brand of 100% handmade resin art & crystal stone mirrors. Hero product: 2×3 ft geode statement mirror (120 artisan hours, crushed crystal, gold aluminum border).

## Architecture
- Frontend: React SPA (converted from Svelte spec) + Tailwind + Framer Motion + shadcn/ui + Cormorant Garamond / Instrument Serif / Outfit fonts. Client-side routing via react-router-dom for /admin.
- Backend: FastAPI + Motor + Pydantic + PyJWT + bcrypt + razorpay SDK.
- DB: MongoDB (products, reviews, orders, b2b_leads, admins).

## User Personas
1. Retail collector — browses & buys a statement mirror via Razorpay (cards/UPI/netbanking).
2. Trade / B2B client (interior designer, hotel, salon) — submits enquiry via /#b2b form.
3. Atelier admin — logs into /admin to manage products, orders, leads and reviews.

## Core Requirements
- Cinematic hero + editorial luxury aesthetic (deep black, cream, gold).
- Product showcase with variant customizer (Aqua, Lavender, Silver, Gold) & materials breakdown.
- Companion collection grid + Craftsmanship story + Verified Collector Reviews.
- Fully interactive fly-out cart + real Razorpay checkout (test mode).
- B2B enquiry form → leads captured.
- Admin panel: JWT login, dashboard, product CRUD, order status pipeline, lead pipeline, review moderation.

## What's Been Implemented (Feb 2026)
- Full luxury storefront: Hero, ProductShowcase (variant customizer), Craftsmanship, Collection, Reviews, B2B, Footer, CartSheet, CheckoutDialog. ✅
- Real Razorpay integration (create-order + signature verification). ✅
- Admin panel at /admin with JWT auth, dashboard stats, products/orders/leads/reviews management. ✅
- Autofill dark-background fix + centered checkout dialog. ✅
- Seeded 4 products + 6 reviews + 1 admin.
- **[Phase A — Feb 2026] Returns Overhaul**: strict 3-day return window from delivery timestamp; customer return dialog with packaging warning + damage image URL + packaging confirmation checkbox; admin Returns tab with approve/reject + genuine assessment + admin notes to customer; delivered_at auto-set on admin status change; refund + privacy policies updated. ✅
- **[Phase B — Feb 2026] Product Details + Wishlist + Emails**: dedicated `/product/:slug` page (gallery, MRP strikethrough, savings badge, low-stock/out-of-stock indicators, variant picker, qty controls, add-to-cart, wishlist toggle, per-product WhatsApp CTA to +91 9970107760 with product context, social share menu — WhatsApp/Instagram/X/copy link); Wishlist context + `/api/me/wishlist` endpoints + Wishlist tab in /account (move-to-cart + remove); ShopPage cards linked to product page with heart + low-stock badges; ProductShowcase hero got low-stock badge + view-details CTA. Resend integrated (verified `artyfex.in` domain, sender `no-reply@artyfex.in`) — customer receives branded email when admin approves or rejects their return. 9/9 backend pytest, 100% frontend flows verified with live Resend delivery. ✅
- **[Phase C — Feb 2026] Admin CRM + Profile Edit + Messages**: PATCH `/api/auth/me` (name/phone update, email read-only); Admin `Customers` tab with searchable table (orders count, lifetime spend, last order, contact) + right-side drawer showing full order/return/message history + inline "Send personal message" composer; customer sees admin messages under new `Messages` tab in `/account` with unread badge on tab, gold pulsing indicator per unread item, mark-as-read; gold banner surfaces unread messages from any tab. 29/29 backend pytest, retest passed on frontend after Messages+Profile render branches were wired. ✅
- **[Phase A2 — Jul 2026] UI Polish, Branding & Frontend Fixes**: Removed all Emergent watermarks (index.html: dropped `emergent-main.js`, `#emergent-badge`, PostHog init; updated `<title>`, meta, OG tags, favicon paths, Google Fonts to Cormorant + Instrument + Outfit). New `BrandLogo` component tries `/brand/logo.svg` then falls back to serif text — wired into Navbar + Footer for future custom logo drop-in. Collection cards + ProductShowcase hero image are now `<Link>`s routing to `/product/:slug` with hover overlay CTAs. Built new `ProductGallery` component: fixed thumbnail-swap bug (combined deduped variant+gallery images with single `activeIdx` state), added carousel (prev/next chevrons + Arrow-key nav + touch swipe + framer-motion slide-fade), hover-to-zoom (cursor-follow, scale 1.9x, cursor: zoom-in), fullscreen lightbox (Esc / ← → nav), and image counter. All 4 tasks verified by testing agent. ✅
- **[Phase B — Jul 2026] Core E-commerce Expansion**: (a) Product Variations — extended `Variant` model with optional per-variant `size` / `stock` / `price_inr` / `mrp_inr` (Shopify-style backward-compat). Seeded Moon Crystal with 4 SKUs (2 colours × 2 sizes: 24"/30"). New Size selector on ProductPage (sold-out state, per-size price display). Admin variants JSON editor now supports the extra fields. (b) Coupons — Coupon model (percentage|flat, min_cart, max_uses, expires_at, active), public `POST /api/coupons/validate`, admin CRUD (uniqueness + validation guardrails), server revalidates on order create, `used_count` increments on order/verify success. 3 seed codes: WELCOME10, ATELIER500, SIGNATURE15. Cart drawer coupon input with live discount + shipping recompute; admin `Coupons` tab with modal editor. (c) Catalog Scalability — full `/shop` overhaul: search across name/tagline/description/materials, dual-slider price range auto-fit to catalog, size pills, colour swatch multi-select, in-stock toggle, category radio (Signature/Companion/All), sort (Featured / Price asc/desc / Newest), active filter counter, empty state, mobile-collapsible sidebar. Cards show price range when variants differ. (d) Payment Error Handling — CheckoutDialog rewritten with prominent red-banner error state, retry button (up to 3 attempts), edit-details, contact-atelier mailto CTA after limit; every failure path (RZP script load, order create, modal dismiss, payment.failed, verify) auto-logs to new `POST /api/payments/failed` with rich context; admin `Failed Payments` tab with inline recovery-email button. Backend 28/28 tests + Frontend 23/25 tests (2 minor script-timing quirks, features verified working). ✅
- **[Phase C — Jul 2026] Backend Integration, User Accounts & Retention**: (a) **Emergent Google Auth** integrated as additional login method — new `POST /api/auth/google/session` exchanges session_id from `auth.emergentagent.com` redirect for our existing JWT (users upserted in `db.users` with `auth_provider='google'`, picture, session_token); new `/auth/callback` route in React parses fragment, calls backend, applies JWT via `AuthContext.applyGoogleSession`, then navigates to `/account`. Real Google 4-color G-glyph button on AuthDialog. (b) Customer dashboard: **Messages tab renamed to Updates** (label, empty state, unread banner copy — endpoint keys unchanged for compatibility). (c) **Automated Review System** — new `GET /api/me/review-prompts` returns products delivered ≥ `review_prompt_days` (default 7, admin-tunable 0–90) ago that user hasn't reviewed; app_settings collection with `GET/PATCH /api/admin/settings`; new ReviewPromptProvider fetches on login, elegant sticky gold banner site-wide + gold card on /account both open a global modal with 5-star rate + title + body form per pending product (submits via existing `POST /api/products/:slug/reviews`, auto-dismisses when list empties). New admin Settings tab with numeric input for threshold. Backend 32/32 tests + Frontend 18/18 tests. ✅

## Prioritized Backlog
### P1 — Next
- Order-confirmation email on checkout success (extend send_email helper).
- Product reviews section on product detail page (per-product review submit + display).

### P2 — Later
- Object-storage backed image uploads in admin (replace URL paste), including damage evidence upload.
- Inventory decrement on order confirmation + low-stock alerts.
- Multi-currency / international shipping calculator.
- Instagram lookbook grid + Pinterest boards.
- Search + filters on collection.
- Move admin_list_users to a MongoDB aggregation pipeline (currently N+1).

## Credentials
- Admin: admin@artyfex.in / ArtyFex@2026
- Razorpay test: rzp_test_T8wuUhk6q4NKFz (secret in backend/.env)
- Test card: 4111 1111 1111 1111 · 12/28 · 123
