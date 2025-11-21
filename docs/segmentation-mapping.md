# Segmentation Mapping Rules (FTP Engine)

Segmentation resolves each position to exactly one segment. Evaluation is deterministic, using either direct match (hash/key) or ordered rules (first match wins).

## Data Inputs
- Position fields: product_type, subtype/product, customer_type, geo (country/state), balance, rate, nmd_flag, stability_segment, beta_to_policy_rate, decay_half_life_days, modeled_life_years, branch_id, channel.
- Config: segment definitions with criteria, priority, curve_id, and ticket_strategy.

## Evaluation Modes
1) Direct match (hash/key):
   - Build a composite key (e.g., product_type + customer_type + geo + nmd_flag) to a segment_id.
   - Fast path for well-defined products (e.g., time deposits, wholesale).
2) Ordered list:
   - Rules evaluated in ascending priority; first match wins.
   - Use for NMD cohorts where behavior bands are needed (balance band, beta band, stability segment).

## Example YAML Config
```yaml
segments:
  - id: td_corp
    name: Corp Time Deposits
    product_type: deposit
    criteria:
      all:
        - field: product
          op: in
          value: [time]
        - field: customer_type
          op: eq
          value: corp
    curve_id: ftp_term_curve
    modeled_term_months: remaining_term  # match-funded
    ticket_strategy: match_funded
    overnight_share: 0.0
    priority: 10

  - id: nmd_retail_stable
    name: Retail NMD Stable
    product_type: deposit
    criteria:
      all:
        - field: product
          op: in
          value: [demand, savings]
        - field: customer_type
          op: eq
          value: retail
        - field: balance
          op: between
          value: [0, 100000]
        - field: stability_segment
          op: eq
          value: stable
    curve_id: ftp_ois_curve
    modeled_term_months: 18
    ticket_strategy: ladder
    overnight_share: 0.1
    priority: 20

  - id: nmd_retail_volatile
    name: Retail NMD Volatile
    product_type: deposit
    criteria:
      all:
        - field: product
          op: in
          value: [demand, savings]
        - field: customer_type
          op: eq
          value: retail
        - field: stability_segment
          op: eq
          value: volatile
    curve_id: ftp_ois_curve
    modeled_term_months: 6
    ticket_strategy: ladder
    overnight_share: 0.5
    priority: 30

  - id: nmd_sme_mid
    name: SME NMD Mid Balances
    product_type: deposit
    criteria:
      all:
        - field: product
          op: in
          value: [demand, savings]
        - field: customer_type
          op: eq
          value: SME
        - field: balance
          op: between
          value: [100000, 1000000]
    curve_id: ftp_ois_curve
    modeled_term_months: 12
    ticket_strategy: ladder
    overnight_share: 0.25
    priority: 40

  - id: wholesale_all
    name: Wholesale Funding
    product_type: wholesale
    criteria:
      all:
        - field: product
          op: any
          value: []
    curve_id: ftp_term_curve
    modeled_term_months: remaining_term
    ticket_strategy: match_funded
    overnight_share: 0.0
    priority: 90
```

## Resolution Algorithm (pseudo)
1) Try direct match table if a composite key exists; if found, assign segment_id.
2) Else iterate segments ordered by priority; evaluate criteria (AND/OR as defined); first match wins.
3) Ticketing depends on ticket_strategy:
   - match_funded: one ticket per instrument_id (no aggregation).
   - ladder: aggregate positions by segment (instrument_ids dropped) then ladder tickets (overnight + modeled term); tickets carry `side` (asset/liability) for reporting.
4) If no match: flag to "unassigned" segment or raise for data-quality review.

## Notes
- Keep priorities sparse (10,20,30...) to allow inserts.
- Criteria ops: eq, in, between, gt, gte, lt, lte, any.
- modeled_term_months can be numeric or `remaining_term` for match-funded items.
- Overnight/ladders computed after segment resolution; ticket_strategy is explicit in segment definitions.
