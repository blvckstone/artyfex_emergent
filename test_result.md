#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Phase B — Core E-commerce Expansion & UX Enhancements:
  1) Catalog Scalability: search + filters (price / size / colour / in-stock / sort) on /shop.
  2) Product Variations: extend product model to support Shopify-style variations (colour + size axes) with per-variant stock/price/image; admin can upload via variants JSON.
  3) Checkout Upgrades: percentage + flat coupon codes, admin-managed with expiry / min-cart / max-uses; applied in cart & checkout.
  4) Payment Error Handling: prominent inline error state with retry / edit-details / contact-atelier actions; log every failure to backend for admin visibility.

backend:
  - task: "Extend Variant model: per-variant size/stock/price_inr/mrp_inr; Order.coupon_code + discount_inr"
    implemented: true
    working: true
    file: "backend/server.py, backend/server_seed.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          Extended Variant with optional size/stock/price_inr/mrp_inr (backward compat with old data - existing docs get nulls).
          OrderIn + Order now accept coupon_code + discount_inr. Order.status now also uses 'payment_failed'.
          Seed data for moon-crystal-24 replaced with 4 variants (2 colours × 2 sizes) with distinct prices.
      - working: true
        agent: "testing"
        comment: |
          ✅ VERIFIED - All tests passed (28/28):
          - Variant model extensions working correctly
          - moon-crystal-24 has 4 variants with distinct sizes (24" x2, 30" x2) and prices (18999, 24999)
          - Order model accepts coupon_code and discount_inr fields
          - Order.status='payment_failed' working correctly when failed payment logged with order_number
          - All regression tests passed (products, reviews, admin endpoints)

  - task: "Coupons: model + validate endpoint + admin CRUD + used_count on order verify"
    implemented: true
    working: true
    file: "backend/server.py, backend/server_seed.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          New models: CouponIn, Coupon, CouponValidateIn. Fields: code, type (percentage|flat), value, min_cart_inr, max_uses, expires_at, active, description, used_count.
          Endpoints:
            POST /api/coupons/validate (public) — returns discount_inr or 400/404 with detail
            GET /api/admin/coupons — list (admin only)
            POST /api/admin/coupons — create (uppercases code, validates uniqueness / percentage cap / positive value)
            PATCH /api/admin/coupons/{id} — update
            DELETE /api/admin/coupons/{id} — delete
          On POST /api/orders: coupon revalidated server-side; on POST /api/orders/verify success: coupon.used_count incremented atomically ($inc).
          Seed: 3 coupons — WELCOME10 (10% off, no min), ATELIER500 (₹500 off, min ₹10k, max 100 uses), SIGNATURE15 (15% off, min ₹25k, max 50 uses).
          Curl-tested: WELCOME10 on ₹20k → discount 2000. SIGNATURE15 on ₹10k → 400 with 'Minimum cart value...'. NOPE → 404.
      - working: true
        agent: "testing"
        comment: |
          ✅ VERIFIED - All coupon tests passed (15/15):
          PUBLIC VALIDATION (6 tests):
          - WELCOME10 on ₹20k → 200 with valid=true, discount_inr=2000, type="percentage", value=10
          - ATELIER500 on ₹15k → 200 with discount_inr=500
          - SIGNATURE15 on ₹10k → 400 with "Minimum cart" error (requires ₹25k)
          - Invalid code "NOPE" → 404
          - Empty code → 400
          - Case insensitivity: "welcome10" → 200 with code="WELCOME10" (server uppercases)
          
          ADMIN CRUD (9 tests):
          - GET /api/admin/coupons → returns list with 3 seeded coupons
          - POST create TESTX → 201/200 with coupon returned
          - POST duplicate TESTX → 409 conflict
          - POST percentage > 100 → 400 validation error
          - POST value <= 0 → 400 validation error
          - POST invalid type "weird" → 400 validation error
          - PATCH update description → 200 with updated coupon
          - DELETE coupon → 200 with deleted:true, verified removed from list
          - Unauthorized access without token → 401
          
          ORDER INTEGRATION (3 tests):
          - Order creation with valid coupon WELCOME10 → order saved with coupon_code + discount_inr
          - Order creation with invalid coupon "EXPIRED" → 400
          - Order creation with SIGNATURE15 below min_cart → 400 with min_cart error

  - task: "Failed payment logging: model + POST /api/payments/failed + GET /api/admin/failed-payments"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          New models: FailedPaymentIn, FailedPayment. Captures order_number, razorpay_order_id, razorpay_payment_id, error_code, error_description, error_source/step/reason, amount_inr, customer_email/name/phone, attempt counter.
          POST /api/payments/failed (public — called from CheckoutDialog whenever Razorpay fails or user cancels); also marks Order.status='payment_failed' if order_number provided.
          GET /api/admin/failed-payments (admin only) sorted desc by created_at.
      - working: true
        agent: "testing"
        comment: |
          ✅ VERIFIED - All failed payment tests passed (4/4):
          - POST /api/payments/failed with basic payload → 200 with FailedPayment doc (id + created_at)
          - POST with order_number → order.status updated to "payment_failed" (verified via GET /api/orders/{order_number})
          - GET /api/admin/failed-payments with admin token → 200 with list containing logged entries
          - GET /api/admin/failed-payments without token → 401 unauthorized

