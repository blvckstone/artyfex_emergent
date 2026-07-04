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
