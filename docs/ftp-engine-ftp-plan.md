# FTP Engine Plan (Assets, NMD Segmentation, Tickets)

## Goal
Build an FTP engine that prices all assets/liabilities daily (as_of_date = today), supports match-funding for assets/time deposits (nettable via tickets), and models NMDs by behavioral segment with adjustable ticketing rules.

## Core Principles
- Assets: mostly match-funded; priced on their own term/rate curve (no explicit treasury transfer assumed; tickets can net internally).
- Time deposits: match-funded on original term; optional haircut/markup.
- NMDs: grouped into behavioral cohorts and modeled via tickets (overnight + ladder across tenor bucket). Unstable portions go to overnight; stable spreads evenly across modeled tenor.
- Config-driven: segmentation rules, stability fractions, ticket tenors/weights, and curve selection are adjustable without code changes.

## Data Model (base tables)
- positions (as_of_date, instrument_id, product_type [asset|deposit|wholesale], subtype, customer_segment, currency, balance, rate, origination_date, maturity_date, nmd_flag, stability_segment, beta_to_policy_rate, decay_half_life_days, modeled_life_years, runoff_rate_stress)
- segments (segment_id, name, product_type, criteria_json, stability_share, modeled_term_months, overnight_share, ticket_strategy [match_funded|ladder], curve_id, notes)
- curves (curve_id, name, daycount, points_json or curve_ref)
- tickets (ticket_id, segment_id, tenor_days, weight, bucket_type [overnight|ladder], active_flag)
- ftp_results (as_of_date, instrument_id, segment_id, ticket_id, tenor_days, assigned_rate, ftp_charge, ftp_credit, method, notes)

## Processing Flow
1) Load positions for as_of_date = today.
2) Segment deposits:
   - Evaluate criteria_json (e.g., customer_type, balance bands, rate betas, geography).
   - Derive stability_share and overnight_share from segment definition.
3) Ticketing:
   - If nmd_flag=1: issue 1 overnight ticket for overnight_share; issue N ladder tickets for remaining stability_share, evenly distributed across modeled_term_months (e.g., 18-month model → 18 tickets at 1/18 weight).
   - If time deposit: single ticket at remaining term (match-funded).
   - Assets: match-funded tickets at remaining term; allow overrides for prepay/shortening.
4) Pricing:
   - Pull the FTP curve for as_of_date (daily snapshot) per segment; map tenor to rate via interpolation. Current assumption: single OIS curve.
   - Price all tickets on that as_of_date curve using 30/360 day count for accrual math.
   - Add optional liquidity premiums or stability adjustments per segment.
5) Compute FTP:
   - ticket_strategy drives ticketing:
     - match_funded: one ticket per instrument_id (no aggregation).
     - ladder: aggregate positions by segment (instrument IDs dropped) then ladder tickets (overnight + modeled term).
   - ftp_charge/credit = balance * (assigned_rate - position_rate) * day_count_fraction.
   - Store per-ticket; ladder tickets are segment-level (no instrument IDs), match-funded are instrument-level.
6) Output results to ftp_results with signed balances (assets positive, liabilities negative) for a single balance sheet view.

## Configuration Adjustability
- segments: editable JSON/YAML defining criteria, stability/overnight shares, modeled_term_months, curve_id.
- tickets: generated dynamically based on modeled_term_months; allow manual overrides.
- curves: swap between curve sets (e.g., OIS, term SOFR) via curve_id; day count fixed at 30/360 for tickets.
- knobs: liquidity premium per tenor, floor/ceil on rates, scaling factors for unstable NMD share.

## Validation & Controls
- Balancing: sum of ticket weights per instrument = 1.0.
- Stability: stable_share + overnight_share = 1.0 for NMD segments.
- Time consistency: maturity_date >= as_of_date for term items; modeled_term_months > 0.
- Audit: store config version used; log segmentation/ticket assignments.
- Sensitivity: be able to rerun with alternative segment sets and compare deltas.

## Deliverables
- Config schema (segments/curves knobs).
- Engine module: segmentation, ticketing, pricing, FTP calc.
- CLI: run FTP for as_of_date (default today) and export results CSV/Parquet.
- Tests: segmentation correctness, ticket weights, curve interpolation, match-funding math, NMD overnight split and ladder distribution.
