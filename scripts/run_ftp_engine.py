import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AS_OF_DATE = datetime.today().date()
BASE_DIR = Path(__file__).resolve().parents[1]

ASSETS_PATH = BASE_DIR / "data/balance_sheet/assets.csv"
LIABILITIES_PATH = BASE_DIR / "data/balance_sheet/liabilities.csv"
SEGMENTS_PATH = BASE_DIR / "config/segments/segmentation-mapping.csv"
CURVE_PATH = BASE_DIR / f"config/curves/ois-curve-{AS_OF_DATE}.csv"
OUTPUT_PATH = BASE_DIR / "data/results/ftp_results.csv"


@dataclass
class Segment:
    segment_id: str
    product_type: str
    criteria: Dict[str, Any]
    modeled_term_months: str
    ticket_strategy: str
    overnight_share: float
    curve_id: str
    priority: int


def load_curve(path: Path) -> List[Tuple[int, float]]:
    points: List[Tuple[int, float]] = []
    with path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            points.append((int(row["tenor_days"]), float(row["rate_pct"])))
    points.sort(key=lambda x: x[0])
    return points


def interpolate_curve(points: List[Tuple[int, float]], tenor: int) -> float:
    if not points:
        return 0.0
    if tenor <= points[0][0]:
        return points[0][1]
    if tenor >= points[-1][0]:
        return points[-1][1]
    for (t0, r0), (t1, r1) in zip(points, points[1:]):
        if t0 <= tenor <= t1:
            span = t1 - t0
            weight = (tenor - t0) / span if span else 0
            return r0 + weight * (r1 - r0)
    return points[-1][1]


def load_segments(path: Path) -> List[Segment]:
    segments: List[Segment] = []
    with path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            segments.append(
                Segment(
                    segment_id=row["id"],
                    product_type=row["product_type"],
                    criteria=json.loads(row["criteria_json"]),
                    modeled_term_months=row["modeled_term_months"],
                    ticket_strategy=row.get("ticket_strategy", "match_funded"),
                    overnight_share=float(row["overnight_share"]),
                    curve_id=row["curve_id"],
                    priority=int(row["priority"]),
                )
            )
    segments.sort(key=lambda s: s.priority)
    return segments


def parse_float(value: str) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def matches(criteria: Dict[str, Any], row: Dict[str, Any]) -> bool:
    rules = criteria.get("all", [])
    for rule in rules:
        field = rule["field"]
        op = rule["op"]
        val = rule.get("value")
        raw = row.get(field, "")
        if op == "any":
            continue
        if op == "eq":
            if raw != str(val):
                return False
        elif op == "in":
            if raw not in [str(v) for v in val]:
                return False
        elif op == "between":
            num = parse_float(raw)
            if num is None:
                return False
            low, high = val
            if not (float(low) <= num <= float(high)):
                return False
        elif op == "gt":
            num = parse_float(raw)
            if num is None or not num > float(val):
                return False
        elif op == "gte":
            num = parse_float(raw)
            if num is None or not num >= float(val):
                return False
        elif op == "lt":
            num = parse_float(raw)
            if num is None or not num < float(val):
                return False
        elif op == "lte":
            num = parse_float(raw)
            if num is None or not num <= float(val):
                return False
        else:
            return False
    return True


def assign_segment(segments: List[Segment], product_type: str, row: Dict[str, Any]) -> Optional[Segment]:
    for seg in segments:
        if seg.product_type != product_type:
            continue
        if matches(seg.criteria, row):
            return seg
    return None


def load_positions() -> List[Dict[str, Any]]:
    positions: List[Dict[str, Any]] = []
    for path, product_type in [(ASSETS_PATH, "asset"), (LIABILITIES_PATH, "liability")]:
        with path.open() as f:
            r = csv.DictReader(f)
            for row in r:
                if product_type == "liability":
                    cat = row.get("category", "")
                    if cat.lower() == "equity" or row.get("tier"):
                        continue
                    row["product_type"] = cat
                else:
                    row["product_type"] = product_type
                positions.append(row)
    return positions


def tenor_from_dates(as_of: datetime.date, maturity_str: str) -> int:
    if not maturity_str:
        return 1
    try:
        maturity = datetime.strptime(maturity_str, "%Y-%m-%d").date()
        days = (maturity - as_of).days
        return max(days, 1)
    except ValueError:
        return 1


def pick_position_rate(row: Dict[str, Any]) -> float:
    for key in ("current_rate", "rate", "coupon_rate"):
        val = parse_float(row.get(key, ""))
        if val is not None:
            return val
    return 0.0