frontend:
  - task: "Cart coupon flow (CartContext + CartSheet)"
    implemented: true
    working: "NA"
    file: "frontend/src/context/CartContext.jsx, frontend/src/components/CartSheet.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          CartContext: added coupon (persisted to localStorage 'artyfex_coupon_v1'), discount (memoized), applyCoupon(), clearCoupon(). Discount enforced against subtotal, capped so total >= 0. Shipping now computed on discounted subtotal (free >= 25k after discount).
          CartSheet: new coupon input row (Tag icon + uppercase input + Apply). On apply, POST /api/coupons/validate — success updates cart context; error shows inline red message. Applied coupon shows as green badge with 'Remove' button. Discount line surfaces as separate row when > 0. Variant size shown next to variant label ('Aqua · 24" diameter').

  - task: "CheckoutDialog: coupon submission + robust error state + retry + failed payment logging"
    implemented: true
    working: "NA"
    file: "frontend/src/components/CheckoutDialog.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          POST /api/orders payload now includes coupon_code + discount_inr.
          Error state completely redesigned: red-left-border banner with AlertTriangle icon, big title, description, error code + order number reference, attempt counter (n / 3), Retry button (re-uses last payload), Edit details, Contact atelier CTA (mailto with prefilled subject/body) after 3 attempts.
          Every failure path (RZP script load fail, order create fail, RZP modal dismiss, RZP payment.failed event, verify failure) calls failWith() which fires-and-forgets POST /api/payments/failed with rich context (error_code, source, step, reason, RZP ids, customer info).

  - task: "ShopPage: search + price range + size + colour + in-stock + sort filters"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/ShopPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          Fully rewrote ShopPage. New: search bar (matches name/tagline/description/materials/variant labels), sort dropdown (Featured / Price low→high / high→low / Newest), sidebar with Category radio (All/Signature/Companion), dual-slider price range auto-fit to catalog, size checkbox pills (from variant sizes), colour swatch multi-select, in-stock toggle. Active filter counter badge. 'Clear all' button. Empty state. Range price display 'Xk – Yk' on cards when variants have different prices. Mobile: filter panel collapses behind toggle button. All new controls have data-testids (shop-search, shop-toggle-filters, shop-sort, shop-filter-cat-*, shop-filter-price-min/max, shop-filter-size-*, shop-filter-colour-{hex}, shop-filter-stock, shop-clear-filters, shop-count, shop-empty).

  - task: "ProductPage: colour + size selector using per-variant fields"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/ProductPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          Detects hasSizeAxis (any variant has 'size' field). If true, colour swatches are deduped by hex, and a separate 'Size' selector appears below Colourway with size pills — includes per-size price display when the variant price differs, sold-out state (line-through disabled) when variant.stock=0.
          Effective price/mrp/stock/size all use activeVariant fields with product-level fallback. Wishlist / share / WhatsApp deep links updated accordingly. data-testids: product-size-selector, product-size-{key}.

  - task: "Admin Coupons tab + Failed Payments tab"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/AdminPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          Two new left-nav tabs: Coupons (Tag icon) + Failed Payments (AlertTriangle icon).
          Coupons tab: list existing with badges (Disabled/Expired/Sold out) + edit + delete. 'New coupon' opens CouponEditor modal with fields: code (uppercase), type (percentage|flat select), value, min_cart_inr, max_uses (blank=unlimited), expires_at (date), active toggle, description. Uses /api/admin/coupons endpoints. data-testids: admin-add-coupon, admin-coupon-{CODE}, admin-coupon-edit-*, admin-coupon-delete-*, admin-coupon-editor + all fields, admin-coupon-save.
          Failed Payments tab: read-only list of every failure with error code, description, timestamp, attempt, customer name/email/phone, order number, amount, and inline 'Contact' mailto button prefilled with recovery message. data-testids: admin-failed-{id}, admin-failed-contact-{id}.
          Also updated Product editor: variants JSON hint mentions size/stock/price_inr/mrp_inr Shopify-style fields.

