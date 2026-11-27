"""Read-only daily Claude Code analytics for authorized Console administrators."""
import argparse
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from decimal import Decimal

URL = "https://api.anthropic.com/v1/organizations/usage_report/claude_code"
def fetch_page(day, cursor, key):
    q = {"starting_at": day, "limit": 100}
    if cursor:
        q["page"] = cursor
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(q),
        headers={"x-api-key": key, "anthropic-version": "2026-10-21",
                 "User-Agent": "Koinos/0.2"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def report(day, key, reader=fetch_page):
    day = dt.date.fromisoformat(day).isoformat()
    cursor = None
    seen = set()
    totals = {}
    for _ in range(100):
        page = reader(day, cursor, key)
        if not isinstance(page.get("data"), list):
            raise ValueError("Unexpected analytics schema")
        for row in page["data"]:
            actor = row["actor"]
            kind = actor["type"]
            identity = actor.get("email_address") if kind == "user_actor" else actor.get("api_key_name")
            if not isinstance(identity, str) or not identity:
                continue
            item = totals.setdefault((kind, identity), {"actor_type": kind, "actor": identity,
                "sessions": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": Decimal(0)})
            item["sessions"] += int(row["core_metrics"]["num_sessions"])
            for model in row.get("model_breakdown", []):
                item["input_tokens"] += int(model["tokens"]["input"])
                item["output_tokens"] += int(model["tokens"]["output"])
                cost = model["estimated_cost"]
                if cost["currency"] != "USD":
                    raise ValueError("Unsupported currency")
                item["estimated_cost_usd"] += Decimal(str(cost["amount"])) / 100
        if not page.get("has_more"):
            break
        cursor = page.get("next_page")
        if not cursor or cursor in seen:
            raise ValueError("Invalid pagination cursor")
        seen.add(cursor)
    else:
        raise ValueError("Pagination safety limit exceeded")
    rows = sorted(totals.values(), key=lambda x: (x["sessions"], x["actor"]))
    for row in rows:
        row["estimated_cost_usd"] = str(row["estimated_cost_usd"])
    return {"date_utc": day, "source": "Claude Code Analytics API",
            "remaining_quota": None, "rows": rows}

def main():
    p = argparse.ArgumentParser(description="Historical activity, not remaining subscription quota.")
    p.add_argument("--date", default=(dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=2)).isoformat())
    args = p.parse_args()
    key = os.environ.get("ANTHROPIC_ADMIN_KEY")
    if not key:
        p.error("Set ANTHROPIC_ADMIN_KEY through an approved secrets manager.")
    try:
        print(json.dumps(report(args.date, key), indent=2))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        p.exit(1, "Analytics unavailable; verify organization, key permissions and date.\n")

if __name__ == "__main__":
    main()
