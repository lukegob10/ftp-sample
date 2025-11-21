import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Deterministic seed for reproducible datasets.
random.seed(42)

OUTPUT_DIR = Path("data/balance_sheet")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_ASSETS = OUTPUT_DIR / "assets.csv"
OUTPUT_LIABILITIES = OUTPUT_DIR / "liabilities.csv"

TOTAL_BALANCE_SHEET = 100_000_000  # dollars

# Allocation targets as a share of total assets/liabilities.
ASSET_SPLIT = {
    "cash": 0.05,         # 5%
    "securities": 0.25,   # 25%
    "loans": 0.70,        # 70%
}

LIABILITY_SPLIT = {
    "deposits": 0.80,     # 80%
    "wholesale": 0.15,    # 15%
    "equity": 0.05,       # 5%
}


def _allocate(total: float, n: int, minimum: float = 0.5, maximum: float = 1.5):
    """Allocate 'total' across n buckets with soft randomness; returns list of floats that sum to total."""
    weights = [random.uniform(minimum, maximum) for _ in range(n)]
    weight_sum = sum(weights)
    allocations = []
    running_total = 0.0
    for i, weight in enumerate(weights, start=1):
        if i == n:
            amount = total - running_total
        else:
            amount = round(total * weight / weight_sum, 2)
            running_total += amount
        allocations.append(amount)
    return allocations


def _date_from_today(days_ahead: int) -> str:
    return (datetime.today() + timedelta(days=days_ahead)).date().isoformat()


def generate_cash_rows(total_cash: float, count: int = 10):
    rows = []
    amounts = _allocate(total_cash, count, 0.8, 1.2)
    for idx, balance in enumerate(amounts, start=1):
        rows.append(
            {
                "asset_id": f"C{idx:03d}",
                "category": "cash",
                "currency": "USD",
                "institution": random.choice(["Fed", "Correspondent", "On-us vault"]),
                "book_value": f"{balance:.2f}",
                "fair_value": f"{balance:.2f}",
                "rate": "0.00",
                "maturity_date": "",
                "end_of_period_balance": f"{balance:.2f}",
            }
        )
    return rows


def generate_security_rows(total_sec: float, count: int = 50):
    rows = []
    amounts = _allocate(total_sec, count, 0.4, 1.6)
    for idx, book_value in enumerate(amounts, start=1):
        coupon = random.uniform(1.0, 5.0)
        fair_value = round(book_value * random.uniform(0.98, 1.03), 2)
        term_days = random.randint(180, 3650)
        rows.append(
            {
                "asset_id": f"S{idx:03d}",
                "category": "security",
                "type": random.choice(["UST", "Agency", "Corp"]),
                "classification": random.choice(["AFS", "HTM"]),
                "currency": "USD",
                "coupon_rate": f"{coupon:.2f}",
                "book_value": f"{book_value:.2f}",
                "face_value": f"{round(book_value * random.uniform(0.95, 1.05), 2):.2f}",
                "fair_value": f"{fair_value:.2f}",
                "maturity_date": _date_from_today(term_days),
                "duration_years": f"{random.uniform(0.5, 7.0):.2f}",
                "rating": random.choice(["AAA", "AA", "A", "BBB"]),
                "end_of_period_balance": f"{book_value:.2f}",
            }
        )
    return rows


def generate_loan_rows(total_loans: float, count: int = 200):
    rows = []
    amounts = _allocate(total_loans, count, 0.3, 1.4)
    segments = ["mortgage", "auto", "consumer", "SME", "CRE"]
    for idx, principal in enumerate(amounts, start=1):
        spread_bps = random.randint(80, 350)
        base_rate = random.uniform(1.5, 4.5)
        current_rate = base_rate + spread_bps / 100
        term_days = random.randint(365, 3650)
        lgd = random.uniform(0.1, 0.6)
        pd = random.uniform(0.1, 3.0)
        rows.append(
            {
                "asset_id": f"L{idx:04d}",
                "category": "loan",
                "segment": random.choice(segments),
                "currency": "USD",
                "origination_date": _date_from_today(-random.randint(30, 3650)),
                "maturity_date": _date_from_today(term_days),
                "rate_type": random.choice(["fixed", "variable"]),
                "rate_index": random.choice(["SOFR", "Prime", "Treasury"]),
                "spread_bps": spread_bps,
                "current_rate": f"{current_rate:.2f}",
                "principal_outstanding": f"{principal:.2f}",
                "accrued_interest": f"{round(principal * 0.001, 2):.2f}",
                "internal_rating": random.randint(1, 10),
                "pd_annualized": f"{pd:.2f}",
                "lgd": f"{lgd:.2f}",
                "npl_flag": random.choice([0, 0, 0, 1]),
                "end_of_period_balance": f"{principal:.2f}",
            }
        )
    return rows


def write_assets(total: float):
    total_cash = total * ASSET_SPLIT["cash"]
    total_sec = total * ASSET_SPLIT["securities"]
    total_loans = total * ASSET_SPLIT["loans"]

    cash_rows = generate_cash_rows(total_cash)
    sec_rows = generate_security_rows(total_sec)
    loan_rows = generate_loan_rows(total_loans)

    rows = cash_rows + sec_rows + loan_rows
    fieldnames = sorted({key for row in rows for key in row.keys()})

    with OUTPUT_ASSETS.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    totals = sum(float(row["end_of_period_balance"]) for row in rows)
    return round(totals, 2)


