# Product Requirements Document

## Product Overview

- **Name**: A website for finding rare stuffies (working title)
- **Value Proposition**: Make it easy for collectors to find out-of-production stuffies
- **Type**: Web application
- **Category**: E-commerce / Marketplace

## Vision and Problem Statement

### Problem

It's hard to find out-of-production stuffed animals. Collectors looking for
specific rare or discontinued stuffies have no dedicated marketplace; they
must wade through general-purpose platforms where discovery is poor and
relevant inventory is buried among unrelated listings.

### Vision

A dedicated marketplace where any stuffie collector can describe what
they're looking for in plain language and quickly find — and bid on — the
exact rare or discontinued stuffed animal they want.

### How People Solve This Today

Collectors rely on eBay. eBay's general-purpose keyword search and category
structure are inadequate for finding rare, discontinued stuffed animals
described in collector-specific language (character name, year, edition,
distinguishing features). Listings are buried among unrelated toys, and
sellers don't consistently use collector vocabulary.

## Target Audience

### Primary Users

- **Who**: A stuffie collector — an individual consumer searching for rare
  or out-of-production stuffed animals to add to their collection.
- **Pain Point**: Can't find the stuffies they want.
- **Current Solution**: Browsing and searching eBay.

### Secondary Users

Two distinct user types:

- **Buyers** — search for stuffies, favorite listings, place bids.
- **Sellers** — list stuffies with a photo and description.

(Most users are expected to act primarily as one or the other, though a
single account can do both.)

## Features

### MVP (Must Have)

- [ ] Email-based authentication (signup / login)
- [ ] Sellers can create a stuffie listing with at least one photo and a description
- [ ] Buyers can favorite stuffies
- [ ] Buyers can place bids on a stuffie
- [ ] Natural-language search for stuffies (the differentiating capability)

### Out of Scope (v1)

- Non-stuffie toys (action figures, dolls, plush-adjacent collectibles, etc.)
- Native mobile apps (web only for v1)
- Seller payouts / escrow / dispute handling beyond a minimum to support bidding
- Shipping integrations and label generation

### Core Value Proposition

The product must do **one thing exceptionally well**: let collectors search
for stuffies using natural language (e.g., "1990s Beanie Baby with the
heart tag still attached" or "discontinued Steiff bear from the 80s") and
surface the right listings.

## Success Metrics

| Metric                          | Target (3 months)            |
|---------------------------------|------------------------------|
| Primary: Monthly active users   | 100                          |
| Secondary: Listings created     | TBD (set after early traffic)|
| Secondary: Bids placed          | TBD (set after early traffic)|

## Competitive Analysis

| Competitor | Strength                                         | Weakness                                                          | Our Differentiator                                                  |
|------------|--------------------------------------------------|-------------------------------------------------------------------|---------------------------------------------------------------------|
| eBay       | Massive inventory, established trust and bidding | Generic search, not tuned for collector vocabulary; no curation   | Natural-language search tuned for stuffie collectors                |

## Constraints and Requirements

- **Timeline**: 2-3 months to launch (target: July-August 2026)
- **Budget**: No major constraints reported
- **Technical**: Google Cloud Platform, Neon (serverless Postgres),
  FastAPI (Python). Aligns with the stack defined in `CLAUDE.md`.
- **Team**: No major constraints reported

## Non-Functional Requirements

| Category      | Requirement                                                                                    |
|---------------|------------------------------------------------------------------------------------------------|
| Security      | Email-based auth; user passwords stored hashed; bidding actions require authentication.        |
| Performance   | Search results return in under ~1s for typical queries on launch-scale inventory.              |
| Scalability   | Sized for ~100 MAU at 3 months; Cloud Run + Neon scale-to-zero is sufficient.                  |
| Accessibility | Reasonable WCAG 2.1 AA effort for v1 (semantic HTML, alt text on listing photos, keyboard nav).|

## Dependencies

- Google Cloud Platform (Cloud Run, Artifact Registry, Secret Manager)
- Neon (serverless Postgres with per-PR branching)
- An embedding / LLM provider for natural-language search (specific
  provider deferred to `/bootstrap-architecture`)

## Risks and Mitigations

| Risk                                                                                                  | Impact | Mitigation                                                                                      |
|-------------------------------------------------------------------------------------------------------|--------|--------------------------------------------------------------------------------------------------|
| Natural-language search doesn't feel meaningfully better than eBay's keyword search.                  | High   | Invest in collector-vocabulary tuning early; dogfood with real collector queries before launch. |
| Cold-start: not enough listings for buyers to find anything interesting.                              | High   | Seed listings via early seller outreach in collector communities before public launch.          |
| Bidding without payments / escrow leads to abandoned bids and bad buyer experience.                   | Medium | Keep v1 bidding lightweight (signal of intent), explicitly defer settlement to v2.              |
| Counterfeit or misrepresented listings (fake "rare" stuffies) damage trust.                           | Medium | Lightweight reporting flow in MVP; build out moderation post-launch.                            |

## Glossary

| Term            | Definition                                                                            |
|-----------------|---------------------------------------------------------------------------------------|
| Stuffie         | A stuffed animal / plush toy. The only product category in scope for v1.              |
| Out-of-production| A stuffie that the original manufacturer no longer produces. Core target inventory.   |
| Listing         | A single stuffie offered for sale by a seller, with photo(s) and description.         |
| Bid             | A buyer's offer on a listing. v1 captures intent; settlement is post-MVP.             |
| Favorite        | A buyer's saved listing, for tracking interest over time.                             |
