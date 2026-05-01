# Product Roadmap

## Overview

A web marketplace dedicated to rare and out-of-production stuffies, where
collectors can search in natural language, favorite finds, and bid on
listings. Targeting a 2-3 month path to MVP launch (roughly July-August
2026), with a primary goal of reaching 100 monthly active users within
3 months of launch.

## Phase 1: MVP

- **Target**: Launch in 2-3 months (≈ July-August 2026)
- **Goal**: Deliver the core value proposition — collectors can find and
  bid on out-of-production stuffies via natural-language search.

### Features

| Feature                                                  | Priority | Status   |
|----------------------------------------------------------|----------|----------|
| Email-based auth (signup / login)                        | P0       | Backlog  |
| Seller can create a listing (photo + description)        | P0       | Backlog  |
| Buyer can favorite a stuffie                             | P0       | Backlog  |
| Buyer can bid on a stuffie                               | P0       | Backlog  |
| Natural-language search for stuffies                     | P0       | Backlog  |
| Basic user profile / "my listings" + "my favorites"      | P1       | Backlog  |
| Lightweight listing report / flag flow                   | P1       | Backlog  |

### Success Criteria

- [ ] 100 monthly active users within 3 months post-launch
- [ ] Natural-language search returns relevant results for collector queries
      (validated against a hand-built eval set before launch)
- [ ] At least one healthy seed of seller listings before public launch

## Phase 2: Iteration

- **Target**: Post-MVP (1-2 months after launch)
- **Goal**: Improve discovery, listing quality, and trust based on real
  user behavior.

### Features

| Feature                                                          | Priority | Status   |
|------------------------------------------------------------------|----------|----------|
| Search-quality improvements driven by query/click logs           | TBD      | Backlog  |
| Saved searches / alerts ("notify me when X is listed")           | TBD      | Backlog  |
| Richer listing fields (era, manufacturer, edition, condition)    | TBD      | Backlog  |
| Seller reputation / ratings                                      | TBD      | Backlog  |
| Improved bid mechanics (bid expiry, counter-offers)              | TBD      | Backlog  |

### Success Criteria

- [ ] Repeat-visitor / retention metric established and trending up
- [ ] Increase in listings created per active seller

## Phase 3: Growth

- **Target**: 3-6 months post-launch
- **Goal**: Scale, expand category depth, and harden trust + payments.

### Features

| Feature                                                          | Priority | Status   |
|------------------------------------------------------------------|----------|----------|
| Payments / escrow for bids                                       | TBD      | Backlog  |
| Shipping label / tracking integration                            | TBD      | Backlog  |
| Moderation tooling for fake / misrepresented listings            | TBD      | Backlog  |
| Collections / wishlists shared between collectors                | TBD      | Backlog  |

## Milestone Definitions

| Milestone               | Criteria                                                              | Target Date     |
|-------------------------|-----------------------------------------------------------------------|-----------------|
| M1: MVP Launch          | All Phase 1 P0 features live; first sellers seeded; first bids placed | 2026-07/08      |
| M2: Product-Market Fit  | 100 MAU sustained; meaningful repeat-visit rate                       | 2026-10/11      |
| M3: Growth              | Payments / escrow live; listing count growing month-over-month        | 2027 H1         |

## Constraints and Risks

| Risk                                                                          | Phase | Mitigation                                                                  |
|-------------------------------------------------------------------------------|-------|------------------------------------------------------------------------------|
| Natural-language search doesn't feel better than eBay                         | 1     | Build a collector-query eval set; tune embeddings + ranking before launch.  |
| Cold-start (too few listings for buyers to find anything)                     | 1     | Seed sellers via collector communities before public launch.                |
| Bidding without payments creates a poor settlement experience                 | 1-2   | Scope v1 bidding as intent only; introduce payments in Phase 3.             |
| Counterfeit / misrepresented listings damage trust                            | 2-3   | Reporting flow in MVP; moderation tooling in Phase 3.                       |

## Dependencies

```text
Phase 1: MVP
    |
    v
Phase 2: Iteration (requires usage signal from Phase 1)
    |
    v
Phase 3: Growth (requires retention signal + listing volume from Phase 2)
```

## Revision History

| Date       | Change                                                  | Author |
|------------|---------------------------------------------------------|--------|
| 2026-05-01 | Initial roadmap from /bootstrap-product questionnaire   | kira-kim-11 |