def build_ladder_tickets(balance: float, segment: Segment) -> List[Tuple[int, float, str, float]]:
    """Return list of (tenor_days, weight, bucket_type, ticket_balance_share) for laddered (NMD) segments."""
    tickets: List[Tuple[int, float, str, float]] = []
    overnight = segment.overnight_share
    stable_share = max(0.0, 1.0 - overnight)
    if overnight > 0:
        tickets.append((1, overnight, "overnight", balance * overnight))
    modeled = segment.modeled_term_months
    try:
        months = int(float(modeled))
    except ValueError:
        months = 0
    if stable_share > 0 and months > 0:
        per = stable_share / months
        for i in range(1, months + 1):
            tenor = 30 * i
            tickets.append((tenor, per, "ladder", balance * per))
    elif stable_share > 0:
        tickets.append((30, stable_share, "ladder", balance * stable_share))
    return tickets


def run():
    curve_points = load_curve(CURVE_PATH)
    segments = load_segments(SEGMENTS_PATH)
    positions = load_positions()

    results: List[Dict[str, Any]] = []
    ladder_aggs: Dict[str, Dict[str, Any]] = {}

    for row in positions:
        product_type = row.get("product_type", "")
        side = "asset" if product_type == "asset" else "liability"
        segment = assign_segment(segments, product_type, row)
        segment_id = segment.segment_id if segment else "unassigned"
        strategy = (segment.ticket_strategy if segment else "match_funded").lower()
        balance = parse_float(row.get("end_of_period_balance") or "0") or 0.0
        if balance == 0:
            continue
        rate_pos = pick_position_rate(row)
        tenor_days = tenor_from_dates(AS_OF_DATE, row.get("maturity_date", ""))
        instrument_id = row.get("asset_id") or row.get("liability_id") or ""

        if strategy == "ladder":
            agg = ladder_aggs.setdefault(
                segment_id,
                {
                    "segment": segment,
                    "side": side,
                    "category": row.get("category"),
                    "product_type": product_type,
                    "balance": 0.0,
                    "weighted_rate": 0.0,
                },
            )
            agg["balance"] += balance
            agg["weighted_rate"] += rate_pos * balance
            continue

        # Match-funded: one ticket per instrument_id
        ftp_rate = interpolate_curve(curve_points, tenor_days)
        spread = ftp_rate - rate_pos
        day_fraction = tenor_days / 360
        ftp_charge = balance * (spread / 100.0) * day_fraction
        results.append(
            {
                "as_of_date": AS_OF_DATE.isoformat(),
                "instrument_id": instrument_id,
                "side": side,
                "category": row.get("category"),
                "product_type": product_type,
                "segment_id": segment_id,
                "bucket_type": "match_funded",
                "tenor_days": tenor_days,
                "weight": 1.0,
                "ticket_balance": round(balance, 2),
                "ftp_rate_pct": round(ftp_rate, 4),
                "position_rate_pct": round(rate_pos, 4),
                "ftp_spread_pct": round(spread, 4),
                "ftp_charge": round(ftp_charge, 2),
            }
        )

    # Process laddered (NMD) segments aggregated by segment
    for segment_id, agg in ladder_aggs.items():
        segment = agg["segment"] or Segment(segment_id, agg["product_type"], {"all": []}, "0", "ladder", 0.0, "ftp_ois_curve", 9999)
        total_balance = agg["balance"]
        if total_balance == 0:
            continue
        avg_rate = agg["weighted_rate"] / total_balance
        tickets = build_ladder_tickets(total_balance, segment)
        for tenor_days, weight, bucket_type, ticket_balance in tickets:
            ftp_rate = interpolate_curve(curve_points, tenor_days)
            spread = ftp_rate - avg_rate
            day_fraction = tenor_days / 360
            ftp_charge = ticket_balance * (spread / 100.0) * day_fraction
            results.append(
                {
                    "as_of_date": AS_OF_DATE.isoformat(),
                    "instrument_id": "",
                    "side": agg["side"],
                    "category": agg["category"],
                    "product_type": agg["product_type"],
                    "segment_id": segment_id,
                    "bucket_type": bucket_type,
                    "tenor_days": tenor_days,
                    "weight": round(weight, 6),
                    "ticket_balance": round(ticket_balance, 2),
                    "ftp_rate_pct": round(ftp_rate, 4),
                    "position_rate_pct": round(avg_rate, 4),
                    "ftp_spread_pct": round(spread, 4),
                    "ftp_charge": round(ftp_charge, 2),
                }
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        fieldnames = [
            "as_of_date",
            "instrument_id",
            "side",
            "category",
            "product_type",
            "segment_id",
            "bucket_type",
            "tenor_days",
            "weight",
            "ticket_balance",
            "ftp_rate_pct",
            "position_rate_pct",
            "ftp_spread_pct",
            "ftp_charge",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    total_charge = sum(r["ftp_charge"] for r in results)
    print(f"Tickets generated: {len(results)} rows")
    print(f"Total FTP charge/credit (signed): {total_charge:,.2f}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    run()
