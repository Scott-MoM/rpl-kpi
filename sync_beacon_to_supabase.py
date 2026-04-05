import os
import json
import requests
import time
from datetime import datetime

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from supabase import create_client

BEACON_BASE_URL = "https://api.beaconcrm.org/v1/account/{account_id}"


def load_secrets():
    secrets = {}
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path) and tomllib:
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
    return secrets


def get_env_or_secret(secrets, key):
    return os.getenv(key) or secrets.get(key)


def build_beacon_url(endpoint, account_id, base_url=None):
    base = (base_url or BEACON_BASE_URL).strip()
    if "{account_id}" in base:
        if not account_id:
            raise SystemExit("Missing BEACON_ACCOUNT_ID for base URL template.")
        base = base.format(account_id=account_id)
    base = base.rstrip("/")
    if endpoint.startswith("/"):
        return f"{base}{endpoint}"
    if base.endswith("/entities"):
        return f"{base}/{endpoint}"
    return f"{base}/entities/{endpoint}"


def extract_results(payload):
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return payload.get("results") or []
        if isinstance(payload.get("data"), list):
            return payload.get("data") or []
    if isinstance(payload, list):
        return payload
    return []

def extract_total_count(payload):
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta")
    if isinstance(meta, dict):
        total = meta.get("total")
        if isinstance(total, int):
            return total
    total = payload.get("total")
    if isinstance(total, int):
        return total
    return None

def extract_page_progress(payload):
    if not isinstance(payload, dict):
        return None, None
    meta = payload.get("meta")
    if isinstance(meta, dict):
        current_page = meta.get("current_page")
        total_pages = meta.get("total_pages")
        if isinstance(current_page, int) and isinstance(total_pages, int):
            return current_page, total_pages
    current_page = payload.get("current_page")
    total_pages = payload.get("total_pages")
    if isinstance(current_page, int) and isinstance(total_pages, int):
        return current_page, total_pages
    return None, None


def extract_entity(record):
    if not isinstance(record, dict):
        return {}
    if isinstance(record.get("entity"), dict):
        entity = dict(record.get("entity") or {})
        # Keep wrapper-level fields (e.g., relationships) when present.
        for k, v in record.items():
            if k == "entity":
                continue
            if k not in entity:
                entity[k] = v
        return entity
    return record


def fetch_all(endpoint, api_key, account_id, base_url=None, per_page=50, max_pages=200):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Beacon-Application": "developer_api",
    }
    all_rows = []
    page = 1
    while page <= max_pages:
        url = build_beacon_url(endpoint, account_id, base_url=base_url)
        params = {
            "page": page,
            "per_page": per_page,
            "sort_by": "created_at",
            "sort_direction": "desc",
        }
        resp = None
        for attempt in range(4):
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code not in (429, 500, 502, 503, 504):
                break
            if attempt < 3:
                time.sleep(2 ** attempt)
        if resp is None:
            raise SystemExit(f"Beacon request failed for {endpoint}: no response")
        if resp.status_code >= 400:
            try:
                details = resp.json()
            except Exception:
                details = resp.text[:500]
            raise SystemExit(f"Beacon error {resp.status_code} for {endpoint}: {details}")
        data = resp.json()
        rows = extract_results(data)
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < per_page:
            break
        total = extract_total_count(data)
        if isinstance(total, int) and len(all_rows) >= total:
            break
        current_page, total_pages = extract_page_progress(data)
        if isinstance(current_page, int) and isinstance(total_pages, int) and current_page >= total_pages:
            break
        page += 1
    return all_rows


