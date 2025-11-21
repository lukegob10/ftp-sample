# Bank Assets & Liabilities Dataset Guide

## 1. Purpose
- Define simplified balance sheet components so we can synthesize a sample dataset for portfolio simulation.
- Keep scope lean: core retail/commercial bank with typical asset/liability mix; no exotic derivatives.

## 2. Assumptions
- Currency: single (e.g., USD).  
- Reporting date: snapshot basis (T0) with optional monthly history.  
- Accounting: amortized cost for loans; fair value for trading securities; FVOCI for AFS.  
- Risk tagging: internal rating scale 1–10; regulatory classes (e.g., pass/special mention/substandard).

## 3. Balance Sheet High-Level
- Assets: cash & reserves, securities (AFS/HTM/trading), loan portfolio (retail, SME, CRE), other assets (fixed assets, accruals).  
- Liabilities: deposits (demand, savings, time), wholesale funding (repos, term debt), other liabilities (accrued expenses).  
- Equity: CET1/tiered capital (optional for dataset completeness).

## 4. Asset Breakdown & Fields
- Cash & Reserves: account_id, currency, balance, institution (central bank/correspondent), reserve_flag.  
- Securities:
  - Common fields: security_id, type (gov/agency/corp), classification (AFS/HTM/trading), issuer_country, coupon_type (fixed/floating), coupon_rate, frequency, issue_date, maturity_date, face_value, book_value, fair_value, duration, convexity, rating (S&P/Moody’s/internal), accrued_interest.
  - Market data: price, yield_to_maturity, oas, spread_benchmark.
- Loans:
  - Common: loan_id, segment (mortgage/auto/consumer/SME/CRE), product_type, origination_date, maturity_date, amortization_type, rate_type (fixed/variable), rate_index, spread_bps, current_rate, payment_frequency, principal_origination, principal_outstanding, accrued_interest.
  - Credit quality: internal_rating, pd_annualized, lgd, ead, days_past_due, npl_flag, forbearance_flag, collateral_type, collateral_value.
  - Geography: country, state, zip, branch_id.
  - Behavior: prepayment_penalty_flag, prepayment_speed, utilization (for revolving).
- Other Assets (optional): fixed_asset_id, book_value, depreciation_method, remaining_life_years.

## 5. Liability Breakdown & Fields
- Deposits:
  - Common: deposit_id, customer_type (retail/SME/corp), product (demand/savings/time), open_date, maturity_date (time), rate_type (fixed/teaser/variable), rate, balance, currency, branch_id.
  - Behavior: withdrawal_limit, early_withdrawal_penalty, avg_balance_30d, inflow_rate, outflow_rate.
  - Non-maturity deposits (NMDs): nmd_flag, stability_segment (stable/volatile), beta_to_policy_rate, decay_half_life_days, modeled_life_years, runoff_rate_stress.
- Wholesale Funding:
  - Common: funding_id, type (repo/term_debt/subordinated), counterparty_type, issue_date, maturity_date, notional, rate_type, rate, collateral_type (for repo), haircut, covenant_flags.
  - Market: current_spread, benchmark (SOFR/EURIBOR), fair_value.
  - Other Liabilities (optional): accrued_expense_id, type, amount, due_date.
  - Equity (optional): tier, amount, issuance_date, maturity_date (if AT1/T2), coupon_rate.

## 6. Dataset Shape & Constraints
- Row counts: aim for 5–10k loans, 500–2k securities, 50–200 wholesale lines, 20–50k deposits (wide behavior distribution).  
- Balancing: Assets ≈ Liabilities + Equity (allow small imbalance for realism: ±0.5%).  
- Data quality: enforce referential integrity (branch/customer ids), non-negative balances, dates ordered (origination < maturity).  
- Rates: keep within realistic ranges (deposits 0–5%, loans 2–12%, spreads 50–400 bps).  
- Credit: PD/LGD consistent with rating buckets; collateral_value ≥ principal for secured CRE/mortgage, else flagged.

## 7. Sample Schemas (flat tables)
```
assets_cash(currency, account_id, balance, institution, reserve_flag)
assets_securities(security_id, type, classification, coupon_type, coupon_rate, issue_date, maturity_date, face_value, book_value, fair_value, duration, convexity, rating, price, ytm, oas, spread_benchmark, accrued_interest, issuer_country)
assets_loans(loan_id, segment, product_type, origination_date, maturity_date, rate_type, rate_index, spread_bps, current_rate, payment_frequency, principal_origination, principal_outstanding, accrued_interest, internal_rating, pd_annualized, lgd, ead, days_past_due, npl_flag, forbearance_flag, collateral_type, collateral_value, country, state, zip, branch_id, prepayment_speed, utilization)
liabilities_deposits(deposit_id, customer_type, product, open_date, maturity_date, rate_type, rate, balance, currency, branch_id, withdrawal_limit, early_withdrawal_penalty, avg_balance_30d, inflow_rate, outflow_rate, nmd_flag, stability_segment, beta_to_policy_rate, decay_half_life_days, modeled_life_years, runoff_rate_stress)
liabilities_wholesale(funding_id, type, counterparty_type, issue_date, maturity_date, notional, rate_type, rate, collateral_type, haircut, current_spread, benchmark, fair_value, covenant_flags)
equity(optional_id, tier, amount, issuance_date, maturity_date, coupon_rate)
```
- All rows include `end_of_period_balance`; assets are positive, liabilities/equity are negative to allow a single signed balance sheet.

## 8. Generation Tips
- Randomize by segment distributions (e.g., retail mortgages 40%, auto 15%, SME 20%, consumer 15%, CRE 10%).  
- Correlate rates with term and credit quality; add seasonal patterns to deposits; include churn simulation via outflow_rate.  
- Inject noise: small missing values, mild outliers, a few NPLs and forbearance cases for testing risk logic.  
- NMD realism: set stable vs volatile mixes, different betas to policy rates, and varying half-lives to test interest-sensitivity.  
- Provide at least one snapshot plus a 6–12 month history for trend-based analytics if needed.

## 9. Outputs to Produce
- CSVs per table above, plus a simple balance sheet summary (totals by class) to validate balancing.  
- Optional: parquet versions for bulk processing; JSON small sample for docs/tests.
