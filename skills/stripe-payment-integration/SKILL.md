---
name: stripe-payment-integration
description: >-
  Architects secure payment flows, subscriptions, checkout sessions, and idempotent
  webhook handlers using Stripe and modern billing APIs. Inspired by
  stripe/stripe-best-practices. Use when monetizing SaaS apps, websites, or games.
---

# Stripe & Payment Integration Best Practices

Inspired by `stripe/stripe-best-practices`. Use this skill whenever implementing payments, subscriptions, credits, or billing webhooks.

## 1. Golden Rules of Payment Engineering

1. **Never Trust Client-Side Amounts**:
   - Never accept `price` or `amount` from the frontend request body. Send only `priceId` or `productId` and look up the authoritative price on the server.
2. **Webhook Signature Verification is Mandatory**:
   - Always verify `stripe-signature` using the raw request body (`stripe.webhooks.constructEvent(rawBody, sig, webhookSecret)`) before processing any billing event.
3. **Idempotent Webhook Processing**:
   - Payment providers may deliver the same webhook event multiple times. Store processed `event.id` values in a `processed_webhook_events` table and ignore duplicates.
4. **Integer Minor Units (Cents / Qəpik)**:
   - Store and calculate all monetary values as integers in the smallest currency unit (e.g., `1999` for `$19.99` or `19.99 AZN`) or `NUMERIC(12,2)`—never IEEE 754 floating-point (`float`/`double`).

## 2. Subscription Lifecycle Checklist
- Handle `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, and `customer.subscription.deleted`.
- Sync subscription status (`active`, `past_due`, `canceled`, `trialing`) and `current_period_end` directly to your database so access checks are fast local DB reads.