def generate_deposit_rows(total_deposits: float, count: int = 400):
    rows = []
    amounts = _allocate(total_deposits, count, 0.6, 1.6)
    products = ["demand", "savings", "time"]
    for idx, balance in enumerate(amounts, start=1):
        rate = random.uniform(0.0, 3.5)
        term_days = random.randint(30, 1095)
        product = random.choice(products)
        is_nmd = 1 if product in ("demand", "savings") else 0
        maturity = _date_from_today(term_days) if product == "time" else ""
        stability_segment = random.choice(["stable", "volatile"]) if is_nmd else ""
        beta_policy = random.uniform(0.05, 0.6) if is_nmd else 0.0
        half_life_days = random.randint(90, 720) if is_nmd else 0
        modeled_life_years = round(random.uniform(1.0, 7.0), 2) if is_nmd else 0.0
        runoff_stress = random.uniform(1.0, 15.0) if is_nmd else 0.0
        rows.append(
            {
                "liability_id": f"D{idx:04d}",
                "category": "deposit",
                "product": product,
                "currency": "USD",
                "open_date": _date_from_today(-random.randint(30, 3650)),
                "maturity_date": maturity,
                "rate": f"{rate:.2f}",
                "balance": f"{balance:.2f}",
                "customer_type": random.choice(["retail", "SME", "corp"]),
                "branch_id": random.randint(1, 50),
                "nmd_flag": is_nmd,
                "stability_segment": stability_segment,
                "beta_to_policy_rate": f"{beta_policy:.2f}",
                "decay_half_life_days": half_life_days,
                "modeled_life_years": f"{modeled_life_years:.2f}",
                "runoff_rate_stress": f"{runoff_stress:.2f}",
                "end_of_period_balance": f"{-balance:.2f}",
            }
        )
    return rows


def generate_wholesale_rows(total_wholesale: float, count: int = 30):
    rows = []
    amounts = _allocate(total_wholesale, count, 0.5, 1.5)
    for idx, notional in enumerate(amounts, start=1):
        rate = random.uniform(2.0, 6.0)
        term_days = random.randint(90, 1825)
        rows.append(
            {
                "liability_id": f"W{idx:03d}",
                "category": "wholesale",
                "type": random.choice(["repo", "term_debt", "subordinated"]),
                "currency": "USD",
                "issue_date": _date_from_today(-random.randint(30, 1825)),
                "maturity_date": _date_from_today(term_days),
                "rate": f"{rate:.2f}",
                "notional": f"{notional:.2f}",
                "collateral_type": random.choice(["UST", "Agency", "None"]),
                "haircut": f"{random.uniform(1.0, 5.0):.2f}",
                "end_of_period_balance": f"{-notional:.2f}",
            }
        )
    return rows


def generate_equity_rows(total_equity: float, count: int = 3):
    rows = []
    amounts = _allocate(total_equity, count, 0.8, 1.2)
    for idx, amount in enumerate(amounts, start=1):
        rows.append(
            {
                "liability_id": f"E{idx:02d}",
                "category": "equity",
                "tier": random.choice(["CET1", "AT1", "T2"]),
                "amount": f"{amount:.2f}",
                "issuance_date": _date_from_today(-random.randint(365, 3650)),
                "maturity_date": "",
                "coupon_rate": f"{random.uniform(0.0, 8.0):.2f}",
                "end_of_period_balance": f"{-amount:.2f}",
            }
        )
    return rows


def write_liabilities(total: float):
    total_dep = total * LIABILITY_SPLIT["deposits"]
    total_wholesale = total * LIABILITY_SPLIT["wholesale"]
    total_equity = total * LIABILITY_SPLIT["equity"]

    deposit_rows = generate_deposit_rows(total_dep)
    wholesale_rows = generate_wholesale_rows(total_wholesale)
    equity_rows = generate_equity_rows(total_equity)

    rows = deposit_rows + wholesale_rows + equity_rows
    fieldnames = sorted({key for row in rows for key in row.keys()})

    with OUTPUT_LIABILITIES.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    liability_signed_total = sum(float(r["end_of_period_balance"]) for r in rows)
    liability_magnitude = sum(abs(float(r["end_of_period_balance"])) for r in rows)
    return round(liability_signed_total, 2), round(liability_magnitude, 2)


def main():
    asset_total = write_assets(TOTAL_BALANCE_SHEET)
    liability_signed_total, liability_mag_total = write_liabilities(TOTAL_BALANCE_SHEET)

    print(f"Assets written to {OUTPUT_ASSETS} total ${asset_total:,.2f} (positive)")
    print(
        f"Liabilities written to {OUTPUT_LIABILITIES} total ${liability_mag_total:,.2f} magnitude (signed {liability_signed_total:,.2f})"
    )
    net = round(asset_total + liability_signed_total, 2)
    print(f"Balance sheet check (assets + liabilities_signed): ${net:,.2f}")


if __name__ == "__main__":
    main()