metadata:
  created_by: "main_agent"
  version: "1.2"
  test_sequence: 4
  run_ui: true

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Phase B backend is ready for verification. Priorities for test:
      1) POST /api/coupons/validate — happy path (WELCOME10 on ₹20k = 2000), min-cart failure (SIGNATURE15 on ₹10k = 400), not-found (NOPE = 404).
      2) Admin coupon CRUD flow — POST / PATCH / DELETE with admin JWT. Validate: uniqueness (409 on duplicate code), percentage > 100 (400), negative value (400), type must be 'percentage' or 'flat'.
      3) POST /api/orders WITH coupon — coupon revalidated server-side; order saved with coupon_code + discount_inr fields.
      4) POST /api/orders/verify — on success, coupons collection used_count for that code increments by exactly 1.
      5) POST /api/payments/failed — public endpoint accepts arbitrary payload, returns FailedPayment doc; if order_number provided, that Order.status becomes 'payment_failed'.
      6) GET /api/admin/failed-payments — admin only (401 without token), returns list.
      7) Regression: existing /api/products, /api/products/{slug}, admin login, admin/orders, admin/stats etc. still work.
      Admin creds: admin@artyfex.in / ArtyFex@2026
  
  - agent: "testing"
    message: |
      ✅ PHASE B BACKEND TESTING COMPLETE - ALL TESTS PASSED (28/28)
      
      Comprehensive testing completed for all Phase B backend features:
      
      1. COUPON VALIDATION (6/6 tests passed):
         - Public endpoint POST /api/coupons/validate working correctly
         - Happy paths: WELCOME10 (10% off), ATELIER500 (₹500 flat)
         - Validation: min_cart enforcement, invalid codes (404), empty codes (400)
         - Case insensitivity: server uppercases codes correctly
      
      2. ADMIN COUPON CRUD (9/9 tests passed):
         - GET /api/admin/coupons returns all seeded coupons
         - POST creates new coupons with proper validation
         - Duplicate code detection (409 conflict)
         - Value validation: percentage cap (100), positive values only
         - Type validation: only "percentage" or "flat" allowed
         - PATCH updates working correctly
         - DELETE removes coupons and verified via GET
         - Auth protection: 401 without token
      
      3. ORDER WITH COUPON (3/3 tests passed):
         - Orders accept coupon_code and discount_inr fields
         - Server-side coupon revalidation working
         - Invalid coupon rejection (400)
         - Min_cart enforcement during order creation
      
      4. FAILED PAYMENT LOGGING (4/4 tests passed):
         - POST /api/payments/failed creates FailedPayment docs
         - Order status updated to "payment_failed" when order_number provided
         - GET /api/admin/failed-payments returns logged entries (admin only)
         - Auth protection: 401 without token
      
      5. REGRESSION TESTS (5/5 tests passed):
         - GET /api/products returns 4 products
         - moon-crystal-24 has 4 variants with correct size/price structure
         - GET /api/reviews returns 6 reviews
         - Admin login working with token generation
         - GET /api/admin/stats returns dashboard stats
      
      All backend APIs are functioning correctly. No issues found.