def upsert_rows(table, rows, client):
    if not rows:
        return 0
    total = len(rows)
    index = 0
    default_chunk_size = 200

    while index < total:
        chunk_size = min(default_chunk_size, total - index)
        while True:
            chunk = rows[index:index + chunk_size]
            try:
                client.table(table).upsert(chunk, on_conflict="id").execute()
                index += len(chunk)
                break
            except Exception as e:
                msg = str(e).lower()
                is_timeout = "statement timeout" in msg or "57014" in msg
                if is_timeout and chunk_size > 25:
                    # Reduce batch size and retry the same offset.
                    chunk_size = max(25, chunk_size // 2)
                    time.sleep(1)
                    continue
                if is_timeout:
                    time.sleep(2)
                raise
    return total

def log_system_audit(client, action, details=None, region="Global"):
    try:
        client.table("audit_logs").insert({
            "user_email": "System",
            "action": action,
            "details": details or {},
            "region": region,
        }).execute()
    except Exception as e:
        # Keep sync resilient even if audit logging fails.
        print(f"Audit Log Error: {e}")

def _as_int(value, default):
    try:
        return int(str(value).strip())
    except Exception:
        return default

def is_retryable_error(exc):
    msg = str(exc).lower()
    retry_markers = [
        "statement timeout",
        "57014",
        "timed out",
        "timeout",
        "429",
        "500",
        "502",
        "503",
        "504",
        "connection reset",
        "temporarily unavailable",
    ]
    return any(marker in msg for marker in retry_markers)

def get_last_sync_action(client):
    try:
        resp = (
            client.table("audit_logs")
            .select("action, details, created_at")
            .in_("action", ["Data Sync Completed", "Data Sync Failed"])
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )
        rows = resp.data or []
        for row in rows:
            details = row.get("details") or {}
            if details.get("source") == "beacon_api":
                return row
    except Exception:
        return None
    return None

def send_admin_notification(event_name, details):
    webhook_url = os.getenv("ADMIN_ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return
    try:
        repo = os.getenv("GITHUB_REPOSITORY", "")
        run_id = os.getenv("GITHUB_RUN_ID", "")
        server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        run_url = f"{server}/{repo}/actions/runs/{run_id}" if repo and run_id else ""
        message = (
            f"[{event_name}] Beacon sync ({details.get('trigger', 'unknown')}) "
            f"source={details.get('source', 'beacon_api')} "
            f"run_id={details.get('run_id') or run_id or 'n/a'} "
            f"error={details.get('error', 'none')}"
        )
        if run_url:
            message += f" run_url={run_url}"
        requests.post(webhook_url, json={"text": message}, timeout=15)
    except Exception as e:
        print(f"Notification Error: {e}")

def run_sync_once(client, beacon_key, account_id, beacon_base_url):
    total_started = time.time()
    fetch_started = time.time()
    fetch_breakdown_ms = {}

    endpoint_plan = [
        ("people", "person"),
        ("organisations", "organization"),
        ("events", "event"),
        ("payments", "payment"),
        ("subscriptions", "subscription"),
        ("grants", "grant"),
    ]
    datasets = {}
    for dataset_key, endpoint in endpoint_plan:
        endpoint_started = time.time()
        datasets[dataset_key] = fetch_all(endpoint, beacon_key, account_id, base_url=beacon_base_url)
        fetch_breakdown_ms[dataset_key] = int((time.time() - endpoint_started) * 1000)

    # Optional direct attendee source (preferred for participant drill-down).
    datasets["event_attendees"] = []
    configured_attendee_endpoint = os.getenv("BEACON_EVENT_ATTENDEES_ENDPOINT", "").strip()
    attendee_endpoint_candidates = [
        configured_attendee_endpoint,
        "event_attendee",
        "event_attendees",
        "event_attendance",
        "event_attendances",
        "attendance",
        "attendees",
        "event_registration",
        "event_registrations",
    ]
    attendee_fetch_started = time.time()
    for endpoint in attendee_endpoint_candidates:
        if not endpoint:
            continue
        try:
            datasets["event_attendees"] = fetch_all(endpoint, beacon_key, account_id, base_url=beacon_base_url)
            break
        except Exception:
            continue
    fetch_breakdown_ms["event_attendees"] = int((time.time() - attendee_fetch_started) * 1000)
    fetch_duration_ms = int((time.time() - fetch_started) * 1000)

    transform_started = time.time()
    people_rows = [
        {"id": e.get("id"), "payload": e, "created_at": e.get("created_at")}
        for e in [extract_entity(p) for p in datasets["people"]]
        if e.get("id")
    ]
    def _id_key(value):
        if value is None:
            return ""
        s = str(value).strip().lower()
        if not s:
            return ""
        if "/" in s:
            s = s.rstrip("/").split("/")[-1]
        if ":" in s:
            s = s.split(":")[-1]
        digits = "".join(ch for ch in s if ch.isdigit())
        if len(digits) >= 4:
            return digits
        return "".join(ch for ch in s if ch.isalnum())

    people_name_by_id = {}
    for p in people_rows:
        payload = p.get("payload") or {}
        pid = payload.get("id")
        if pid is None:
            continue
        pname = (
            payload.get("name")
            or payload.get("full_name")
            or payload.get("display_name")
            or payload.get("email")
            or pid
        )
        people_name_by_id[_id_key(pid)] = str(pname).strip()
    org_rows = [
        {"id": e.get("id"), "payload": e, "created_at": e.get("created_at")}
        for e in [extract_entity(o) for o in datasets["organisations"]]
        if e.get("id")
    ]
    attendee_map = {}

    def _norm_key(value):
        if value is None:
            return ""
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

    def _row_value(row, *keys):
        if not isinstance(row, dict):
            return None
        for k in keys:
            if row.get(k) not in [None, ""]:
                return row.get(k)
        wanted = {_norm_key(k) for k in keys}
        for rk, rv in row.items():
            if _norm_key(rk) in wanted and rv not in [None, ""]:
                return rv
        return None

    def _att_event_id(att):
        direct = _row_value(att, "event_id", "eventId", "event")
        if isinstance(direct, dict):
            direct = direct.get("id")
        if direct not in [None, ""]:
            return str(direct)
        rel = att.get("relationships") if isinstance(att, dict) else None
        if isinstance(rel, dict):
            for key in ("event", "events", "activity", "session"):
                ref = rel.get(key)
                if isinstance(ref, dict):
                    data = ref.get("data")
                    if isinstance(data, dict) and data.get("id") not in [None, ""]:
                        return str(data.get("id"))
                    if ref.get("id") not in [None, ""]:
                        return str(ref.get("id"))
        return None

    def _att_person_id(att):
        direct = _row_value(att, "person_id", "contact_id", "participant_id", "person", "contact", "participant")
        if isinstance(direct, dict):
            direct = direct.get("id")
        if direct not in [None, ""]:
            return str(direct)
        rel = att.get("relationships") if isinstance(att, dict) else None
        if isinstance(rel, dict):
            for key in ("person", "people", "contact", "participant"):
                ref = rel.get(key)
                if isinstance(ref, dict):
                    data = ref.get("data")
                    if isinstance(data, dict) and data.get("id") not in [None, ""]:
                        return str(data.get("id"))
                    if ref.get("id") not in [None, ""]:
                        return str(ref.get("id"))
        return None

    def _walk_find_ids(value, context_tokens, id_tokens, out, path=""):
        path_l = str(path).lower()
        in_context = any(t in path_l for t in context_tokens) if path_l else False
        if isinstance(value, dict):
            for k, v in value.items():
                next_path = f"{path}.{k}" if path else str(k)
                key_l = str(k).lower()
                if any(tok in key_l for tok in id_tokens) and (in_context or any(t in key_l for t in context_tokens)):
                    if v not in [None, ""]:
                        out.add(str(v))
                _walk_find_ids(v, context_tokens, id_tokens, out, next_path)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                _walk_find_ids(item, context_tokens, id_tokens, out, f"{path}[{idx}]")

    for row in datasets.get("event_attendees") or []:
        att = extract_entity(row)
        eid = _att_event_id(att)
        if not eid:
            event_ids = set()
            _walk_find_ids(att, context_tokens=("event", "activity", "session"), id_tokens=("id", "event"), out=event_ids)
            if event_ids:
                eid = sorted(event_ids, key=lambda x: len(str(x)))[0]
        if not eid:
            continue
        pid = _att_person_id(att)
        if not pid:
            person_ids = set()
            _walk_find_ids(att, context_tokens=("person", "contact", "participant", "attendee", "people"), id_tokens=("id", "person", "contact", "participant"), out=person_ids)
            if person_ids:
                pid = sorted(person_ids, key=lambda x: len(str(x)))[0]
        name = _row_value(att, "name", "full_name", "display_name", "participant_name", "attendee_name", "person_name", "email")
        if (not name) and pid:
            name = people_name_by_id.get(_id_key(pid))
        bucket = attendee_map.setdefault(eid, {"names": set(), "ids": set()})
        norm_eid = _id_key(eid)
        bucket_norm = attendee_map.setdefault(norm_eid, {"names": set(), "ids": set()}) if norm_eid else bucket
        if pid:
            bucket["ids"].add(str(pid))
            bucket_norm["ids"].add(str(pid))
        if name:
            bucket["names"].add(str(name).strip())
            bucket_norm["names"].add(str(name).strip())

    event_rows = []
    for x in [extract_entity(e) for e in datasets["events"]]:
        if not x.get("id"):
            continue
        eid = str(x.get("id"))
        bucket = attendee_map.get(eid, {"names": set(), "ids": set()})
        if not bucket["names"] and not bucket["ids"]:
            bucket = attendee_map.get(_id_key(eid), {"names": set(), "ids": set()})
        names = sorted([n for n in bucket["names"] if n])
        ids = sorted([i for i in bucket["ids"] if i])
        if names:
            x["participant_list"] = names
        if ids:
            x["participant_ids"] = ids
        if not x.get("number_of_attendees"):
            x["number_of_attendees"] = max(len(names), len(ids))
        event_rows.append(
            {
                "id": x.get("id"),
                "payload": x,
                "start_date": x.get("start_date") or x.get("date") or x.get("created_at"),
                "region": (x.get("c_region") or [x.get("region")] or [None])[0],
            }
        )

    payment_entities = {}
    for p in datasets["payments"]:
        e = extract_entity(p)
        rec_id = e.get("id")
        if rec_id:
            payment_entities[rec_id] = e
    for s in datasets["subscriptions"]:
        e = extract_entity(s)
        rec_id = e.get("id")
        if rec_id and rec_id not in payment_entities:
            payment_entities[rec_id] = e

    payment_rows = [
        {"id": x.get("id"), "payload": x, "payment_date": x.get("payment_date") or x.get("date") or x.get("created_at")}
        for x in payment_entities.values()
        if x.get("id")
    ]
    grant_rows = [
        {"id": x.get("id"), "payload": x, "close_date": x.get("close_date") or x.get("award_date") or x.get("created_at")}
        for x in [extract_entity(g) for g in datasets["grants"]]
        if x.get("id")
    ]
    transform_duration_ms = int((time.time() - transform_started) * 1000)

    upsert_started = time.time()
    count_people = upsert_rows("beacon_people", people_rows, client)
    count_orgs = upsert_rows("beacon_organisations", org_rows, client)
    count_events = upsert_rows("beacon_events", event_rows, client)
    count_payments = upsert_rows("beacon_payments", payment_rows, client)
    count_grants = upsert_rows("beacon_grants", grant_rows, client)
    upsert_duration_ms = int((time.time() - upsert_started) * 1000)
    total_duration_ms = int((time.time() - total_started) * 1000)

    return {
        "people": count_people,
        "organisations": count_orgs,
        "events": count_events,
        "payments": count_payments,
        "grants": count_grants,
        "synced_at": datetime.utcnow().isoformat() + "Z",
        "fetch_duration_ms": fetch_duration_ms,
        "transform_duration_ms": transform_duration_ms,
        "upsert_duration_ms": upsert_duration_ms,
        "total_duration_ms": total_duration_ms,
        "fetch_breakdown_ms": fetch_breakdown_ms,
    }


def main():
    secrets = load_secrets()
    supabase_url = get_env_or_secret(secrets, "SUPABASE_URL") or (secrets.get("supabase") or {}).get("url")
    supabase_key = get_env_or_secret(secrets, "SUPABASE_SERVICE_ROLE_KEY") or (secrets.get("supabase") or {}).get("key")
    beacon_key = get_env_or_secret(secrets, "BEACON_API_KEY")
    account_id = get_env_or_secret(secrets, "BEACON_ACCOUNT_ID")
    beacon_base_url = get_env_or_secret(secrets, "BEACON_BASE_URL")

    if not supabase_url or not supabase_key:
        raise SystemExit("Missing Supabase URL or key. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    if not beacon_key:
        raise SystemExit("Missing Beacon credentials. Set BEACON_API_KEY.")
    if not beacon_base_url and not account_id:
        raise SystemExit("Set BEACON_BASE_URL (preferred) or BEACON_ACCOUNT_ID.")

    client = create_client(supabase_url, supabase_key)

    last_sync = get_last_sync_action(client)

    sync_context = {
        "source": "beacon_api",
        "trigger": "github_actions",
        "workflow": os.getenv("GITHUB_WORKFLOW", "manual_or_unknown"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
    }
    log_system_audit(client, "Data Sync Started", sync_context)

    max_retries = max(0, _as_int(os.getenv("SYNC_MAX_RETRIES"), 1))
    retry_delay_seconds = max(30, _as_int(os.getenv("SYNC_RETRY_DELAY_SECONDS"), 600))
    attempt = 0

    while True:
        attempt += 1
        attempt_context = {**sync_context, "attempt": attempt, "max_attempts": max_retries + 1}
        if attempt > 1:
            log_system_audit(client, "Data Sync Retry Attempt", attempt_context)

        try:
            summary = run_sync_once(client, beacon_key, account_id, beacon_base_url)
            result_details = {**attempt_context, **summary, "attempts_used": attempt}
            log_system_audit(client, "Data Sync Completed", result_details)

            previous_action = (last_sync or {}).get("action")
            if previous_action == "Data Sync Failed":
                send_admin_notification("Data Sync Recovered", result_details)
            elif os.getenv("ADMIN_NOTIFY_ON_SUCCESS", "").strip().lower() in ("1", "true", "yes"):
                send_admin_notification("Data Sync Completed", result_details)

            print(json.dumps(summary, indent=2))
            break
        except Exception as e:
            error_details = {**attempt_context, "error": str(e)}
            retryable = is_retryable_error(e)
            if retryable and attempt <= max_retries:
                log_system_audit(
                    client,
                    "Data Sync Retry Scheduled",
                    {**error_details, "retry_delay_seconds": retry_delay_seconds},
                )
                time.sleep(retry_delay_seconds)
                continue

            log_system_audit(client, "Data Sync Failed", error_details)
            send_admin_notification("Data Sync Failed", error_details)
            raise


if __name__ == "__main__":
    main()
