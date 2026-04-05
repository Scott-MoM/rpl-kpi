import csv
import os
from datetime import datetime

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from supabase import create_client


def load_secrets():
    secrets = {}
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path) and tomllib:
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
    return secrets


def get_env_or_secret(secrets, key):
    return os.getenv(key) or secrets.get(key)


def sniff_delimiter(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
    try:
        return csv.Sniffer().sniff(sample).delimiter
    except Exception:
        return ","


def read_rows(path):
    delim = sniff_delimiter(path)
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        return list(reader)


def to_list(value):
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts if parts else [s]

def clean_ts(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def norm_people(row):
    payload = dict(row)
    payload["id"] = row.get("Record ID")
    payload["created_at"] = clean_ts(row.get("Created date"))
    payload["type"] = to_list(row.get("Type"))
    payload["c_region"] = to_list(row.get("Region"))
    return payload


def norm_org(row):
    payload = dict(row)
    payload["id"] = row.get("Record ID")
    payload["created_at"] = clean_ts(row.get("Created date"))
    payload["type"] = row.get("Type")
    payload["c_region"] = to_list(row.get("Region"))
    return payload


def norm_event(row):
    payload = dict(row)
    payload["id"] = row.get("Record ID")
    payload["start_date"] = clean_ts(row.get("Start date"))
    payload["type"] = row.get("Type")
    payload["c_region"] = to_list(row.get("Location (region)"))
    payload["number_of_attendees"] = row.get("Number of attendees")
    return payload


def norm_payment(row):
    payload = dict(row)
    payload["id"] = row.get("Record ID")
    payload["payment_date"] = clean_ts(row.get("Payment date"))
    payload["amount"] = row.get("Amount (value)")
    return payload


def norm_grant(row):
    payload = dict(row)
    payload["id"] = row.get("Record ID")
    payload["close_date"] = clean_ts(row.get("Award date"))
    payload["amount"] = row.get("Amount granted (value)") or row.get("Amount requested (value)") or row.get("Value (value)")
    payload["stage"] = row.get("Stage")
    return payload


def upsert_rows(table, rows, client):
    if not rows:
        return 0
    client.table(table).upsert(rows).execute()
    return len(rows)


def main():
    secrets = load_secrets()
    supabase_url = get_env_or_secret(secrets, "SUPABASE_URL") or (secrets.get("supabase") or {}).get("url")
    supabase_key = get_env_or_secret(secrets, "SUPABASE_SERVICE_ROLE_KEY") or (secrets.get("supabase") or {}).get("key")
    if not supabase_url or not supabase_key:
        raise SystemExit("Missing Supabase URL or key. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")

    base_dir = os.path.join(os.path.dirname(__file__), "beacon_exports")
    paths = {
        "people": os.path.join(base_dir, "people.csv"),
        "organization": os.path.join(base_dir, "organization.csv"),
        "event": os.path.join(base_dir, "event.csv"),
        "payment": os.path.join(base_dir, "payment.csv"),
        "grant": os.path.join(base_dir, "grant.csv"),
    }

    for name, path in paths.items():
        if not os.path.exists(path):
            raise SystemExit(f"Missing file: {path}")

    people_rows = [norm_people(r) for r in read_rows(paths["people"]) if r.get("Record ID")]
    org_rows = [norm_org(r) for r in read_rows(paths["organization"]) if r.get("Record ID")]
    event_rows = [norm_event(r) for r in read_rows(paths["event"]) if r.get("Record ID")]
    payment_rows = [norm_payment(r) for r in read_rows(paths["payment"]) if r.get("Record ID")]
    grant_rows = [norm_grant(r) for r in read_rows(paths["grant"]) if r.get("Record ID")]

    client = create_client(supabase_url, supabase_key)

    count_people = upsert_rows(
        "beacon_people",
        [{"id": p.get("id"), "payload": p, "created_at": p.get("created_at")} for p in people_rows],
        client,
    )
    count_orgs = upsert_rows(
        "beacon_organisations",
        [{"id": o.get("id"), "payload": o, "created_at": o.get("created_at")} for o in org_rows],
        client,
    )
    count_events = upsert_rows(
        "beacon_events",
        [{"id": e.get("id"), "payload": e, "start_date": e.get("start_date"), "region": (e.get("c_region") or [None])[0]} for e in event_rows],
        client,
    )
    count_payments = upsert_rows(
        "beacon_payments",
        [{"id": p.get("id"), "payload": p, "payment_date": p.get("payment_date")} for p in payment_rows],
        client,
    )
    count_grants = upsert_rows(
        "beacon_grants",
        [{"id": g.get("id"), "payload": g, "close_date": g.get("close_date")} for g in grant_rows],
        client,
    )

    print({
        "people": count_people,
        "organisations": count_orgs,
        "events": count_events,
        "payments": count_payments,
        "grants": count_grants,
        "imported_at": datetime.utcnow().isoformat() + "Z",
    })


if __name__ == "__main__":
    main()
