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
- **[Phase A — Feb 2026] Returns Overhaul**: strict 3-day return window from delivery timestamp; customer return dialog with packaging warning + damage image URL + packaging confirmation checkbox; admin Returns tab with approve/reject + genuine assessment + admin notes to customer; delivered_at auto-set on admin status change; refund + privacy policies updated. 9/9 backend pytest passing, frontend flows verified. ✅

## Prioritized Backlog
### P1 — Next (Phase B — Product Details, Wishlist, Socials)
- Product Details Page `/product/:slug` — dedicated page, stock status ("low on stock"), MRP strikethrough beside sale price.
- Social share buttons on product page.
- Per-product WhatsApp CTA (+91 9970107760) with product context in message.
- Wishlist functionality (save products, wishlist tab in /account).
- Object-storage backed image uploads in admin (replace URL paste).
- Email confirmation on order (Resend/SendGrid).

### P2 — Later (Phase C — Admin CRM & Profile)
- Custom Admin-to-Customer messages displayed on targeted customer's dashboard.
- Admin Users tab (list registered users, industry-standard CRM options).
- Customer profile edit (name, phone) in /account.

### P3 — Backlog
- Inventory decrement on order confirmation + low-stock alerts.
- Multi-currency / international shipping calculator.
- Instagram lookbook grid + Pinterest boards.
- Search + filters on collection.

## Credentials
- Admin: admin@artyfex.in / ArtyFex@2026
- Razorpay test: rzp_test_T8wuUhk6q4NKFz (secret in backend/.env)
- Test card: 4111 1111 1111 1111 · 12/28 · 123
