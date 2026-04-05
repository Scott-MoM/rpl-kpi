import streamlit as st
import pandas as pd
import json
import os
import re
import math
import requests
import time
import threading
import uuid
import plotly.express as px
import plotly.io as pio
from passlib.hash import pbkdf2_sha256
from datetime import datetime, UTC
from concurrent.futures import ThreadPoolExecutor

# --- SUPABASE SETUP ---
from supabase import create_client, Client

# --- CONFIGURATION ---
USER_DB_FILE = 'usersAuth.json'
CASE_STUDIES_FILE = 'case_studies.json'

st.set_page_config(page_title="Regional KPI Dashboard", layout="wide")

# --- UI THEME / STYLES ---
def inject_global_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

        :root {
            --bg-1: #0a0a12;
            --bg-2: #1a0f2e;
            --bg-3: #0e2a3b;
            --card: rgba(255, 255, 255, 0.08);
            --card-strong: rgba(255, 255, 255, 0.14);
            --text: #f7f8fb;
            --muted: #c7d0e2;
            --accent-1: #00f5d4;
            --accent-2: #ff9f1c;
            --accent-3: #5a4dff;
            --accent-4: #ff3d7f;
            --accent-5: #7bff6b;
            --accent-6: #ffd166;
        }

        html, body, [class*="css"]  {
            font-family: "Space Grotesk", system-ui, -apple-system, Segoe UI, Roboto, sans-serif !important;
            color: var(--text);
        }

        .stApp {
            background:
                radial-gradient(900px 700px at 5% 0%, #ff3d7f 0%, transparent 55%),
                radial-gradient(900px 700px at 95% 0%, #5a4dff 0%, transparent 55%),
                radial-gradient(800px 600px at 50% 10%, #00f5d4 0%, transparent 55%),
                radial-gradient(900px 700px at 50% 110%, #ff9f1c 0%, transparent 55%),
                linear-gradient(145deg, var(--bg-1), var(--bg-2), var(--bg-3));
            color: var(--text);
            animation: bgShift 18s ease-in-out infinite alternate;
        }

        @keyframes bgShift {
            0% { filter: hue-rotate(0deg); }
            100% { filter: hue-rotate(12deg); }
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a0f2e, #0e2a3b);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        
        header[data-testid="stHeader"] {
            background: linear-gradient(90deg, rgba(11,15,26,0.95), rgba(15,27,45,0.95));
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }

        div[data-testid="stToolbar"] {
            background: transparent;
        }

        label, .stMarkdown, .stTextInput label, .stTextArea label, .stSelectbox label, .stDateInput label {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span {
            color: #ffffff !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: rgba(255,255,255,0.06);
            padding: 6px;
            border-radius: 14px;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 10px;
            color: var(--muted);
            font-weight: 600;
            padding: 10px 14px;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, #00f5d4, #7bff6b, #ff9f1c, #ff3d7f, #5a4dff);
            color: #001018 !important;
            box-shadow: 0 8px 24px rgba(90, 77, 255, 0.45);
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(255,61,127,0.25), rgba(90,77,255,0.18), rgba(0,245,212,0.18), rgba(255,159,28,0.18));
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            padding: 16px 18px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.35);
            box-shadow: 0 12px 30px rgba(0,0,0,0.35);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border 0.2s ease;
        }

        div[data-testid="stMetric"] * {
            color: var(--text) !important;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px) scale(1.01);
            border: 1px solid rgba(255,255,255,0.4);
            box-shadow: 0 18px 45px rgba(0,0,0,0.4);
        }

        /* Popover triggers styled like KPI metric cards */
        div[data-testid="stPopover"] > div > button,
        div[data-testid="stPopoverButton"] > button {
            width: 100%;
            min-height: 90px;
            text-align: left;
            white-space: pre-line;
            background: linear-gradient(135deg, rgba(255,61,127,0.25), rgba(90,77,255,0.18), rgba(0,245,212,0.18), rgba(255,159,28,0.18));
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            padding: 16px 18px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.35);
            box-shadow: 0 12px 30px rgba(0,0,0,0.35);
            color: var(--text) !important;
            font-weight: 600;
            line-height: 1.35;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border 0.2s ease;
        }

        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopoverButton"] > button:hover {
            transform: translateY(-5px) scale(1.01);
            border: 1px solid rgba(255,255,255,0.4);
            box-shadow: 0 18px 45px rgba(0,0,0,0.4);
        }

        /* Drill-down controls: enforce readable contrast */
        div[data-testid="stPopover"] [data-baseweb="select"] > div {
            background: rgba(12, 18, 32, 0.92) !important;
            color: #f7f8fb !important;
            border: 1px solid rgba(255,255,255,0.28) !important;
        }

        div[data-testid="stPopover"] [data-baseweb="select"] input,
        div[data-testid="stPopover"] [data-baseweb="select"] span,
        div[data-testid="stPopover"] [data-baseweb="select"] div {
            color: #f7f8fb !important;
        }

        div[role="listbox"] {
            background: #0f1a2b !important;
            color: #f7f8fb !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
        }

        div[role="option"] {
            background: transparent !important;
            color: #f7f8fb !important;
        }

        div[role="option"][aria-selected="true"] {
            background: rgba(90, 77, 255, 0.35) !important;
            color: #ffffff !important;
        }

        .stPlotlyChart, .stDataFrame {
            background: linear-gradient(135deg, rgba(90,77,255,0.22), rgba(255,61,127,0.18), rgba(0,245,212,0.18));
            border-radius: 14px;
            padding: 8px;
            border: 1px solid rgba(255,255,255,0.28);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.4);
        }

        .stButton>button, .stDownloadButton>button, div[data-testid="stFormSubmitButton"]>button {
            background: linear-gradient(90deg, #00f5d4, #7bff6b, #ff9f1c, #ff3d7f, #5a4dff);
            border: 1px solid rgba(255,255,255,0.12);
            color: #0c0c12;
            font-weight: 700;
            border-radius: 999px;
            padding: 8px 16px;
            box-shadow: 0 12px 26px rgba(90, 77, 255, 0.45);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .stButton>button:hover, .stDownloadButton>button:hover, div[data-testid="stFormSubmitButton"]>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 32px rgba(255, 61, 127, 0.55);
        }

        section[data-testid="stSidebar"] label[data-testid="stMarkdownContainer"] + div [role="radiogroup"] label {
            background: linear-gradient(90deg, #ff3d7f, #ff9f1c, #7bff6b, #00f5d4, #5a4dff);
            border-radius: 999px;
            padding: 6px 10px;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.18);
            margin-bottom: 6px;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
            margin-right: 6px;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label[data-selected="true"] {
            box-shadow: 0 8px 22px rgba(122, 60, 255, 0.4);
        }

        /* Ensure radio/checkbox option text is always white */
        [role="radiogroup"] label,
        [role="radiogroup"] label span,
        [data-testid="stCheckbox"] label,
        [data-testid="stCheckbox"] label span {
            color: #ffffff !important;
        }

        /* Force BaseWeb internals (used by Streamlit radio/checkbox) */
        [data-baseweb="radio"] *,
        [data-baseweb="checkbox"] *,
        [data-testid="stRadio"] *,
        [data-testid="stCheckbox"] *,
        [data-testid="stSidebar"] [data-baseweb="radio"] *,
        [data-testid="stSidebar"] [data-baseweb="checkbox"] * {
            color: #ffffff !important;
            fill: #ffffff !important;
        }

        h1, h2, h3, h4 {
            letter-spacing: 0.2px;
        }

        .section-card {
            background: linear-gradient(90deg, rgba(255,61,127,0.3), rgba(255,159,28,0.2), rgba(0,245,212,0.2), rgba(90,77,255,0.2));
            border: 1px solid rgba(255,255,255,0.2);
            padding: 14px 16px;
            border-radius: 16px;
            margin: 4px 0 10px 0;
        }

        .glass-card {
            background: linear-gradient(135deg, rgba(255,61,127,0.22), rgba(90,77,255,0.18), rgba(0,245,212,0.18));
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 18px;
            padding: 14px 16px;
            margin: 10px 0 16px 0;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 10px 26px rgba(0,0,0,0.25);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border 0.2s ease;
        }

        .glass-card:hover {
            transform: translateY(-4px);
            border: 1px solid rgba(255,255,255,0.35);
            box-shadow: 0 18px 40px rgba(0,0,0,0.35);
        }

        .badge {
            display: inline-block;
            background: linear-gradient(90deg, #00f5d4, #7bff6b, #ff9f1c, #ff3d7f, #5a4dff);
            border: 1px solid rgba(255,255,255,0.25);
            color: #0c0c12;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }

        h2::after, h3::after {
            content: "";
            display: block;
            width: 120px;
            height: 4px;
            margin-top: 6px;
            border-radius: 999px;
            background: linear-gradient(90deg, #00f5d4, #7bff6b, #ff9f1c, #ff3d7f, #5a4dff);
        }

        .refresh-card {
            padding: 10px 12px;
            border-radius: 14px;
            margin-top: 10px;
            font-weight: 600;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .refresh-green {
            background: rgba(0, 245, 212, 0.18);
            color: #7bff6b;
            border-color: rgba(123, 255, 107, 0.5);
        }
        .refresh-amber {
            background: rgba(255, 159, 28, 0.2);
            color: #ffd166;
            border-color: rgba(255, 209, 102, 0.5);
        }
        .refresh-red {
            background: rgba(255, 61, 127, 0.2);
            color: #ff9fb5;
            border-color: rgba(255, 61, 127, 0.5);
        }
        .sync-toast {
            padding: 10px 12px;
            border-radius: 14px;
            margin: 8px 0 10px 0;
            font-weight: 600;
            border: 1px solid rgba(255,255,255,0.2);
            line-height: 1.35;
        }
        .sync-toast-running {
            background: rgba(0, 245, 212, 0.14);
            color: #c8fff4;
            border-color: rgba(0, 245, 212, 0.45);
        }
        .sync-toast-complete {
            background: rgba(123, 255, 107, 0.15);
            color: #d8ffd0;
            border-color: rgba(123, 255, 107, 0.5);
        }
        .sync-toast-failed {
            background: rgba(255, 61, 127, 0.2);
            color: #ffd2df;
            border-color: rgba(255, 61, 127, 0.5);
        }

        .neon-callout {
            padding: 10px 14px;
            border-radius: 14px;
            background: linear-gradient(90deg, #00f5d4, #7bff6b, #ff9f1c, #ff3d7f, #5a4dff);
            color: #0c0c12;
            font-weight: 700;
            box-shadow: 0 12px 30px rgba(90, 77, 255, 0.45);
            text-align: center;
        }

        .overlay-message {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
            padding: 12px 18px;
            border-radius: 999px;
            background: linear-gradient(90deg, #00f5d4, #7bff6b, #ff9f1c, #ff3d7f, #5a4dff);
            color: #0c0c12;
            font-weight: 700;
            font-size: 16px;
            box-shadow: 0 12px 30px rgba(90, 77, 255, 0.45);
            animation: overlay-fade 0.6s ease forwards;
            animation-delay: 7.5s;
        }
        @keyframes overlay-fade {
            0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(0.98); }
        }

        .confetti-container {
            position: relative;
            height: 80px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .confetti-piece {
            position: absolute;
            width: 10px;
            height: 14px;
            opacity: 0.9;
            animation: confetti-fall 1.6s ease-out forwards;
        }
        @keyframes confetti-fall {
            0% { transform: translateY(-20px) rotate(0deg); }
            100% { transform: translateY(120px) rotate(360deg); opacity: 0; }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- DATABASE CONNECTION (HYBRID) ---

def get_db_connection():
    """
    Attempts to connect to Supabase.
    Returns ('supabase', client) if secrets exist.
    Returns ('local', None) otherwise.
    """
    if "supabase" in st.secrets:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            if key and key.startswith("eyJ"):
                try:
                    payload = key.split(".")[1]
                    padding = "=" * (-len(payload) % 4)
                    payload_bytes = payload + padding
                    import base64
                    decoded = json.loads(base64.b64decode(payload_bytes).decode("utf-8"))
                    st.session_state["supabase_role"] = decoded.get("role")
                except Exception:
                    st.session_state["supabase_role"] = "unknown"
            supabase: Client = create_client(url, key)
            return 'supabase', supabase
        except Exception as e:
            st.error(f"Supabase Configuration Error: {e}")
            return 'local', None
    return 'local', None

DB_TYPE, DB_CLIENT = get_db_connection()
SYNC_EXECUTOR = ThreadPoolExecutor(max_workers=1)
SYNC_JOBS = {}
SYNC_JOBS_LOCK = threading.Lock()
APP_ROLE_NAMES = ["Admin", "Manager", "RPL", "ML", "Funder"]

class SyncCancelledError(Exception):
    pass

def get_admin_client():
    if "supabase" not in st.secrets:
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

def ensure_supabase_roles():
    if DB_TYPE != "supabase":
        return
    try:
        existing_rows = DB_CLIENT.table("roles").select("name").execute().data or []
        existing = {str(row.get("name") or "").strip() for row in existing_rows}
        missing = [name for name in APP_ROLE_NAMES if name not in existing]
        for role_name in missing:
            DB_CLIENT.table("roles").insert({"name": role_name}).execute()
    except Exception as e:
        print(f"Role seed error: {e}")

def _get_openrouteservice_api_key():
    if "openrouteservice" in st.secrets:
        return str(st.secrets["openrouteservice"].get("api_key") or "").strip()
    if "routing" in st.secrets:
        provider = str(st.secrets["routing"].get("provider") or "").strip().lower()
        if provider in {"openrouteservice", "ors"}:
            return str(st.secrets["routing"].get("api_key") or "").strip()
    return ""

# --- AUDIT LOGGING HELPER ---
def log_audit_event(action, details=None):
    """Utility to record administrative actions to the audit log."""
    if DB_TYPE == 'supabase':
        try:
            DB_CLIENT.table("audit_logs").insert({
                "user_email": st.session_state.get("email", "System"),
                "action": action,
                "details": details or {},
                "region": st.session_state.get("region", "Global")
            }).execute()
        except Exception as e:
            # We print instead of st.error to avoid UI clutter on background ops
            print(f"Audit Log Error: {e}")

def log_audit_state_change(state_key, action, details=None):
    """Logs an event only when the tracked state payload changes."""
    payload = details or {}
    marker = json.dumps(payload, sort_keys=True, default=str)
    ss_key = f"_audit_state_{state_key}"
    if st.session_state.get(ss_key) == marker:
        return
    st.session_state[ss_key] = marker
    log_audit_event(action, payload)

def _sanitize_audit_value(value, max_len=500):
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = value
    elif isinstance(value, (list, tuple, set)):
        text = [_sanitize_audit_value(v, max_len=120) for v in list(value)[:50]]
    elif isinstance(value, dict):
        text = {
            str(k): _sanitize_audit_value(v, max_len=120)
            for idx, (k, v) in enumerate(value.items())
            if idx < 50
        }
    else:
        text = str(value)
    if isinstance(text, str) and len(text) > max_len:
        return text[:max_len] + "..."
    return text

def _should_audit_session_key(key):
    key_l = str(key or "").strip().lower()
    if not key_l:
        return False
    if key_l.startswith("_"):
        return False
    if key_l.startswith("formsubmitter:"):
        return False
    if key_l in {
        "logged_in",
        "name",
        "email",
        "role",
        "roles",
        "region",
        "supabase_role",
        "force_password_change",
    }:
        return False
    sensitive_tokens = ("password", "token", "secret", "api_key", "service_role_key")
    if any(token in key_l for token in sensitive_tokens):
        return False
    internal_tokens = (
        "manual_sync",
        "sync_jobs",
        "reports_applied_filters",
        "reports_applied_advanced_filters",
        "audit_state",
    )
    if any(token in key_l for token in internal_tokens):
        return False
    return True

def _capture_audit_session_snapshot():
    snapshot = {}
    for key, value in st.session_state.items():
        if not _should_audit_session_key(key):
            continue
        snapshot[str(key)] = _sanitize_audit_value(value)
    return snapshot

def audit_user_interactions(current_view=None):
    if DB_TYPE != 'supabase':
        return
    if not st.session_state.get("logged_in"):
        return
    previous = st.session_state.get("_audit_widget_snapshot")
    current = _capture_audit_session_snapshot()
    if previous is None:
        st.session_state["_audit_widget_snapshot"] = current
        return

    changes = []
    all_keys = sorted(set(previous.keys()) | set(current.keys()))
    for key in all_keys:
        old = previous.get(key)
        new = current.get(key)
        if old == new:
            continue
        change_type = "changed"
        if key not in previous:
            change_type = "added"
        elif key not in current:
            change_type = "removed"
        changes.append({
            "key": key,
            "change_type": change_type,
            "previous_value": old,
            "current_value": new,
        })

    st.session_state["_audit_widget_snapshot"] = current
    if not changes:
        return

    log_audit_event(
        "UI Interaction",
        {
            "view": current_view or "",
            "change_count": len(changes),
            "changes": changes[:100],
        },
    )

# --- DATA HELPERS ---
def _clean_ts(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None

def _to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    s = str(value).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts if parts else [s]

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj

def _coerce_money(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("value", "amount", "total", "gross", "net"):
            if key in value:
                coerced = _coerce_money(value.get(key))
                if coerced != 0.0:
                    return coerced
        for nested in value.values():
            coerced = _coerce_money(nested)
            if coerced != 0.0:
                return coerced
        return 0.0
    if isinstance(value, (list, tuple, set)):
        for item in value:
            coerced = _coerce_money(item)
            if coerced != 0.0:
                return coerced
        return 0.0
    s = str(value).replace("£", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0

def _coerce_int(value):
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(float(value))
    try:
        s = str(value).strip().replace(",", "")
        if not s:
            return 0
        return int(float(s))
    except Exception:
        return 0

def _format_dataframe_cell(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, (list, tuple, set)):
        try:
            return json.dumps(list(value), ensure_ascii=True)
        except Exception:
            return str(list(value))
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=True, sort_keys=True)
        except Exception:
            return str(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return str(value)
    return str(value)

def _make_arrow_compatible_df(df):
    if df is None:
        return df
    safe_df = df.copy()
    for col in safe_df.columns:
        if not pd.api.types.is_object_dtype(safe_df[col]):
            continue
        safe_df[col] = safe_df[col].map(_format_dataframe_cell)
    return safe_df

def _safe_dataframe(df, **kwargs):
    st.dataframe(_make_arrow_compatible_df(df), **kwargs)

def _pretty_field_name(name):
    return str(name).replace("_", " ").strip().title()

def render_plot_with_export(fig, export_name, key_prefix):
    plot_config = {
        "displayModeBar": True,
        "toImageButtonOptions": {
            "format": "png",
            "filename": export_name,
            "scale": 2,
        },
        "displaylogo": False,
    }
    st.plotly_chart(fig, width="stretch", config=plot_config)
    try:
        img_bytes = pio.to_image(fig, format="png", width=1400, height=900, scale=2)
        st.download_button(
            "Download chart as PNG",
            data=img_bytes,
            file_name=f"{export_name}.png",
            mime="image/png",
            key=f"{key_prefix}_png_download",
        )
    except Exception:
        st.caption("Use the camera icon on the chart to download PNG.")

def _norm_key(value):
    if value is None:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())

def _entity_ref_key(value):
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

POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE)

def _get_row_value(row, *keys):
    if not row or not keys:
        return None
    try:
        if any(k in row for k in keys):
            for k in keys:
                if k in row and row.get(k) not in [None, ""]:
                    return row.get(k)
    except Exception:
        pass

    normalized = {}
    for k, v in row.items():
        nk = _norm_key(k)
        if nk and nk not in normalized:
            normalized[nk] = v

    for k in keys:
        nk = _norm_key(k)
        if nk in normalized and normalized[nk] not in [None, ""]:
            return normalized[nk]
    return None

def _extract_participant_refs(event_row, people_name_by_id=None):
    people_name_by_id = people_name_by_id or {}
    participant_keys = (
        "participant_list",
        "participants_list",
        "participants",
        "attendees",
        "attendee_list",
        "attendees_list",
        "people",
        "participant_names",
        "attendee_names",
        "contacts",
        "relationships",
    )
    found_names = []
    found_ids = []
    seen_names = set()
    seen_ids = set()
    context_tokens = ("participant", "attendee", "people", "contact", "person", "member")
    id_keys = ("id", "person_id", "contact_id", "participant_id", "attendee_id")

    def _add_name(value):
        candidate = str(value).strip()
        if not candidate:
            return
        key = candidate.lower()
        if key in seen_names:
            return
        seen_names.add(key)
        found_names.append(candidate)

    def _add_id(value):
        candidate = str(value).strip()
        if not candidate or candidate in seen_ids:
            return
        seen_ids.add(candidate)
        found_ids.append(candidate)

    def _looks_like_context(path):
        path_l = str(path).lower()
        return any(t in path_l for t in context_tokens)

    def _walk(value, path=""):
        if value is None:
            return
        if isinstance(value, dict):
            local_name = value.get("name") or value.get("full_name") or value.get("display_name")
            if local_name:
                _add_name(local_name)
            if value.get("email"):
                _add_name(value.get("email"))
            for id_key in id_keys:
                if value.get(id_key) is not None and _looks_like_context(path):
                    _add_id(value.get(id_key))
            for k, v in value.items():
                next_path = f"{path}.{k}" if path else str(k)
                _walk(v, next_path)
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                next_path = f"{path}[{idx}]"
                _walk(item, next_path)
            return
        if isinstance(value, str) and _looks_like_context(path):
            raw = [x.strip() for x in value.replace("\n", ",").replace(";", ",").split(",")]
            for token in raw:
                if token:
                    _add_name(token)

    for key in participant_keys:
        val = event_row.get(key)
        if val is not None:
            _walk(val, key)

    for pid in found_ids:
        mapped_name = people_name_by_id.get(_entity_ref_key(pid))
        if mapped_name:
            _add_name(mapped_name)
    return found_names, found_ids

def _extract_linked_event_ids_from_person(person_row):
    linked_ids = set()
    context_tokens = ("event", "attend", "session", "activity", "retreat", "walk", "booking")
    id_keys = ("id", "event_id", "activity_id", "session_id")

    def _in_context(path):
        p = str(path).lower()
        return any(t in p for t in context_tokens)

    def _walk(value, path=""):
        if value is None:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                next_path = f"{path}.{k}" if path else str(k)
                if k in id_keys and _in_context(path) and v is not None and str(v).strip():
                    linked_ids.add(str(v).strip())
                _walk(v, next_path)
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                _walk(item, f"{path}[{idx}]")
            return
        if isinstance(value, str) and _in_context(path):
            for token in re.split(r"[,;\n]", value):
                token = token.strip()
                if token:
                    linked_ids.add(token)

    _walk(person_row)
    return linked_ids

def _walk_nested_values(value):
    if value is None:
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk_nested_values(v)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _walk_nested_values(item)
        return
    yield value

def _extract_postcode_from_value(value):
    for item in _walk_nested_values(value):
        if isinstance(item, bytes):
            try:
                item = item.decode("utf-8")
            except Exception:
                item = str(item)
        text = str(item).strip()
        if not text:
            continue
        match = POSTCODE_RE.search(text.upper())
        if match:
            postcode = re.sub(r"\s+", "", match.group(1).upper())
            return f"{postcode[:-3]} {postcode[-3:]}" if len(postcode) > 3 else postcode
    return None

def _normalize_person_lookup(value):
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())

def _normalize_gender(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return "Unknown / Not provided"
    if raw in {"prefer not to say", "prefer not say", "prefer not", "pn ts", "n/a", "na"}:
        return "Prefer not to say"
    if any(token in raw for token in ["trans", "non-binary", "non binary", "nonbinary", "gender diverse", "genderqueer", "agender"]):
        return "Trans / Non-binary / Gender diverse"
    if raw in {"m", "male", "man", "men"}:
        return "Men"
    if raw in {"f", "female", "woman", "women"}:
        return "Women"
    if raw in {"unknown", "not provided", "unspecified"}:
        return "Unknown / Not provided"
    return "Trans / Non-binary / Gender diverse"

def _extract_linked_id(value):
    if isinstance(value, list):
        for item in value:
            extracted = _extract_linked_id(item)
            if extracted not in [None, ""]:
                return extracted
        return None
    if isinstance(value, dict):
        for key in ("id", "record_id", "value"):
            if value.get(key) not in [None, ""]:
                return value.get(key)
        return None
    return value

def _extract_coords_from_record(record):
    if not isinstance(record, dict):
        return None, None

    def _to_float_or_none(value):
        try:
            return float(value)
        except Exception:
            return None

    def _walk(value):
        if isinstance(value, dict):
            lat = None
            lon = None
            for lat_key in ("lat", "latitude", "y"):
                if lat_key in value:
                    lat = _to_float_or_none(value.get(lat_key))
                    if lat is not None:
                        break
            for lon_key in ("lon", "lng", "long", "longitude", "x"):
                if lon_key in value:
                    lon = _to_float_or_none(value.get(lon_key))
                    if lon is not None:
                        break
            if lat is not None and lon is not None:
                return lat, lon
            for nested in value.values():
                found = _walk(nested)
                if found != (None, None):
                    return found
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                found = _walk(item)
                if found != (None, None):
                    return found
        return (None, None)

    return _walk(record)

def _extract_location_label(record):
    if not isinstance(record, dict):
        return ""
    return str(
        _get_row_value(
            record,
            "location",
            "venue",
            "site",
            "address",
            "name",
            "title",
            "Display Name",
        ) or ""
    ).strip()

@st.cache_data(show_spinner=False, ttl=86400)
def _lookup_postcode_coordinates(postcode):
    normalized = _extract_postcode_from_value(postcode)
    if not normalized:
        return None
    try:
        encoded = normalized.replace(" ", "%20")
        resp = requests.get(f"https://api.postcodes.io/postcodes/{encoded}", timeout=10)
        resp.raise_for_status()
        payload = resp.json() or {}
        result = payload.get("result") or {}
        lat = result.get("latitude")
        lon = result.get("longitude")
        if lat is None or lon is None:
            return None
        return {"postcode": normalized, "lat": float(lat), "lon": float(lon)}
    except Exception:
        return None

def _resolve_record_location(record):
    lat, lon = _extract_coords_from_record(record)
    postcode = _extract_postcode_from_value(record)
    if lat is not None and lon is not None:
        return {"postcode": postcode or "", "lat": lat, "lon": lon}
    if postcode:
        looked_up = _lookup_postcode_coordinates(postcode)
        if looked_up:
            return looked_up
    return {"postcode": postcode or "", "lat": None, "lon": None}

def _haversine_miles(lat1, lon1, lat2, lon2):
    radius_miles = 3958.7613
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_miles * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@st.cache_data(show_spinner=False, ttl=2592000)
def _lookup_road_distance_miles(lat1, lon1, lat2, lon2, api_key):
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.openrouteservice.org/v2/directions/driving-car",
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
            json={
                "coordinates": [
                    [float(lon1), float(lat1)],
                    [float(lon2), float(lat2)],
                ]
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json() or {}
        routes = payload.get("routes") or []
        if not routes:
            return None
        summary = routes[0].get("summary") or {}
        distance_meters = summary.get("distance")
        if distance_meters in (None, ""):
            return None
        return float(distance_meters) / 1609.344
    except Exception:
        return None

@st.cache_data(show_spinner=False, ttl=900)
def fetch_distance_analysis_data(region="Global", start_date=None, end_date=None):
    batch_size = 1000
    road_api_key = _get_openrouteservice_api_key()

    def _fetch_rows(table, select_cols, date_col=None):
        offset = 0
        rows = []
        while True:
            q = DB_CLIENT.table(table).select(select_cols).range(offset, offset + batch_size - 1)
            if date_col and start_date:
                q = q.gte(date_col, start_date.isoformat())
            if date_col and end_date:
                q = q.lte(date_col, end_date.isoformat())
            chunk = q.execute().data or []
            rows.extend(chunk)
            if len(chunk) < batch_size:
                break
            offset += batch_size
        return rows

    people_rows = _fetch_rows("beacon_people", "payload")
    event_rows = _fetch_rows("beacon_events", "payload, start_date, region", "start_date")

    people_by_id = {}
    people_by_name = {}
    linked_people_by_event = {}
    for row in people_rows:
        payload = row.get("payload") or {}
        person_id = payload.get("id")
        person_name = str(_get_row_value(payload, "name", "full_name", "Display Name", "email") or person_id or "").strip()
        person_email = str(_get_row_value(payload, "email", "Email") or "").strip()
        person_loc = _resolve_record_location(payload)
        person_entry = {
            "person_id": str(person_id or ""),
            "participant": person_name or str(person_id or "Participant"),
            "participant_postcode": person_loc.get("postcode") or "",
            "participant_lat": person_loc.get("lat"),
            "participant_lon": person_loc.get("lon"),
        }
        if person_id:
            people_by_id[_entity_ref_key(person_id)] = person_entry
        for candidate in [person_name, person_email]:
            key = _normalize_person_lookup(candidate)
            if key:
                people_by_name[key] = person_entry
        for event_id in _extract_linked_event_ids_from_person(payload):
            linked_people_by_event.setdefault(_entity_ref_key(event_id), []).append(person_entry)

    analysis_rows = []
    people_name_lookup = {k: v.get("participant") for k, v in people_by_id.items()}
    live_attendee_cache = {}
    for row in event_rows:
        payload = row.get("payload") or {}
        event_region = (
            (_extract_region_tags(payload) or [None])[0]
            or row.get("region")
            or payload.get("region")
            or "Other"
        )
        if region != "Global" and region and region.lower() not in str(event_region).lower():
            continue
        event_type = str(_get_row_value(payload, "type", "event_type", "Activity type", "Category") or "Event")
        event_name = str(_get_row_value(payload, "name", "title", "Event name", "Description") or payload.get("id") or "Event")
        event_date = pd.to_datetime(row.get("start_date") or payload.get("start_date") or payload.get("date"), utc=True, errors="coerce")
        event_loc = _resolve_record_location(payload)
        participant_names, participant_ids = _extract_participant_refs(payload, people_name_lookup)
        participants = []
        seen_participants = set()

        for pid in participant_ids:
            person = people_by_id.get(_entity_ref_key(pid))
            if person:
                dedupe_key = person.get("person_id") or person.get("participant")
                if dedupe_key not in seen_participants:
                    seen_participants.add(dedupe_key)
                    participants.append(person)

        for name in participant_names:
            person = people_by_name.get(_normalize_person_lookup(name))
            if person:
                dedupe_key = person.get("person_id") or person.get("participant")
                if dedupe_key not in seen_participants:
                    seen_participants.add(dedupe_key)
                    participants.append(person)

        for person in linked_people_by_event.get(_entity_ref_key(payload.get("id")), []):
            dedupe_key = person.get("person_id") or person.get("participant")
            if dedupe_key not in seen_participants:
                seen_participants.add(dedupe_key)
                participants.append(person)

        event_id = payload.get("id")
        if not participants and event_id:
            cache_key = str(event_id)
            if cache_key not in live_attendee_cache:
                live_attendee_cache[cache_key] = fetch_live_event_attendees(cache_key)
            live_attendees = live_attendee_cache.get(cache_key) or {"names": [], "ids": []}
            for pid in live_attendees.get("ids") or []:
                person = people_by_id.get(_entity_ref_key(pid))
                if person:
                    dedupe_key = person.get("person_id") or person.get("participant")
                    if dedupe_key not in seen_participants:
                        seen_participants.add(dedupe_key)
                        participants.append(person)
            for name in live_attendees.get("names") or []:
                person = people_by_name.get(_normalize_person_lookup(name))
                if person:
                    dedupe_key = person.get("person_id") or person.get("participant")
                    if dedupe_key not in seen_participants:
                        seen_participants.add(dedupe_key)
                        participants.append(person)

        for person in participants:
            p_lat = person.get("participant_lat")
            p_lon = person.get("participant_lon")
            e_lat = event_loc.get("lat")
            e_lon = event_loc.get("lon")
            straight_line_miles = None if None in (p_lat, p_lon, e_lat, e_lon) else _haversine_miles(p_lat, p_lon, e_lat, e_lon)
            road_distance_miles = None if None in (p_lat, p_lon, e_lat, e_lon) else _lookup_road_distance_miles(
                p_lat, p_lon, e_lat, e_lon, road_api_key
            )
            distance_miles = road_distance_miles if road_distance_miles is not None else straight_line_miles
            analysis_rows.append({
                "event_id": str(payload.get("id") or ""),
                "event_name": event_name,
                "event_type": event_type,
                "event_date": event_date,
                "event_region": event_region,
                "event_location": _extract_location_label(payload),
                "event_postcode": event_loc.get("postcode") or "",
                "participant_id": person.get("person_id") or "",
                "participant": person.get("participant") or "Participant",
                "participant_postcode": person.get("participant_postcode") or "",
                "distance_miles": distance_miles,
                "distance_method": "road" if road_distance_miles is not None else ("straight_line" if straight_line_miles is not None else ""),
            })

    df = pd.DataFrame(analysis_rows)
    if df.empty:
        return df
    df["distance_miles"] = pd.to_numeric(df["distance_miles"], errors="coerce")
    return df

FUNDER_SCOPE_PREFIX = "FUNDER::"

def _encode_funder_scope(funder_name):
    name = str(funder_name or "").strip()
    return f"{FUNDER_SCOPE_PREFIX}{name}" if name else ""

def _decode_funder_scope(scope_value):
    raw = str(scope_value or "").strip()
    if raw.startswith(FUNDER_SCOPE_PREFIX):
        return raw[len(FUNDER_SCOPE_PREFIX):].strip()
    return ""

def _best_user_identity_fields(rows, fallback_region="Global", fallback_name=""):
    region = fallback_region
    display_name = fallback_name

    for row in rows or []:
        row_name = str(row.get("name") or "").strip()
        row_region = str(row.get("region") or "").strip()

        if row_name and not display_name:
            display_name = row_name
        if row_region.startswith(FUNDER_SCOPE_PREFIX):
            region = row_region
        elif row_region and (not region or region == fallback_region):
            region = row_region

    return display_name, region or fallback_region

@st.cache_data(show_spinner=False, ttl=300)
def get_assigned_funder_names(max_rows=3000):
    funders = set()
    if DB_TYPE == "supabase":
        try:
            batch_size = 1000
            fetched = 0
            offset = 0
            while fetched < max_rows:
                end_idx = min(offset + batch_size - 1, max_rows - 1)
                rows = (
                    DB_CLIENT.table("user_roles")
                    .select("region")
                    .range(offset, end_idx)
                    .execute()
                    .data
                    or []
                )
                if not rows:
                    break
                for row in rows:
                    funder_name = _decode_funder_scope(row.get("region"))
                    if funder_name:
                        funders.add(funder_name)
                fetched += len(rows)
                if len(rows) < batch_size:
                    break
                offset += batch_size
        except Exception:
            return []
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        for user in db_data.get("users", []):
            funder_name = _decode_funder_scope(user.get("region"))
            if funder_name:
                funders.add(funder_name)
    return sorted(funders, key=lambda x: x.lower())

@st.cache_data(show_spinner=False, ttl=300)
def get_organisation_name_lookup(max_rows=3000):
    lookup = {}
    if DB_TYPE != "supabase":
        return lookup
    try:
        batch_size = 1000
        fetched = 0
        offset = 0
        while fetched < max_rows:
            end_idx = min(offset + batch_size - 1, max_rows - 1)
            rows = (
                DB_CLIENT.table("beacon_organisations")
                .select("payload")
                .range(offset, end_idx)
                .execute()
                .data
                or []
            )
            if not rows:
                break
            for r in rows:
                payload = r.get("payload") or {}
                org_id = payload.get("id")
                org_name = _get_row_value(payload, "name", "Organisation", "Organization", "Display Name")
                if org_id is None or not org_name:
                    continue
                key = _entity_ref_key(org_id)
                if key:
                    lookup[key] = str(org_name).strip()
            fetched += len(rows)
            if len(rows) < batch_size:
                break
            offset += batch_size
    except Exception:
        return {}
    return lookup

def _extract_funder_name(row, org_name_lookup=None):
    name = _get_row_value(
        row,
        "funder",
        "funder_name",
        "funding_body",
        "funding_body_name",
        "donor",
        "donor_name",
        "sponsor",
        "sponsor_name",
        "organisation",
        "organization",
        "organisation_name",
        "organization_name",
        "grantor",
        "grantor_name",
    )
    if isinstance(name, dict):
        display = _get_row_value(name, "name", "title", "display_name")
        if display:
            name = display
        else:
            ref_id = name.get("id")
            resolved = None
            if org_name_lookup and ref_id is not None:
                resolved = org_name_lookup.get(_entity_ref_key(ref_id))
            name = resolved or ""
    if isinstance(name, list):
        name = ", ".join(str(x) for x in name if str(x).strip())
    value = str(name or "").strip()
    if not value:
        # Common fallback: organization field carries only an id reference.
        ref = _get_row_value(row, "organization", "organisation", "organisation_id", "organization_id")
        if isinstance(ref, dict):
            ref = ref.get("id")
        if org_name_lookup and ref is not None:
            mapped = org_name_lookup.get(_entity_ref_key(ref))
            if mapped:
                return mapped
        return "Unknown / Not tagged"
    # If value itself looks like an ID and can be resolved, prefer the readable name.
    if org_name_lookup:
        mapped = org_name_lookup.get(_entity_ref_key(value))
        if mapped:
            return mapped
    # Do not expose unresolved ID-like tokens in the dashboard.
    key_like = _entity_ref_key(value)
    if key_like and (value.isdigit() or len(value) <= 16):
        return "Unknown / Not tagged"
    return value

@st.cache_data(show_spinner=False, ttl=300)
def get_available_funders(max_rows=2000):
    funders = set()
    org_name_lookup = get_organisation_name_lookup()
    for name in get_assigned_funder_names():
        if name:
            funders.add(name)
    if DB_TYPE == "supabase":
        try:
            pay_rows = DB_CLIENT.table("beacon_payments").select("payload").limit(max_rows).execute().data or []
            grant_rows = DB_CLIENT.table("beacon_grants").select("payload").limit(max_rows).execute().data or []
            for r in pay_rows + grant_rows:
                payload = r.get("payload") or {}
                name = _extract_funder_name(payload, org_name_lookup=org_name_lookup)
                if name:
                    funders.add(name)
        except Exception:
            pass
    return sorted(funders, key=lambda x: x.lower())

def _read_uploaded_csv(uploaded_file):
    if uploaded_file is None:
        return []
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        df = pd.read_csv(uploaded_file, sep="\t")
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")

def _upsert_in_batches(
    admin_client,
    table,
    rows,
    on_conflict="id",
    default_chunk_size=200,
    min_chunk_size=25,
    batch_progress_callback=None,
    should_cancel=None,
):
    if not rows:
        return 0
    total = len(rows)
    index = 0
    while index < total:
        if should_cancel and should_cancel():
            raise SyncCancelledError("Manual sync cancelled by user.")
        chunk_size = min(default_chunk_size, total - index)
        while True:
            if should_cancel and should_cancel():
                raise SyncCancelledError("Manual sync cancelled by user.")
            chunk = rows[index:index + chunk_size]
            try:
                admin_client.table(table).upsert(chunk, on_conflict=on_conflict).execute()
                index += len(chunk)
                if batch_progress_callback:
                    try:
                        batch_progress_callback(index, total)
                    except Exception:
                        pass
                break
            except Exception as e:
                msg = str(e).lower()
                is_timeout = "statement timeout" in msg or "57014" in msg
                if is_timeout and chunk_size > min_chunk_size:
                    chunk_size = max(min_chunk_size, chunk_size // 2)
                    time.sleep(1)
                    continue
                if is_timeout:
                    time.sleep(2)
                raise
    return total

def import_beacon_uploads(admin_client, uploads):
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    people_rows = []
    people_seen = {}
    for r in uploads.get("people", []):
        payload = _sanitize(dict(r))
        payload["id"] = _get_row_value(r, "Record ID", "ID", "Id")
        payload["created_at"] = _clean_ts(_get_row_value(r, "Created date", "Created", "Created at"))
        payload["type"] = _to_list(_get_row_value(r, "Type", "Person type", "Role", "Roles", "Tags", "Category"))
        payload["c_region"] = _to_list(_get_row_value(r, "Region", "Location (region)", "Location (Region)", "Location Region", "Region (region)", "Region (Region)"))
        if payload.get("id"):
            people_seen[payload["id"]] = {"id": payload["id"], "payload": payload, "created_at": payload.get("created_at"), "updated_at": now_iso}

    org_rows = []
    org_seen = {}
    for r in uploads.get("organization", []):
        payload = _sanitize(dict(r))
        payload["id"] = _get_row_value(r, "Record ID", "ID", "Id")
        payload["created_at"] = _clean_ts(_get_row_value(r, "Created date", "Created", "Created at"))
        payload["type"] = _get_row_value(r, "Type", "Organisation type", "Organization type", "Category")
        payload["c_region"] = _to_list(_get_row_value(r, "Region", "Location (region)", "Location (Region)", "Location Region", "Region (region)", "Region (Region)"))
        if payload.get("id"):
            org_seen[payload["id"]] = {"id": payload["id"], "payload": payload, "created_at": payload.get("created_at"), "updated_at": now_iso}

    event_rows = []
    event_seen = {}
    for r in uploads.get("event", []):
        payload = _sanitize(dict(r))
        payload["id"] = _get_row_value(r, "Record ID", "ID", "Id")
        payload["start_date"] = _clean_ts(_get_row_value(r, "Start date", "Start", "Date", "Event date"))
        payload["type"] = _get_row_value(r, "Type", "Event type", "Activity type", "Category")
        payload["c_region"] = _to_list(_get_row_value(r, "Location (region)", "Location (Region)", "Location Region", "Region", "Region (region)", "Region (Region)"))
        payload["number_of_attendees"] = _get_row_value(r, "Number of attendees", "Attendees", "Participants", "Total participants", "Participant count")
        if payload.get("id"):
            event_seen[payload["id"]] = {
                "id": payload["id"],
                "payload": payload,
                "start_date": payload.get("start_date"),
                "region": (payload.get("c_region") or [None])[0],
                "updated_at": now_iso
            }

    payment_rows = []
    payment_seen = {}
    for r in uploads.get("payment", []):
        payload = _sanitize(dict(r))
        payload["id"] = _get_row_value(r, "Record ID", "ID", "Id")
        payload["payment_date"] = _clean_ts(_get_row_value(r, "Payment date", "Date", "Received date"))
        payload["amount"] = _get_row_value(r, "Amount (value)", "Amount", "Value")
        if payload.get("id"):
            payment_seen[payload["id"]] = {"id": payload["id"], "payload": payload, "payment_date": payload.get("payment_date"), "updated_at": now_iso}

    grant_rows = []
    grant_seen = {}
    for r in uploads.get("grant", []):
        payload = _sanitize(dict(r))
        payload["id"] = _get_row_value(r, "Record ID", "ID", "Id")
        payload["close_date"] = _clean_ts(_get_row_value(r, "Award date", "Close date", "Decision date"))
        payload["amount"] = _get_row_value(r, "Amount granted (value)", "Amount requested (value)", "Value (value)", "Amount", "Value")
        payload["stage"] = _get_row_value(r, "Stage", "Status", "Grant stage")
        if payload.get("id"):
            grant_seen[payload["id"]] = {"id": payload["id"], "payload": payload, "close_date": payload.get("close_date"), "updated_at": now_iso}

    people_rows = list(people_seen.values())
    org_rows = list(org_seen.values())
    event_rows = list(event_seen.values())
    payment_rows = list(payment_seen.values())
    grant_rows = list(grant_seen.values())

    if people_rows:
        _upsert_in_batches(admin_client, "beacon_people", people_rows, on_conflict="id")
    if org_rows:
        _upsert_in_batches(admin_client, "beacon_organisations", org_rows, on_conflict="id")
    if event_rows:
        _upsert_in_batches(admin_client, "beacon_events", event_rows, on_conflict="id")
    if payment_rows:
        _upsert_in_batches(admin_client, "beacon_payments", payment_rows, on_conflict="id")
    if grant_rows:
        _upsert_in_batches(admin_client, "beacon_grants", grant_rows, on_conflict="id")

    return {
        "people": len(people_rows),
        "organisations": len(org_rows),
        "events": len(event_rows),
        "payments": len(payment_rows),
        "grants": len(grant_rows),
    }

def _get_secret_or_env(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets.get(key) or default
    except Exception:
        pass
    return os.getenv(key, default)

def _build_beacon_url(base_url, account_id, endpoint):
    base = (base_url or "").strip()
    if not base:
        base = "https://api.beaconcrm.org/v1/account/{account_id}"
    if "{account_id}" in base:
        if not account_id:
            raise ValueError("Missing BEACON_ACCOUNT_ID for base URL template.")
        base = base.format(account_id=account_id)
    base = base.rstrip("/")
    if endpoint.startswith("/"):
        return f"{base}{endpoint}"
    if base.endswith("/entities"):
        return f"{base}/{endpoint}"
    return f"{base}/entities/{endpoint}"

def _extract_result_list(response_json):
    if isinstance(response_json, list):
        return response_json
    if not isinstance(response_json, dict):
        return []
    if isinstance(response_json.get("results"), list):
        return response_json.get("results") or []
    if isinstance(response_json.get("data"), list):
        return response_json.get("data") or []
    return []

def _extract_total_count(response_json):
    if not isinstance(response_json, dict):
        return None
    meta = response_json.get("meta")
    if isinstance(meta, dict):
        total = meta.get("total")
        if isinstance(total, int):
            return total
    total = response_json.get("total")
    if isinstance(total, int):
        return total
    return None

def _extract_page_progress(response_json):
    if not isinstance(response_json, dict):
        return None, None
    meta = response_json.get("meta")
    if isinstance(meta, dict):
        current_page = meta.get("current_page")
        total_pages = meta.get("total_pages")
        if isinstance(current_page, int) and isinstance(total_pages, int):
            return current_page, total_pages
    current_page = response_json.get("current_page")
    total_pages = response_json.get("total_pages")
    if isinstance(current_page, int) and isinstance(total_pages, int):
        return current_page, total_pages
    return None, None

def _extract_entity(record):
    if not isinstance(record, dict):
        return {}
    if isinstance(record.get("entity"), dict):
        entity = dict(record.get("entity") or {})
        # Preserve wrapper metadata/relationships when Beacon sends related data
        # outside entity (common for participant links on events).
        for k, v in record.items():
            if k == "entity":
                continue
            if k not in entity:
                entity[k] = v
        return entity
    return record

@st.cache_data(show_spinner=False, ttl=300)
def fetch_live_event_attendees(event_id):
    target = str(event_id).strip()
    if not target:
        return {"names": [], "ids": [], "endpoint": None}

    beacon_key = _get_secret_or_env("BEACON_API_KEY")
    beacon_base_url = _get_secret_or_env("BEACON_BASE_URL")
    beacon_account_id = _get_secret_or_env("BEACON_ACCOUNT_ID")
    if not beacon_key:
        return {"names": [], "ids": [], "endpoint": None}

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

    target_key = _id_key(target)
    headers = {
        "Authorization": f"Bearer {beacon_key}",
        "Content-Type": "application/json",
        "Beacon-Application": "developer_api",
    }
    endpoint_candidates = [
        _get_secret_or_env("BEACON_EVENT_ATTENDEES_ENDPOINT"),
        "event_attendee",
        "event_attendees",
        "event_attendance",
        "event_attendances",
        "attendance",
        "attendees",
        "event-registration",
        "event_registrations",
    ]
    endpoint_candidates = [e for e in endpoint_candidates if e]

    def _attendee_event_id(att):
        direct = _get_row_value(att, "event_id", "eventId", "event")
        direct = _extract_linked_id(direct)
        if direct not in [None, ""]:
            return direct
        rel = att.get("relationships") if isinstance(att, dict) else None
        if isinstance(rel, dict):
            for key in ("event", "events", "activity", "session"):
                ref = rel.get(key)
                if isinstance(ref, dict):
                    data = ref.get("data")
                    if isinstance(data, dict) and data.get("id") not in [None, ""]:
                        return data.get("id")
                    if ref.get("id") not in [None, ""]:
                        return ref.get("id")
        return None

    def _attendee_name(att):
        name = _get_row_value(
            att,
            "name",
            "full_name",
            "display_name",
            "participant_name",
            "attendee_name",
            "person_name",
            "contact_name",
            "email",
        )
        if name:
            return str(name).strip()
        person = att.get("person") if isinstance(att, dict) else None
        if isinstance(person, dict):
            return str(_get_row_value(person, "name", "full_name", "display_name", "email") or "").strip()
        contact = att.get("contact") if isinstance(att, dict) else None
        if isinstance(contact, dict):
            return str(_get_row_value(contact, "name", "full_name", "display_name", "email") or "").strip()
        return ""

    found_names = []
    found_ids = []
    seen_names = set()
    seen_ids = set()
    for endpoint in endpoint_candidates:
        try:
            url = _build_beacon_url(beacon_base_url, beacon_account_id, endpoint)
            for page in range(1, 11):
                params = {
                    "page": page,
                    "per_page": 100,
                    "sort_by": "created_at",
                    "sort_direction": "desc",
                    "event_id": target,
                }
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code >= 400:
                    break
                payload = resp.json()
                rows = _extract_result_list(payload)
                if not rows:
                    break
                for raw in rows:
                    att = _extract_entity(raw)
                    att_event_id = _attendee_event_id(att)
                    if _id_key(att_event_id) != target_key:
                        continue
                    pid = _extract_linked_id(_get_row_value(att, "person_id", "participant_id", "contact_id", "person", "participant", "contact"))
                    if pid is not None:
                        p = str(pid).strip()
                        if p and p not in seen_ids:
                            seen_ids.add(p)
                            found_ids.append(p)
                    n = _attendee_name(att)
                    if n:
                        nk = n.lower()
                        if nk not in seen_names:
                            seen_names.add(nk)
                            found_names.append(n)
                if len(rows) < 100:
                    break
            if found_names or found_ids:
                return {"names": found_names, "ids": found_ids, "endpoint": endpoint}
        except Exception:
            continue

    return {"names": found_names, "ids": found_ids, "endpoint": None}

def _extract_region_tags(record):
    candidates = []
    for key in (
        "c_region",
        "region",
        "Region",
        "location_region",
        "location",
        "Location (region)",
        "Location Region",
    ):
        if key in record and record.get(key) not in [None, ""]:
            candidates.extend(_to_list(record.get(key)))
    if isinstance(record.get("address"), list):
        for addr in record.get("address"):
            if isinstance(addr, dict):
                if addr.get("region"):
                    candidates.extend(_to_list(addr.get("region")))
                if addr.get("country"):
                    candidates.extend(_to_list(addr.get("country")))
    seen = set()
    out = []
    for item in candidates:
        s = str(item).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out

def _fetch_beacon_entities(base_url, api_key, account_id, endpoint, per_page=50, max_pages=200, should_cancel=None):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Beacon-Application": "developer_api",
    }
    all_rows = []
    page = 1
    while page <= max_pages:
        if should_cancel and should_cancel():
            raise SyncCancelledError("Manual sync cancelled by user.")
        url = _build_beacon_url(base_url, account_id, endpoint)
        params = {
            "page": page,
            "per_page": per_page,
            "sort_by": "created_at",
            "sort_direction": "desc",
        }
        resp = None
        for attempt in range(4):
            if should_cancel and should_cancel():
                raise SyncCancelledError("Manual sync cancelled by user.")
            resp = requests.get(url, headers=headers, params=params, timeout=45)
            if resp.status_code not in (429, 500, 502, 503, 504):
                break
            if attempt < 3:
                time.sleep(2 ** attempt)
        if resp is None:
            raise RuntimeError(f"Beacon API request failed for {endpoint}: no response")
        if resp.status_code >= 400:
            try:
                details = resp.json()
            except Exception:
                details = resp.text[:500]
            raise RuntimeError(f"Beacon API error {resp.status_code} for {endpoint}: {details}")
        payload = resp.json()
        rows = _extract_result_list(payload)
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < per_page:
            break
        total = _extract_total_count(payload)
        if isinstance(total, int) and len(all_rows) >= total:
            break
        current_page, total_pages = _extract_page_progress(payload)
        if isinstance(current_page, int) and isinstance(total_pages, int) and current_page >= total_pages:
            break
        page += 1
    return all_rows

def run_beacon_api_smoke_test():
    beacon_key = _get_secret_or_env("BEACON_API_KEY")
    beacon_base_url = _get_secret_or_env("BEACON_BASE_URL")
    beacon_account_id = _get_secret_or_env("BEACON_ACCOUNT_ID")
    if not beacon_key:
        raise RuntimeError("Missing BEACON_API_KEY in Streamlit secrets or environment.")
    if not beacon_base_url and not beacon_account_id:
        raise RuntimeError("Set BEACON_BASE_URL (preferred) or BEACON_ACCOUNT_ID.")

    endpoint = "person"
    url = _build_beacon_url(beacon_base_url, beacon_account_id, endpoint)
    headers = {
        "Authorization": f"Bearer {beacon_key}",
        "Content-Type": "application/json",
        "Beacon-Application": "developer_api",
    }
    params = {
        "page": 1,
        "per_page": 1,
        "sort_by": "created_at",
        "sort_direction": "desc",
    }

    started = time.time()
    resp = requests.get(url, headers=headers, params=params, timeout=45)
    elapsed_ms = int((time.time() - started) * 1000)

    try:
        payload = resp.json()
    except Exception:
        payload = {}

    if resp.status_code >= 400:
        details = payload if isinstance(payload, dict) and payload else (resp.text[:500] or "No details")
        raise RuntimeError(f"Beacon smoke test failed ({resp.status_code}): {details}")

    records = _extract_result_list(payload)
    has_records_array = isinstance(records, list)

    has_data_array = isinstance(payload, dict) and isinstance(payload.get("data"), list)
    has_meta = isinstance(payload, dict) and isinstance(payload.get("meta"), dict)
    meta = payload.get("meta") if isinstance(payload, dict) else {}
    required_meta_keys = ("current_page", "per_page", "total")
    missing_meta_keys = [k for k in required_meta_keys if not isinstance(meta, dict) or k not in meta]
    docs_compliant_shape = has_data_array and has_meta and len(missing_meta_keys) == 0

    # Accept older Beacon response shapes while still surfacing docs-compliance status.
    if not has_records_array:
        raise RuntimeError(
            "Beacon smoke test response does not include a records array "
            "(expected either data[] or results[])."
        )

    current_page, total_pages = _extract_page_progress(payload)
    total = _extract_total_count(payload)
    if current_page is None:
        current_page = params["page"]
    if total is None:
        total = len(records)
    if total_pages is None:
        per_page = params["per_page"]
        total_pages = max(1, int((total + per_page - 1) / per_page)) if isinstance(total, int) else 1

    return {
        "status_code": resp.status_code,
        "response_time_ms": elapsed_ms,
        "endpoint": endpoint,
        "records_in_page": len(records),
        "meta": {
            "current_page": current_page,
            "per_page": meta.get("per_page") if isinstance(meta, dict) else params["per_page"],
            "total": total,
            "total_pages": total_pages,
        },
        "checks": {
            "has_records_array": has_records_array,
            "has_data_array": has_data_array,
            "has_meta": has_meta,
            "required_meta_present": len(missing_meta_keys) == 0,
            "docs_compliant_shape": docs_compliant_shape,
            "legacy_compatible_shape": has_records_array and not docs_compliant_shape,
        },
    }

def sync_beacon_api_to_supabase(admin_client, progress_callback=None, should_cancel=None):
    def _status_text(progress, message):
        return f"{int(progress)}% | {message}"

    def _report(progress, message):
        if should_cancel and should_cancel():
            raise SyncCancelledError("Manual sync cancelled by user.")
        if progress_callback:
            progress_callback(progress, _status_text(progress, message))

    def _check_cancel():
        if should_cancel and should_cancel():
            raise SyncCancelledError("Manual sync cancelled by user.")

    total_started = time.time()
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    beacon_key = _get_secret_or_env("BEACON_API_KEY")
    beacon_base_url = _get_secret_or_env("BEACON_BASE_URL")
    beacon_account_id = _get_secret_or_env("BEACON_ACCOUNT_ID")
    if not beacon_key:
        raise RuntimeError("Missing BEACON_API_KEY in Streamlit secrets or environment.")

    fetch_plan = [
        ("people", "person", "people"),
        ("organisations", "organization", "organisations"),
        ("events", "event", "events"),
        ("payments", "payment", "payments"),
        ("subscriptions", "subscription", "subscriptions"),
        ("grants", "grant", "grants"),
    ]
    datasets = {}
    fetch_breakdown_ms = {}
    fetch_started = time.time()
    _report(5, "Starting Beacon API sync...")
    for idx, (dataset_key, endpoint, label) in enumerate(fetch_plan):
        _check_cancel()
        fetch_start = 5 + int((idx / len(fetch_plan)) * 45)
        fetch_end = 5 + int(((idx + 1) / len(fetch_plan)) * 45)
        _report(fetch_start, f"Fetching Beacon {label} ({idx + 1} of {len(fetch_plan)} datasets)...")
        endpoint_started = time.time()
        datasets[dataset_key] = _fetch_beacon_entities(
            beacon_base_url, beacon_key, beacon_account_id, endpoint, should_cancel=should_cancel
        )
        fetch_breakdown_ms[dataset_key] = int((time.time() - endpoint_started) * 1000)
        _report(fetch_end, f"Fetched Beacon {label}: {len(datasets[dataset_key])} records.")

    # Optional direct attendee source (preferred for participant drill-down).
    configured_attendee_endpoint = _get_secret_or_env("BEACON_EVENT_ATTENDEES_ENDPOINT")
    attendee_endpoint_candidates = [
        (configured_attendee_endpoint, "event attendees"),
        ("event_attendee", "event attendees"),
        ("event_attendees", "event attendees"),
        ("event_attendance", "event attendance"),
        ("event_attendances", "event attendance"),
        ("attendance", "attendance"),
        ("attendees", "attendees"),
        ("event_registration", "event registrations"),
        ("event_registrations", "event registrations"),
    ]
    datasets["event_attendees"] = []
    attendee_fetch_started = time.time()
    for endpoint, label in attendee_endpoint_candidates:
        _check_cancel()
        if not endpoint:
            continue
        try:
            rows = _fetch_beacon_entities(
                beacon_base_url, beacon_key, beacon_account_id, endpoint, should_cancel=should_cancel
            )
            datasets["event_attendees"] = rows
            _report(50, f"Fetched Beacon {label}: {len(rows)} records from endpoint '{endpoint}'.")
            break
        except Exception:
            continue
    fetch_breakdown_ms["event_attendees"] = int((time.time() - attendee_fetch_started) * 1000)
    fetch_duration_ms = int((time.time() - fetch_started) * 1000)

    _report(55, "Transforming Beacon records...")
    _check_cancel()
    transform_started = time.time()

    people_seen = {}
    for row in datasets["people"]:
        entity = _sanitize(_extract_entity(row))
        rec_id = entity.get("id")
        if not rec_id:
            continue
        entity["id"] = rec_id
        entity["created_at"] = _clean_ts(entity.get("created_at"))
        entity["type"] = _to_list(entity.get("type"))
        if not entity.get("c_region"):
            entity["c_region"] = _extract_region_tags(entity)
        people_seen[rec_id] = {"id": rec_id, "payload": entity, "created_at": entity.get("created_at"), "updated_at": now_iso}

    people_name_by_id = {}
    for p_id, p_row in people_seen.items():
        p_payload = p_row.get("payload") or {}
        p_name = _get_row_value(p_payload, "name", "full_name", "Display Name", "email") or p_id
        people_name_by_id[_entity_ref_key(p_id)] = str(p_name).strip()

    org_seen = {}
    for row in datasets["organisations"]:
        entity = _sanitize(_extract_entity(row))
        rec_id = entity.get("id")
        if not rec_id:
            continue
        entity["id"] = rec_id
        entity["created_at"] = _clean_ts(entity.get("created_at"))
        if isinstance(entity.get("type"), list):
            entity["type"] = ", ".join([str(v) for v in entity.get("type") if str(v).strip()])
        if not entity.get("c_region"):
            entity["c_region"] = _extract_region_tags(entity)
        org_seen[rec_id] = {"id": rec_id, "payload": entity, "created_at": entity.get("created_at"), "updated_at": now_iso}

    attendee_map = {}

    def _attendee_event_id(att):
        direct = _get_row_value(att, "event_id", "eventId", "event")
        direct = _extract_linked_id(direct)
        if direct not in [None, ""]:
            return str(direct)
        for key in ("event", "activity", "session"):
            ref = att.get(key)
            if isinstance(ref, dict) and ref.get("id") not in [None, ""]:
                return str(ref.get("id"))
        rel = att.get("relationships")
        if isinstance(rel, dict):
            for key in ("event", "events", "activity", "session"):
                ref = rel.get(key)
                if isinstance(ref, dict):
                    if isinstance(ref.get("data"), dict) and ref["data"].get("id") not in [None, ""]:
                        return str(ref["data"]["id"])
                    if ref.get("id") not in [None, ""]:
                        return str(ref.get("id"))
                    if isinstance(ref.get("data"), list) and ref["data"]:
                        first = ref["data"][0]
                        if isinstance(first, dict) and first.get("id") not in [None, ""]:
                            return str(first.get("id"))
        return None

    def _attendee_person_id(att):
        direct = _get_row_value(att, "person_id", "contact_id", "participant_id", "person", "contact", "participant")
        direct = _extract_linked_id(direct)
        if direct not in [None, ""]:
            return str(direct)
        rel = att.get("relationships")
        if isinstance(rel, dict):
            for key in ("person", "people", "contact", "participant"):
                ref = rel.get(key)
                if isinstance(ref, dict):
                    if isinstance(ref.get("data"), dict) and ref["data"].get("id") not in [None, ""]:
                        return str(ref["data"]["id"])
                    if ref.get("id") not in [None, ""]:
                        return str(ref.get("id"))
        return None

    def _attendee_name(att):
        return _get_row_value(
            att,
            "name",
            "full_name",
            "display_name",
            "participant_name",
            "attendee_name",
            "person_name",
            "contact_name",
            "email",
        )

    event_attendee_records = {}
    attendee_seen = {}
    for row in datasets.get("event_attendees") or []:
        att = _sanitize(_extract_entity(row))
        rec_id = att.get("id") or _get_row_value(att, "Record ID", "ID", "Id")
        if not rec_id:
            continue
        att["id"] = str(rec_id)
        att["created_at"] = _clean_ts(att.get("created_at") or _get_row_value(att, "Created date", "Created", "Created at"))
        event_id = _attendee_event_id(att)
        if not event_id:
            continue
        person_id = _attendee_person_id(att)
        if person_id:
            att["person_id"] = str(person_id)
        att["event_id"] = str(event_id)
        name = _attendee_name(att)
        if (not name) and person_id:
            name = people_name_by_id.get(_entity_ref_key(person_id))
        bucket = attendee_map.setdefault(event_id, {"names": set(), "ids": set()})
        if person_id:
            bucket["ids"].add(str(person_id))
        if name:
            bucket["names"].add(str(name).strip())
        norm_event_id = _entity_ref_key(event_id)
        records_bucket = event_attendee_records.setdefault(event_id, [])
        records_bucket.append(att)
        if norm_event_id and norm_event_id != event_id:
            event_attendee_records.setdefault(norm_event_id, []).append(att)
        attendee_seen[str(rec_id)] = {
            "id": str(rec_id),
            "event_id": str(event_id),
            "person_id": str(person_id) if person_id else None,
            "created_at": att.get("created_at"),
            "updated_at": now_iso,
            "payload": att,
        }

    event_seen = {}
    for row in datasets["events"]:
        entity = _sanitize(_extract_entity(row))
        rec_id = entity.get("id")
        if not rec_id:
            continue
        entity["id"] = rec_id
        entity["start_date"] = _clean_ts(entity.get("start_date") or entity.get("date") or entity.get("created_at"))
        if not entity.get("c_region"):
            entity["c_region"] = _extract_region_tags(entity)
        entity["type"] = entity.get("type") or entity.get("event_type") or entity.get("category")
        attendee_bucket = attendee_map.get(str(rec_id), {"names": set(), "ids": set()})
        direct_names = sorted([n for n in attendee_bucket["names"] if n])
        direct_ids = sorted([i for i in attendee_bucket["ids"] if i])
        if direct_names:
            entity["participant_list"] = direct_names
        if direct_ids:
            entity["participant_ids"] = direct_ids
        direct_count = max(len(direct_names), len(direct_ids))
        existing_count = entity.get("number_of_attendees") or entity.get("attendees") or entity.get("participant_count")
        if existing_count in [None, ""] and direct_count > 0:
            entity["number_of_attendees"] = direct_count
        else:
            entity["number_of_attendees"] = existing_count
        attendee_records_for_event = event_attendee_records.get(str(rec_id)) or event_attendee_records.get(_entity_ref_key(rec_id)) or []
        event_seen[rec_id] = {
            "id": rec_id,
            "payload": entity,
            "start_date": entity.get("start_date"),
            "region": (entity.get("c_region") or [None])[0],
            "updated_at": now_iso,
        }

    payment_seen = {}
    for row in datasets["payments"] + datasets["subscriptions"]:
        entity = _sanitize(_extract_entity(row))
        rec_id = entity.get("id")
        if not rec_id:
            continue
        if rec_id in payment_seen:
            continue
        entity["id"] = rec_id
        entity["payment_date"] = _clean_ts(entity.get("payment_date") or entity.get("date") or entity.get("created_at"))
        entity["amount"] = entity.get("amount") or entity.get("value")
        payment_seen[rec_id] = {"id": rec_id, "payload": entity, "payment_date": entity.get("payment_date"), "updated_at": now_iso}

    grant_seen = {}
    for row in datasets["grants"]:
        entity = _sanitize(_extract_entity(row))
        rec_id = entity.get("id")
        if not rec_id:
            continue
        entity["id"] = rec_id
        entity["close_date"] = _clean_ts(entity.get("close_date") or entity.get("award_date") or entity.get("created_at"))
        entity["amount"] = entity.get("amount") or entity.get("amount_granted") or entity.get("value")
        entity["stage"] = entity.get("stage") or entity.get("status")
        grant_seen[rec_id] = {"id": rec_id, "payload": entity, "close_date": entity.get("close_date"), "updated_at": now_iso}

    people_rows = list(people_seen.values())
    org_rows = list(org_seen.values())
    event_rows = list(event_seen.values())
    attendee_rows = list(attendee_seen.values())
    payment_rows = list(payment_seen.values())
    grant_rows = list(grant_seen.values())
    transform_duration_ms = int((time.time() - transform_started) * 1000)

    total_records = len(people_rows) + len(org_rows) + len(event_rows) + len(attendee_rows) + len(payment_rows) + len(grant_rows)
    synced_records = 0

    def _upsert_with_progress(table_name, rows, start_pct, end_pct, label):
        if not rows:
            return 0

        def _on_batch(done, total):
            if total <= 0:
                frac = 1.0
            else:
                frac = max(0.0, min(1.0, done / total))
            pct = start_pct + int((end_pct - start_pct) * frac)
            overall_synced = synced_records + done
            _report(pct, f"Upserting {label}... {overall_synced} out of {total_records} records synced.")

        _check_cancel()
        _upsert_in_batches(
            admin_client,
            table_name,
            rows,
            on_conflict="id",
            batch_progress_callback=_on_batch,
            should_cancel=should_cancel,
        )
        return len(rows)

    upsert_started = time.time()
    _report(68, f"Preparing import: {synced_records} out of {total_records} records synced.")
    _report(72, f"Upserting people ({len(people_rows)}) and organisations ({len(org_rows)})...")
    if people_rows:
        synced_records += _upsert_with_progress("beacon_people", people_rows, 72, 76, "people")
        _report(76, f"People upserted: {synced_records} out of {total_records} records synced.")
    if org_rows:
        synced_records += _upsert_with_progress("beacon_organisations", org_rows, 76, 80, "organisations")
        _report(80, f"Organisations upserted: {synced_records} out of {total_records} records synced.")

    _report(84, f"Upserting events ({len(event_rows)}), attendees ({len(attendee_rows)}) and payments ({len(payment_rows)})...")
    if event_rows:
        synced_records += _upsert_with_progress("beacon_events", event_rows, 84, 87, "events")
        _report(87, f"Events upserted: {synced_records} out of {total_records} records synced.")
    if attendee_rows:
        synced_records += _upsert_with_progress("beacon_event_attendees", attendee_rows, 87, 90, "event attendees")
        _report(90, f"Event attendees upserted: {synced_records} out of {total_records} records synced.")
    if payment_rows:
        synced_records += _upsert_with_progress("beacon_payments", payment_rows, 90, 94, "payments")
        _report(92, f"Payments upserted: {synced_records} out of {total_records} records synced.")

    _report(94, f"Upserting grants ({len(grant_rows)})...")
    if grant_rows:
        synced_records += _upsert_with_progress("beacon_grants", grant_rows, 94, 97, "grants")
        _report(97, f"Grants upserted: {synced_records} out of {total_records} records synced.")
    upsert_duration_ms = int((time.time() - upsert_started) * 1000)

    _report(100, f"Beacon API sync complete. {synced_records} out of {total_records} records synced.")
    total_duration_ms = int((time.time() - total_started) * 1000)

    return {
        "people": len(people_rows),
        "organisations": len(org_rows),
        "events": len(event_rows),
        "event_attendees": len(attendee_rows),
        "payments": len(payment_rows),
        "grants": len(grant_rows),
        "synced_at": now_iso,
        "fetch_duration_ms": fetch_duration_ms,
        "transform_duration_ms": transform_duration_ms,
        "upsert_duration_ms": upsert_duration_ms,
        "total_duration_ms": total_duration_ms,
        "fetch_breakdown_ms": fetch_breakdown_ms,
    }

# --- LOCAL FILE HELPERS (Fallback) ---

def load_local_json(filepath, default_content):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            json.dump(default_content, f, indent=4)
        return default_content
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_content

def save_local_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def init_files():
    # 1. LOCAL INITIALIZATION
    if DB_TYPE == 'local':
        if not os.path.exists(CASE_STUDIES_FILE):
            save_local_json(CASE_STUDIES_FILE, [])
        if not os.path.exists(USER_DB_FILE):
            default_db = {
                "users": [
                    {
                        "name": "Scott Harvey-Whittle",
                        "email": "scott.harvey-whittle@mindovermountains.org.uk",
                        "password": "ArthurMillwood01!", 
                        "role": "Admin",
                        "region": "Global"
                    }
                ]
            }
            save_local_json(USER_DB_FILE, default_db)
            
    # 2. SUPABASE INITIALIZATION
    elif DB_TYPE == 'supabase':
        # Auth users are managed in Supabase Auth, but app roles must exist in public.roles.
        ensure_supabase_roles()

# --- AUTHENTICATION LOGIC ---

def verify_user(email, password):
    email = email.strip().lower()
    password = password.strip()

    if not email or not password:
        return "missing_fields", None, None, None, None

    def _local_roles(user):
        roles_field = user.get("roles")
        if isinstance(roles_field, list) and roles_field:
            return roles_field
        role_val = user.get("role")
        return [role_val] if role_val else []

    if DB_TYPE == 'supabase':
        try:
            auth_resp = DB_CLIENT.auth.sign_in_with_password({"email": email, "password": password})
            if not auth_resp or not auth_resp.user:
                return "user_not_found", None, None, None, None
            user_id = auth_resp.user.id

            role_resp = DB_CLIENT.table('user_roles') \
                .select("region, name, must_change_password, roles(name)") \
                .eq("user_id", user_id) \
                .execute()
            if not role_resp.data:
                return "user_not_found", None, None, None, None
            rows = role_resp.data
            role_names = []
            display_name, region = _best_user_identity_fields(
                rows,
                fallback_region="Global",
                fallback_name=str(auth_resp.user.email or "").strip(),
            )
            must_change = False
            for row in rows:
                role_name = (row.get("roles") or {}).get("name")
                if role_name:
                    role_names.append(role_name)
                if row.get("must_change_password"):
                    must_change = True
            dedup_roles = [r for r in dict.fromkeys(role_names)]
            if not dedup_roles:
                dedup_roles = [role_name] if role_name else []
            if not dedup_roles:
                dedup_roles = ["RPL"]
            primary_role = _primary_role_from_list(dedup_roles) or dedup_roles[0]
            return "success", primary_role, region, display_name, must_change, dedup_roles
        except Exception as e:
            msg = str(e)
            if "Invalid login credentials" in msg:
                return "wrong_password", None, None, None, None
            st.error(f"Database Error: {e}")
            return "error", None, None, None, None
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        users_list = db_data.get("users", [])

        for i, user in enumerate(users_list):
            if str(user.get('email', '')).strip().lower() == email:
                stored_pw = str(user.get('password', '')).strip()

                if not stored_pw.startswith('$pbkdf2-sha256'):
                    if stored_pw == password:
                        new_hash = pbkdf2_sha256.hash(stored_pw)
                        users_list[i]['password'] = new_hash
                        db_data["users"] = users_list
                        save_local_json(USER_DB_FILE, db_data)
                        roles = _local_roles(user)
                        primary_role = _primary_role_from_list(roles) or user.get('role')
                        return "success", primary_role, user.get('region', 'Global'), user.get('name', email), False, roles
                    return "wrong_password", None, None, None, None

                try:
                    if pbkdf2_sha256.verify(password, stored_pw):
                        roles = _local_roles(user)
                        primary_role = _primary_role_from_list(roles) or user.get('role')
                        return "success", primary_role, user.get('region', 'Global'), user.get('name', email), False, roles
                except ValueError:
                    pass
                return "wrong_password", None, None, None, None

        return "user_not_found", None, None, None, None

def create_user(name, email, password, roles, region):
    email = email.strip().lower()
    hashed_pw = pbkdf2_sha256.hash(password)
    roles = [r for r in (roles or []) if r]
    if not roles:
        return False
    
    if DB_TYPE == 'supabase':
        try:
            ensure_supabase_roles()
            admin_client = get_admin_client()
            if not admin_client:
                st.error("Admin client not available. Check Supabase secrets.")
                return False
            # Create auth user (requires service role key)
            user_resp = admin_client.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            user_id = user_resp.user.id

            inserted = []
            for role_name in roles:
                role_resp = admin_client.table("roles").select("id").eq("name", role_name).execute()
                if not role_resp.data:
                    continue
                role_id = role_resp.data[0]["id"]
                admin_client.table('user_roles').insert({
                    "user_id": user_id,
                    "role_id": role_id,
                    "region": region,
                    "email": email,
                    "name": name,
                    "must_change_password": True
                }).execute()
                inserted.append(role_name)
            if not inserted:
                return False

            # --- AUDIT LOG ---
            log_audit_event("User Created", {"target_email": email, "roles": inserted, "region": region})
           
            return True
        except Exception as e:
            st.error(f"Error creating user: {e}")
            return False
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        users_list = db_data.get("users", [])
        for user in users_list:
            if user.get('email', '').strip().lower() == email:
                return False
        
        users_list.append({
            "name": name, 
            "email": email, 
            "password": hashed_pw, 
            "roles": roles, 
            "role": roles[0] if roles else "",
            "region": region
        })
        db_data["users"] = users_list
        save_local_json(USER_DB_FILE, db_data)
        return True

def update_user_roles(email, new_roles, audit_reason=None, audit_confirmed=False):
    email = email.strip().lower()
    roles = [r for r in (new_roles or []) if r]
    if not roles:
        return
    if DB_TYPE == 'supabase':
        ensure_supabase_roles()
        admin_client = get_admin_client()
        if not admin_client:
            return
        existing = admin_client.table('user_roles').select("user_id, region, name").eq('email', email).limit(1).execute()
        if not existing.data:
            return
        user_id = existing.data[0]["user_id"]
        region = existing.data[0].get("region", "Global")
        admin_client.table('user_roles').delete().eq('email', email).execute()
        inserted = []
        for role_name in roles:
            role_resp = admin_client.table("roles").select("id").eq("name", role_name).execute()
            if not role_resp.data:
                continue
            role_id = role_resp.data[0]["id"]
            admin_client.table('user_roles').insert({
                "user_id": user_id,
                "role_id": role_id,
                "region": region,
                "email": email,
                "name": existing.data[0].get("name"),
                "must_change_password": True
            }).execute()
            inserted.append(role_name)
        details = {"target_email": email, "new_roles": inserted}
        if audit_reason:
            details["reason"] = audit_reason
        details["confirmed"] = bool(audit_confirmed)
        log_audit_event("Role Updated", details)
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        users_list = db_data.get("users", [])
        for user in users_list:
            if user.get('email', '').strip().lower() == email:
                user['roles'] = roles
                user['role'] = roles[0]
                save_local_json(USER_DB_FILE, db_data)
                return

def update_user_region(email, new_region):
    email = email.strip().lower()
    if DB_TYPE == 'supabase':
        admin_client = get_admin_client()
        if not admin_client:
            return
        admin_client.table('user_roles').update({"region": new_region}).eq('email', email).execute()
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        users_list = db_data.get("users", [])
        for user in users_list:
            if user.get('email', '').strip().lower() == email:
                user['region'] = new_region
                save_local_json(USER_DB_FILE, db_data)
                return

def delete_user(email, audit_reason=None, audit_confirmed=False):
    email = email.strip().lower()
    if DB_TYPE == 'supabase':
        admin_client = get_admin_client()
        if not admin_client:
            return
        # Remove mapping and auth user
        role_resp = admin_client.table('user_roles').select("user_id").eq('email', email).execute()
        if role_resp.data:
            user_id = role_resp.data[0]["user_id"]
            admin_client.table('user_roles').delete().eq('email', email).execute()
            admin_client.auth.admin.delete_user(user_id)
            
            # --- AUDIT LOG ---
            details = {"target_email": email}
            if audit_reason:
                details["reason"] = audit_reason
            details["confirmed"] = bool(audit_confirmed)
            log_audit_event("User Deleted", details)
            
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        users_list = db_data.get("users", [])
        new_list = [u for u in users_list if u.get('email', '').strip().lower() != email]
        if len(new_list) < len(users_list):
            db_data["users"] = new_list
            save_local_json(USER_DB_FILE, db_data)

def reset_password(email, new_password):
    email = email.strip().lower()
    new_hash = pbkdf2_sha256.hash(new_password)
    
    if DB_TYPE == 'supabase':
        admin_client = get_admin_client()
        if not admin_client:
            return
        role_resp = admin_client.table('user_roles').select("user_id").eq('email', email).execute()
        if role_resp.data:
            user_id = role_resp.data[0]["user_id"]
            admin_client.auth.admin.update_user_by_id(user_id, {"password": new_password})
            
            # --- AUDIT LOG ---
            log_audit_event("Password Reset", {"target_email": email})

    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        users_list = db_data.get("users", [])
        for user in users_list:
            if user.get('email', '').strip().lower() == email:
                user['password'] = new_hash
                save_local_json(USER_DB_FILE, db_data)
                return

def get_all_users():
    if DB_TYPE == 'supabase':
        try:
            response = DB_CLIENT.table('user_roles').select("name, email, region, roles(name)").execute()
            users_map = {}
            for r in response.data or []:
                email = str(r.get("email") or "").strip().lower()
                if not email:
                    continue
                entry = users_map.setdefault(email, {
                    "name": r.get("name"),
                    "email": email,
                    "roles": set(),
                    "region": r.get("region")
                })
                role_name = (r.get("roles") or {}).get("name")
                if role_name:
                    entry["roles"].add(role_name)
                row_name = str(r.get("name") or "").strip()
                row_region = str(r.get("region") or "").strip()
                if row_name and not entry.get("name"):
                    entry["name"] = row_name
                if row_region.startswith(FUNDER_SCOPE_PREFIX):
                    entry["region"] = row_region
                elif row_region and not entry.get("region"):
                    entry["region"] = row_region
            rows = []
            for entry in users_map.values():
                region_value = entry.get("region")
                if "Funder" in entry["roles"]:
                    region_value = _decode_funder_scope(region_value) or region_value
                rows.append({
                    "name": entry.get("name"),
                    "email": entry.get("email"),
                    "role": ", ".join(sorted(entry["roles"])),
                    "region": region_value
                })
            return rows
        except:
            return []
        else:
            db_data = load_local_json(USER_DB_FILE, {"users": []})
            out = []
            for u in db_data.get("users", []):
                row = {k: v for k, v in u.items() if k != 'password'}
                if row.get("role") == "Funder":
                    row["region"] = _decode_funder_scope(row.get("region")) or row.get("region")
                out.append(row)
            return out

def get_user_roles(email):
    if not email:
        return []
    target = email.strip().lower()
    if DB_TYPE == 'supabase':
        try:
            resp = DB_CLIENT.table('user_roles').select("roles(name)").eq("email", target).execute()
            return [row.get("roles", {}).get("name") for row in resp.data or [] if row.get("roles", {}).get("name")]
        except Exception:
            return []
    else:
        db_data = load_local_json(USER_DB_FILE, {"users": []})
        for user in db_data.get("users", []):
            if str(user.get('email', '')).strip().lower() == target:
                roles = user.get("roles")
                if isinstance(roles, list) and roles:
                    return roles
                role = user.get("role")
                return [role] if role else []
        return []

# --- CASE STUDIES (CRUD) ---

def add_case_study(title, content, region, study_date=None):
    if study_date is None:
        dt = datetime.now()
    elif isinstance(study_date, datetime):
        dt = study_date
    else:
        dt = datetime.combine(study_date, datetime.min.time())
    date_added = dt.strftime("%Y-%m-%d %H:%M:%S")
    if DB_TYPE == 'supabase':
        DB_CLIENT.table('case_studies').insert({
            "title": title,
            "content": content,
            "region": region,
            "date_added": date_added
        }).execute()
    else:
        studies = load_local_json(CASE_STUDIES_FILE, [])
        studies.append({
            "title": title,
            "content": content,
            "region": region,
            "date_added": date_added
        })
        save_local_json(CASE_STUDIES_FILE, studies)
    try:
        get_case_studies.clear()
    except Exception:
        pass

@st.cache_data(show_spinner=False, ttl=120)
def get_case_studies(region_filter=None, start_date=None, end_date=None):
    if DB_TYPE == 'supabase':
        try:
            query = DB_CLIENT.table('case_studies').select("*")
            # If region is global (admin view), we might fetch all, but usually we filter by dash region
            # If the user's view region is not Global, we filter
            if region_filter and region_filter != "Global":
                query = query.eq('region', region_filter)
            if start_date:
                query = query.gte('date_added', start_date.strftime("%Y-%m-%d %H:%M:%S"))
            if end_date:
                query = query.lte('date_added', end_date.strftime("%Y-%m-%d %H:%M:%S"))
            
            response = query.execute()
            return response.data
        except:
            return []
    else:
        all_studies = load_local_json(CASE_STUDIES_FILE, [])
        if region_filter and region_filter != "Global":
            all_studies = [s for s in all_studies if s.get('region') == region_filter]
        if start_date or end_date:
            def _in_range(s):
                try:
                    dt = datetime.strptime(s.get('date_added', ''), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return False
                if start_date and dt < start_date:
                    return False
                if end_date and dt > end_date:
                    return False
                return True
            all_studies = [s for s in all_studies if _in_range(s)]
        return all_studies

# --- BEACON CRM INTEGRATION (LIVE) ---

def compute_kpis(region, people, organisations, events, payments, grants, event_attendee_records=None):
    if event_attendee_records is None:
        event_attendee_records = {}
    # 2. Filter Helpers
    def get_region_tags(record):
        return _to_list(record.get('c_region'))

    def is_in_region(record):
        if region == "Global":
            return True
        tags = get_region_tags(record)
        if not tags and record.get("region"):
            tags = _to_list(record.get("region"))
        return any(region.lower() in str(t).lower() for t in tags)

    # 3. Process People (Governance)
    region_people = [p for p in people if is_in_region(p)]
    
    # Fuzzy match for volunteers
    volunteers = []
    for p in region_people:
        p_types = [str(t).lower() for t in _to_list(p.get('type'))]
        if any('volunteer' in t for t in p_types):
            volunteers.append(p)

    steering_volunteers = []
    for v in volunteers:
        # Check if they are part of a steering group (often a specific type or tag)
        v_types = [str(t).lower() for t in _to_list(v.get('type'))]
        if any('steering' in t or 'committee' in t for t in v_types):
            steering_volunteers.append(v)
            
    # Proxy: If no specific "steering" tag found, fallback to total or mock logic
    steering_group_proxy = len(steering_volunteers) if steering_volunteers else len(volunteers)

    # 4. Process Organisations (Partnerships)
    region_orgs = [o for o in organisations if is_in_region(o)]
    all_orgs = list(organisations or [])
    org_id_to_region = {o.get('id'): True for o in region_orgs if o.get('id') is not None}
    
    lsp_counts = {}
    ldp_counts = {}
    corporate_orgs = []
    
    for org in region_orgs:
        org_type = str(org.get('type') or "").strip()
        if not org_type:
            continue
        
        # Determine strategic vs delivery
        if any(x in org_type.lower() for x in ["university", "trust", "political", "parliamentary", "media", "nhs", "prescriber"]):
            lsp_counts[org_type] = lsp_counts.get(org_type, 0) + 1
        else:
            ldp_counts[org_type] = ldp_counts.get(org_type, 0) + 1
            
    for org in all_orgs:
        org_type = str(org.get('type') or "").strip().lower()
        if "business" in org_type or "corporate" in org_type:
            corporate_orgs.append(org)

    corporate_count = len(corporate_orgs)

    # 5. Process Income
    global_grants = []
    for g in grants:
        org_link = g.get('organization')
        linked_id = None
        if isinstance(org_link, dict): linked_id = org_link.get('id')
        elif isinstance(org_link, str): linked_id = org_link
        
        if linked_id and linked_id in org_id_to_region:
            global_grants.append(g)
        elif region == "Global":
            global_grants.append(g)

    if region != "Global":
        global_grants = list(grants or [])
            
    # Fuzzy match for grant stages
    bids_submitted = sum(1 for g in global_grants if any(x in str(g.get('stage')).lower() for x in ['submitted', 'review', 'pending']))
    funds_raised_grants = sum(_coerce_money(g.get('amount')) for g in global_grants if str(g.get('stage')).lower() == 'won')
    
    def _payment_in_region(payment):
        if region == "Global":
            return True
        if is_in_region(payment):
            return True
        return False

    global_payments = [p for p in payments if _payment_in_region(p)]
    if region != "Global":
        global_payments = list(payments or [])
    total_payments = sum(_coerce_money(p.get('amount')) for p in global_payments)
    
    total_funds = funds_raised_grants + total_payments

    # 6. Process Delivery (Events)
    region_events = [e for e in events if is_in_region(e)]

    def _to_int(value):
        if value is None:
            return 0
        s = str(value).strip().replace(",", "")
        if not s:
            return 0
        try:
            return int(float(s))
        except ValueError:
            return 0

    def _event_type(event_row):
        for key in ("type", "Type", "Event type", "Activity type", "Category"):
            val = event_row.get(key)
            if val is not None and str(val).strip():
                return str(val).lower()
        return ""

    def _event_attendees(event_row):
        for key in (
            "number_of_attendees",
            "Number of attendees",
            "Attendees",
            "Participants",
            "Total participants",
            "Participant count",
            "Number attending",
        ):
            val = event_row.get(key)
            if val is not None and str(val).strip():
                if isinstance(val, list):
                    return len(val)
                if isinstance(val, dict):
                    for count_key in ("count", "total", "value", "participants", "attendees"):
                        if val.get(count_key) is not None and str(val.get(count_key)).strip():
                            return _to_int(val.get(count_key))
                return _to_int(val)
        return 0

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
    for person_row in people:
        pid = person_row.get("id")
        if pid is None:
            continue
        p_name = _get_row_value(person_row, "name", "full_name", "Display Name", "email") or pid
        people_name_by_id[_id_key(pid)] = str(p_name).strip()

    def _extract_participant_refs(event_row):
        participant_keys = (
            "participant_list",
            "participants_list",
            "participants",
            "attendees",
            "attendee_list",
            "attendees_list",
            "people",
            "participant_names",
            "attendee_names",
            "contacts",
            "relationships",
        )
        found_names = []
        found_ids = []
        seen_names = set()
        seen_ids = set()
        context_tokens = ("participant", "attendee", "people", "contact", "person", "member")
        id_keys = ("id", "person_id", "contact_id", "participant_id", "attendee_id")

        def _add_name(value):
            candidate = str(value).strip()
            if not candidate:
                return
            key = candidate.lower()
            if key in seen_names:
                return
            seen_names.add(key)
            found_names.append(candidate)

        def _add_id(value):
            candidate = str(value).strip()
            if not candidate:
                return
            if candidate in seen_ids:
                return
            seen_ids.add(candidate)
            found_ids.append(candidate)

        def _looks_like_context(path):
            path_l = str(path).lower()
            return any(t in path_l for t in context_tokens)

        def _walk(value, path=""):
            if value is None:
                return
            if isinstance(value, dict):
                local_name = value.get("name") or value.get("full_name") or value.get("display_name")
                if local_name:
                    _add_name(local_name)
                if value.get("email"):
                    _add_name(value.get("email"))
                for id_key in id_keys:
                    if value.get(id_key) is not None and _looks_like_context(path):
                        _add_id(value.get(id_key))
                for k, v in value.items():
                    next_path = f"{path}.{k}" if path else str(k)
                    _walk(v, next_path)
                return
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    next_path = f"{path}[{idx}]"
                    _walk(item, next_path)
                return
            if isinstance(value, str):
                if _looks_like_context(path):
                    raw = [x.strip() for x in value.replace("\n", ",").replace(";", ",").split(",")]
                    for token in raw:
                        if token:
                            _add_name(token)

        for key in participant_keys:
            val = event_row.get(key)
            if val is None:
                continue
            _walk(val, key)

        if found_ids:
            for pid in found_ids:
                mapped_name = people_name_by_id.get(_id_key(pid))
                if mapped_name:
                    _add_name(mapped_name)
        return found_names, found_ids

    def _extract_linked_event_ids_from_person(person_row):
        linked_ids = set()
        context_tokens = ("event", "attend", "session", "activity", "retreat", "walk", "booking")
        id_keys = ("id", "event_id", "activity_id", "session_id")

        def _in_context(path):
            p = str(path).lower()
            return any(t in p for t in context_tokens)

        def _walk(value, path=""):
            if value is None:
                return
            if isinstance(value, dict):
                for k, v in value.items():
                    next_path = f"{path}.{k}" if path else str(k)
                    if k in id_keys and _in_context(path):
                        if v is not None and str(v).strip():
                            linked_ids.add(str(v).strip())
                    _walk(v, next_path)
                return
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    _walk(item, f"{path}[{idx}]")
                return
            if isinstance(value, (int, float)):
                if _in_context(path):
                    linked_ids.add(str(int(value)))
                return
            if isinstance(value, str):
                if _in_context(path):
                    parts = [x.strip() for x in value.replace("\n", ",").replace(";", ",").split(",")]
                    for part in parts:
                        if part:
                            linked_ids.add(part)

        _walk(person_row)
        return linked_ids
    
    walks_delivered = 0
    participants = 0
    delivery_event_count = 0
    delivery_events = []
    event_type_counts = {}
    people_by_event_id = {}
    for p in region_people:
        p_name = _get_row_value(p, "name", "full_name", "Display Name", "email") or p.get("id")
        if not p_name:
            continue
        linked_event_ids = _extract_linked_event_ids_from_person(p)
        for linked_id in linked_event_ids:
            key = _id_key(linked_id)
            if key not in people_by_event_id:
                people_by_event_id[key] = []
            if str(p_name) not in people_by_event_id[key]:
                people_by_event_id[key].append(str(p_name))
    for e in region_events:
        e_type = _event_type(e)
        if any(x in e_type for x in ['walk', 'retreat', 'delivery', 'session', 'hike', 'trek']):
            walks_delivered += 1
            delivery_event_count += 1
            participant_list, participant_ids = _extract_participant_refs(e)
            event_id = str(e.get("id")) if e.get("id") is not None else ""
            linked_people = people_by_event_id.get(_id_key(event_id), [])
            if linked_people:
                seen_names = set(str(x).strip().lower() for x in participant_list)
                for lp in linked_people:
                    lp_norm = str(lp).strip().lower()
                    if lp_norm and lp_norm not in seen_names:
                        participant_list.append(lp)
                        seen_names.add(lp_norm)
            event_participants = max(_event_attendees(e), len(participant_list), len(participant_ids))
            participants += event_participants
            event_type_label = e_type.title() if e_type else "Unknown Event Type"
            event_type_counts[event_type_label] = event_type_counts.get(event_type_label, 0) + 1
            delivery_events.append({
                "id": e.get("id"),
                "type": e_type,
                "participants": event_participants,
                "date": e.get("start_date") or e.get("date") or e.get("created_at"),
                "name": _get_row_value(e, "name", "title", "Event name", "Description") or e.get("id"),
                "region": ", ".join(_to_list(e.get("c_region"))),
                "participant_list": participant_list,
                "participant_ids": participant_ids,
                "attendee_records": event_attendee_records.get(str(event_id)) or event_attendee_records.get(_id_key(event_id)) or [],
                "raw_event": e,
            })

    # Fallback: if event labels are inconsistent, treat all region events as delivered.
    if walks_delivered == 0 and region_events:
        walks_delivered = len(region_events)
        participants = sum(_event_attendees(e) for e in region_events)

    attendee_gender_demographics = {}
    seen_attendees = set()
    for event in region_events:
        event_id = str(event.get("id") or "")
        attendee_rows = event_attendee_records.get(event_id) or event_attendee_records.get(_id_key(event_id)) or []
        for attendee in attendee_rows:
            if not isinstance(attendee, dict):
                continue
            attendee_key = str(attendee.get("id") or f"{event_id}:{attendee.get('person_id') or attendee.get('name') or attendee.get('email') or ''}").strip()
            if attendee_key in seen_attendees:
                continue
            seen_attendees.add(attendee_key)
            label = _normalize_gender(_get_row_value(attendee, "c_gender", "Gender", "gender"))
            attendee_gender_demographics[label] = attendee_gender_demographics.get(label, 0) + 1

    # Delivery demographics from currently available fields.
    # Priority 1: event attendee gender
    # Priority 2: people type tags
    # Priority 3: event type split
    demographic_keyword_map = {
        "Men": ["men", "male"],
        "Women": ["women", "female"],
        "Young Adults": ["young adult", "young people", "youth"],
        "Carers": ["carer", "caregiver"],
        "Veterans": ["veteran"],
        "Ethnic Minorities": ["ethnic minority", "minority ethnic", "bame", "global majority"],
        "Parents": ["parent", "mum", "dad"],
    }
    people_tag_demographics = {}
    for p in region_people:
        person_tags = [str(t).lower() for t in _to_list(p.get("type"))]
        if not person_tags:
            continue
        person_text = " | ".join(person_tags)
        for label, keywords in demographic_keyword_map.items():
            if any(k in person_text for k in keywords):
                people_tag_demographics[label] = people_tag_demographics.get(label, 0) + 1

    if attendee_gender_demographics:
        delivery_demographics = attendee_gender_demographics
        delivery_demographics_source = "event_attendee_gender"
    elif people_tag_demographics:
        delivery_demographics = people_tag_demographics
        delivery_demographics_source = "people_type_tags"
    elif event_type_counts:
        delivery_demographics = event_type_counts
        delivery_demographics_source = "event_type_split"
    else:
        delivery_demographics = {"General": participants if participants > 0 else 1}
        delivery_demographics_source = "fallback"

    return {
        "region": region,
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "governance": {
            "steering_group_active": steering_group_proxy > 0, 
            "steering_members": steering_group_proxy,
            "volunteers_new": len(volunteers) 
        },
        "partnerships": {
            "LSP": lsp_counts if lsp_counts else {"None": 0},
            "LDP": ldp_counts if ldp_counts else {"None": 0},
            "active_referrals": len(region_orgs),
            "networks_sat_on": 0 
        },
        "delivery": {
            "walks_delivered": walks_delivered, 
            "participants": participants,
            "bursary_participants": 0, 
            "wellbeing_change_score": 0,
            "demographics": delivery_demographics,
            "demographics_source": delivery_demographics_source,
        },
        "income": {
            "bids_submitted": bids_submitted,
            "total_funds_raised": total_funds,
            "corporate_partners": corporate_count,
            "in_kind_value": 0 
        },
        "comms": {
            "press_releases": 0,
            "media_coverage": 0,
            "newsletters_sent": 0,
            "open_rate": 0
        },
        "_debug": {
            "region_people": len(region_people),
            "volunteers": len(volunteers),
            "steering_volunteers": len(steering_volunteers),
            "region_events": len(region_events),
            "walk_events": walks_delivered,
            "participants": participants,
            "region_grants": len(global_grants),
            "bids_submitted": bids_submitted,
            "delivery_events_tagged": delivery_event_count
        },
        "_raw_income": {
            "payments": global_payments,
            "grants": global_grants
        },
        "_raw_kpi": {
            "region_people": region_people,
            "volunteers": volunteers,
            "steering_volunteers": steering_volunteers,
            "region_orgs": region_orgs,
            "corporate_orgs": corporate_orgs,
            "region_events": region_events,
            "delivery_events": delivery_events,
            "region_grants": global_grants,
            "region_payments": global_payments,
            "event_attendee_records": event_attendee_records,
        }
    }


def get_mock_data(region):
    return {
        "region": region,
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "governance": {
            "steering_group_active": True, 
            "steering_members": 8,
            "volunteers_new": 12
        },
        "partnerships": {
            "LSP": {"Charity": 5, "Health": 3, "Social Prescribing": 2, "Corporate": 1, "University": 1, "Statutory": 4},
            "LDP": {"Charity": 10, "Health": 6, "Social Prescribing": 8, "Corporate": 2, "University": 0, "Statutory": 2},
            "active_referrals": 15,
            "networks_sat_on": 4
        },
        "delivery": {
            "walks_delivered": 45,
            "participants": 320,
            "bursary_participants": 15,
            "wellbeing_change_score": 1.4,
            "demographics": {"Men": 20, "Young Adults": 30, "Carers": 15, "Ethnic Minorities": 10, "General": 25}
        },
        "income": {
            "bids_submitted": 5,
            "total_funds_raised": 25000,
            "corporate_partners": 2,
            "in_kind_value": 5000
        },
        "comms": {
            "press_releases": 3,
            "media_coverage": 5,
            "newsletters_sent": 12,
            "open_rate": 42.5
        }
    }

@st.cache_data(show_spinner=False, ttl=300)
def _fetch_supabase_rows(table, columns, date_field=None, start_iso=None, end_iso=None, batch_size=1000, max_retries=4):
    if DB_TYPE != 'supabase':
        return []
    rows = []
    offset = 0
    while True:
        attempt = 0
        while True:
            try:
                q = DB_CLIENT.table(table).select(columns)
                if date_field and start_iso:
                    q = q.gte(date_field, start_iso)
                if date_field and end_iso:
                    q = q.lte(date_field, end_iso)
                chunk = q.range(offset, offset + batch_size - 1).execute().data or []
                break
            except Exception as e:
                msg = str(e).lower()
                retriable = any(
                    token in msg
                    for token in (
                        "502",
                        "bad gateway",
                        "json could not be generated",
                        "timeout",
                        "timed out",
                        "connection reset",
                        "temporarily unavailable",
                    )
                )
                if retriable and attempt < max_retries:
                    time.sleep(min(8, 1.5 * (2 ** attempt)))
                    attempt += 1
                    continue
                raise
        rows.extend(chunk)
        if len(chunk) < batch_size:
            break
        offset += batch_size
    return rows

def _rows_to_payloads(rows, date_field=None, region_field=None):
    payloads = []
    for row in rows:
        payload = row.get("payload") or {}
        if date_field and row.get(date_field) and not payload.get(date_field):
            payload[date_field] = row.get(date_field)
        if region_field and row.get(region_field) and not payload.get("c_region"):
            payload["c_region"] = [row.get(region_field)]
        payloads.append(payload)
    return payloads

def _build_event_attendee_records(attendee_rows):
    event_attendee_records = {}
    for row in attendee_rows:
        payload = row.get("payload") or {}
        event_id = payload.get("event_id") or row.get("event_id")
        person_id = payload.get("person_id") or row.get("person_id")
        if person_id and not payload.get("person_id"):
            payload["person_id"] = person_id
        if event_id and not payload.get("event_id"):
            payload["event_id"] = event_id
        if row.get("created_at") and not payload.get("created_at"):
            payload["created_at"] = row.get("created_at")
        if not event_id:
            continue
        event_attendee_records.setdefault(str(event_id), []).append(payload)
        norm_event_id = _entity_ref_key(event_id)
        if norm_event_id and norm_event_id != str(event_id):
            event_attendee_records.setdefault(norm_event_id, []).append(payload)
    return event_attendee_records

@st.cache_data(show_spinner=False, ttl=300)
def fetch_supabase_data(region, start_date=None, end_date=None):
    if DB_TYPE != 'supabase':
        return None
    start_iso = start_date.isoformat() if start_date else None
    end_iso = end_date.isoformat() if end_date else None

    fetch_errors = []
    def _safe_fetch(table, columns, date_field):
        try:
            return _fetch_supabase_rows(table, columns, date_field, start_iso, end_iso)
        except Exception as e:
            fetch_errors.append((table, str(e)))
            return []

    people_rows = _safe_fetch("beacon_people", "payload, created_at", "created_at")
    org_rows = _safe_fetch("beacon_organisations", "payload, created_at", "created_at")
    # For events, we need the region column as well to ensure robust mapping.
    event_rows = _safe_fetch("beacon_events", "payload, start_date, region", "start_date")
    attendee_rows = _safe_fetch("beacon_event_attendees", "payload, event_id, person_id, created_at", "created_at")
    payment_rows = _safe_fetch("beacon_payments", "payload, payment_date", "payment_date")
    grant_rows = _safe_fetch("beacon_grants", "payload, close_date", "close_date")

    if fetch_errors:
        failed_tables = ", ".join(t for t, _ in fetch_errors)
        st.warning(f"Temporary Supabase issue while loading: {failed_tables}. Showing available data.")
        # If everything failed, still show explicit error and return no data.
        if not any([people_rows, org_rows, event_rows, attendee_rows, payment_rows, grant_rows]):
            first_error = fetch_errors[0][1] if fetch_errors else "Unknown error"
            st.error(f"Supabase Data Error: {first_error}")
            return None

    people = _rows_to_payloads(people_rows, date_field="created_at")
    organisations = _rows_to_payloads(org_rows, date_field="created_at")
    events = _rows_to_payloads(event_rows, date_field="start_date", region_field="region")
    payments = _rows_to_payloads(payment_rows, date_field="payment_date")
    grants = _rows_to_payloads(grant_rows, date_field="close_date")
    event_attendee_records = _build_event_attendee_records(attendee_rows)

    result = compute_kpis(region, people, organisations, events, payments, grants, event_attendee_records=event_attendee_records)
    result["_source"] = "supabase"
    return result

@st.cache_data(show_spinner=False, ttl=300)
def fetch_ml_dashboard_data(region, start_date=None, end_date=None):
    if DB_TYPE != 'supabase':
        return None
    start_iso = start_date.isoformat() if start_date else None
    end_iso = end_date.isoformat() if end_date else None
    fetch_errors = []

    def _safe_fetch(table, columns, date_field):
        try:
            return _fetch_supabase_rows(table, columns, date_field, start_iso, end_iso)
        except Exception as e:
            fetch_errors.append((table, str(e)))
            return []

    people_rows = _safe_fetch("beacon_people", "payload, created_at", "created_at")
    event_rows = _safe_fetch("beacon_events", "payload, start_date, region", "start_date")
    attendee_rows = _safe_fetch("beacon_event_attendees", "payload, event_id, person_id, created_at", "created_at")

    if fetch_errors and not any([people_rows, event_rows, attendee_rows]):
        first_error = fetch_errors[0][1] if fetch_errors else "Unknown error"
        st.error(f"Supabase Data Error: {first_error}")
        return None

    people = _rows_to_payloads(people_rows, date_field="created_at")
    events = _rows_to_payloads(event_rows, date_field="start_date", region_field="region")
    event_attendee_records = _build_event_attendee_records(attendee_rows)
    result = compute_kpis(region, people, [], events, [], [], event_attendee_records=event_attendee_records)
    result["_source"] = "supabase_ml"
    return result

@st.cache_data(show_spinner=False, ttl=300)
def fetch_funder_dashboard_data(region, start_date=None, end_date=None, include_summary=True):
    if DB_TYPE != 'supabase':
        return None
    start_iso = start_date.isoformat() if start_date else None
    end_iso = end_date.isoformat() if end_date else None
    fetch_errors = []

    def _safe_fetch(table, columns, date_field):
        try:
            return _fetch_supabase_rows(table, columns, date_field, start_iso, end_iso)
        except Exception as e:
            fetch_errors.append((table, str(e)))
            return []

    org_rows = _safe_fetch("beacon_organisations", "payload, created_at", "created_at")
    payment_rows = _safe_fetch("beacon_payments", "payload, payment_date", "payment_date")
    grant_rows = _safe_fetch("beacon_grants", "payload, close_date", "close_date")
    people_rows = _safe_fetch("beacon_people", "payload, created_at", "created_at") if include_summary else []
    event_rows = _safe_fetch("beacon_events", "payload, start_date, region", "start_date") if include_summary else []

    if fetch_errors and not any([org_rows, payment_rows, grant_rows, people_rows, event_rows]):
        first_error = fetch_errors[0][1] if fetch_errors else "Unknown error"
        st.error(f"Supabase Data Error: {first_error}")
        return None

    people = _rows_to_payloads(people_rows, date_field="created_at")
    organisations = _rows_to_payloads(org_rows, date_field="created_at")
    events = _rows_to_payloads(event_rows, date_field="start_date", region_field="region")
    payments = _rows_to_payloads(payment_rows, date_field="payment_date")
    grants = _rows_to_payloads(grant_rows, date_field="close_date")
    result = compute_kpis(region, people, organisations, events, payments, grants, event_attendee_records={})
    result["_source"] = "supabase_funder"
    return result

@st.cache_data(show_spinner=False, ttl=300)
def fetch_kpi_section_data(section, region, start_date=None, end_date=None):
    if DB_TYPE != 'supabase':
        return None
    start_iso = start_date.isoformat() if start_date else None
    end_iso = end_date.isoformat() if end_date else None
    fetch_errors = []

    def _safe_fetch(table, columns, date_field):
        try:
            return _fetch_supabase_rows(table, columns, date_field, start_iso, end_iso)
        except Exception as e:
            fetch_errors.append((table, str(e)))
            return []

    people_rows = []
    org_rows = []
    event_rows = []
    attendee_rows = []
    payment_rows = []
    grant_rows = []

    if section in {"Governance", "Delivery"}:
        people_rows = _safe_fetch("beacon_people", "payload, created_at", "created_at")
    if section in {"Partnerships", "Income"}:
        org_rows = _safe_fetch("beacon_organisations", "payload, created_at", "created_at")
    if section == "Delivery":
        event_rows = _safe_fetch("beacon_events", "payload, start_date, region", "start_date")
        attendee_rows = _safe_fetch("beacon_event_attendees", "payload, event_id, person_id, created_at", "created_at")
    if section == "Income":
        payment_rows = _safe_fetch("beacon_payments", "payload, payment_date", "payment_date")
        grant_rows = _safe_fetch("beacon_grants", "payload, close_date", "close_date")

    if fetch_errors and not any([people_rows, org_rows, event_rows, attendee_rows, payment_rows, grant_rows]):
        first_error = fetch_errors[0][1] if fetch_errors else "Unknown error"
        st.error(f"Supabase Data Error: {first_error}")
        return None

    people = _rows_to_payloads(people_rows, date_field="created_at")
    organisations = _rows_to_payloads(org_rows, date_field="created_at")
    events = _rows_to_payloads(event_rows, date_field="start_date", region_field="region")
    payments = _rows_to_payloads(payment_rows, date_field="payment_date")
    grants = _rows_to_payloads(grant_rows, date_field="close_date")
    event_attendee_records = _build_event_attendee_records(attendee_rows)
    result = compute_kpis(region, people, organisations, events, payments, grants, event_attendee_records=event_attendee_records)
    result["_source"] = "supabase_kpi_section"
    result["_section"] = section
    return result

@st.cache_data(show_spinner=False, ttl=120)
def get_last_refresh_timestamp():
    if DB_TYPE != 'supabase':
        return None
    try:
        tables = [
            "beacon_people",
            "beacon_organisations",
            "beacon_events",
            "beacon_event_attendees",
            "beacon_payments",
            "beacon_grants",
        ]
        latest = None
        for t in tables:
            resp = DB_CLIENT.table(t).select("updated_at").order("updated_at", desc=True).limit(1).execute()
            if resp.data:
                ts = resp.data[0].get("updated_at")
                if ts:
                    # Parse ISO timestamp
                    try:
                        if ts.endswith("Z"):
                            ts = ts[:-1] + "+00:00"
                        dt = datetime.fromisoformat(ts)
                    except Exception:
                        dt = None
                    if dt and (latest is None or dt > latest):
                        latest = dt
        return latest
    except Exception:
        return None

def _set_sync_job_state(job_id, **updates):
    with SYNC_JOBS_LOCK:
        state = SYNC_JOBS.get(job_id) or {}
        state.update(updates)
        SYNC_JOBS[job_id] = state
        return state

def _get_sync_job_state(job_id):
    with SYNC_JOBS_LOCK:
        state = SYNC_JOBS.get(job_id)
        return dict(state) if state else None

def _find_recent_sync_job_id(user_email=None, max_age_seconds=7200):
    now_ts = time.time()
    with SYNC_JOBS_LOCK:
        candidates = []
        for job_id, state in SYNC_JOBS.items():
            created_at = state.get("created_at") or state.get("started_at") or now_ts
            if (now_ts - created_at) > max_age_seconds:
                continue
            if user_email and state.get("user_email") not in (user_email, "System"):
                continue
            candidates.append((created_at, job_id))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]

def _insert_system_audit(admin_client, action, details, user_email="System", region="Global"):
    try:
        admin_client.table("audit_logs").insert({
            "user_email": user_email or "System",
            "action": action,
            "details": details or {},
            "region": region or "Global",
        }).execute()
    except Exception as e:
        print(f"Audit Log Error: {e}")

def _log_manual_sync_progress(admin_client, user_email, region, job_id, progress, message):
    _insert_system_audit(
        admin_client,
        "Data Sync Progress",
        {
            "source": "beacon_api",
            "trigger": "manual_ui",
            "job_id": job_id,
            "progress": int(max(0, min(100, progress))),
            "message": message,
        },
        user_email=user_email,
        region=region,
    )

def get_latest_manual_sync_state(user_email=None, lookback_rows=300):
    if DB_TYPE != 'supabase':
        return None
    try:
        resp = (
            DB_CLIENT.table("audit_logs")
            .select("created_at, user_email, action, details, region")
            .in_("action", ["Data Sync Started", "Data Sync Progress", "Data Sync Completed", "Data Sync Failed", "Data Sync Cancelled", "Data Sync Cleared"])
            .order("created_at", desc=True)
            .limit(lookback_rows)
            .execute()
        )
        rows = resp.data or []
    except Exception:
        return None

    filtered = []
    for r in rows:
        details = r.get("details") or {}
        if details.get("source") != "beacon_api" or details.get("trigger") != "manual_ui":
            continue
        if user_email and r.get("user_email") not in (user_email, "System"):
            continue
        if not details.get("job_id"):
            continue
        filtered.append(r)
    if not filtered:
        return None

    latest = filtered[0]
    latest_details = latest.get("details") or {}
    job_id = latest_details.get("job_id")
    job_rows = [r for r in filtered if (r.get("details") or {}).get("job_id") == job_id]
    if not job_rows:
        return None

    start_row = next((r for r in reversed(job_rows) if r.get("action") == "Data Sync Started"), None)
    end_row = next((r for r in job_rows if r.get("action") in ("Data Sync Completed", "Data Sync Failed", "Data Sync Cancelled", "Data Sync Cleared")), None)
    progress_row = next((r for r in job_rows if r.get("action") == "Data Sync Progress"), None)

    status = "running"
    if end_row:
        if end_row.get("action") == "Data Sync Completed":
            status = "completed"
        elif end_row.get("action") in ("Data Sync Cancelled", "Data Sync Cleared"):
            status = "cancelled"
        else:
            status = "failed"

    if status in ("completed", "failed", "cancelled"):
        progress = 100
    elif progress_row:
        progress = int((progress_row.get("details") or {}).get("progress") or 0)
    else:
        progress = 0

    message = "Starting Beacon API sync..."
    if progress_row:
        message = (progress_row.get("details") or {}).get("message") or message
    if status == "completed":
        message = "Beacon API sync complete."
    if status == "failed":
        message = "Beacon API sync failed."
    if status == "cancelled":
        if end_row and end_row.get("action") == "Data Sync Cleared":
            message = "Manual sync cleared by user."
        else:
            message = "Beacon API sync cancelled."

    state = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "user_email": latest.get("user_email"),
        "region": latest.get("region"),
    }

    if start_row and start_row.get("created_at"):
        ts = pd.to_datetime(start_row.get("created_at"), utc=True, errors="coerce")
        if not pd.isna(ts):
            state["started_at"] = ts.timestamp()
    if end_row and end_row.get("created_at"):
        ts = pd.to_datetime(end_row.get("created_at"), utc=True, errors="coerce")
        if not pd.isna(ts):
            state["ended_at"] = ts.timestamp()
    if end_row:
        details = end_row.get("details") or {}
        if status == "completed":
            state["result"] = details
        else:
            state["error"] = details.get("error")

    return state

def _run_manual_sync_job(job_id):
    state = _get_sync_job_state(job_id) or {}
    user_email = state.get("user_email", "System")
    region = state.get("region", "Global")
    if state.get("status") == "cancelled" or state.get("cancel_requested"):
        _set_sync_job_state(
            job_id,
            status="cancelled",
            progress=100,
            message="Manual sync cancelled before start.",
            ended_at=time.time(),
        )
        return
    started_at = time.time()
    _set_sync_job_state(
        job_id,
        status="running",
        progress=0,
        message="Starting Beacon API sync...",
        started_at=started_at,
    )

    admin_client = get_admin_client()
    if not admin_client:
        _set_sync_job_state(
            job_id,
            status="failed",
            progress=100,
            message="Admin client not available.",
            ended_at=time.time(),
            error="Admin client not available.",
        )
        return

    _insert_system_audit(
        admin_client,
        "Data Sync Started",
        {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
        user_email=user_email,
        region=region,
    )

    def _is_cancel_requested():
        current_state = _get_sync_job_state(job_id) or {}
        return bool(current_state.get("cancel_requested"))

    last_logged_progress = {"value": -1}
    def _sync_job_progress(progress, message):
        pct = int(max(0, min(100, progress)))
        if _is_cancel_requested():
            _set_sync_job_state(job_id, message="Cancellation requested...")
            raise SyncCancelledError("Manual sync cancelled by user.")
        _set_sync_job_state(job_id, progress=pct, message=message)
        if pct >= last_logged_progress["value"] + 5 or pct in (0, 100):
            _log_manual_sync_progress(admin_client, user_email, region, job_id, pct, message)
            last_logged_progress["value"] = pct

    try:
        result = sync_beacon_api_to_supabase(
            admin_client,
            progress_callback=_sync_job_progress,
            should_cancel=_is_cancel_requested,
        )
        result["source"] = "beacon_api"
        result["trigger"] = "manual_ui"
        result["job_id"] = job_id
        _insert_system_audit(admin_client, "Data Sync Completed", result, user_email=user_email, region=region)
        _set_sync_job_state(
            job_id,
            status="completed",
            progress=100,
            message="Beacon API sync complete.",
            ended_at=time.time(),
            result=result,
        )
    except SyncCancelledError:
        _insert_system_audit(
            admin_client,
            "Data Sync Cancelled",
            {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
            user_email=user_email,
            region=region,
        )
        _set_sync_job_state(
            job_id,
            status="cancelled",
            progress=100,
            message="Manual sync cancelled.",
            ended_at=time.time(),
        )
    except Exception as e:
        _insert_system_audit(
            admin_client,
            "Data Sync Failed",
            {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id, "error": str(e)},
            user_email=user_email,
            region=region,
        )
        _set_sync_job_state(
            job_id,
            status="failed",
            progress=100,
            message="Beacon API sync failed.",
            ended_at=time.time(),
            error=str(e),
        )

def start_manual_sync_job(user_email, region):
    audit_state = get_latest_manual_sync_state(user_email=user_email)
    if audit_state and audit_state.get("status") == "running":
        return audit_state.get("job_id"), "A manual sync is already running. Showing its progress."

    with SYNC_JOBS_LOCK:
        for running_job_id, state in SYNC_JOBS.items():
            if state.get("status") == "running":
                return running_job_id, "A manual sync is already running. Showing its progress."
        job_id = uuid.uuid4().hex[:10]
        SYNC_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "Queued...",
            "created_at": time.time(),
            "user_email": user_email,
            "region": region,
        }
    SYNC_EXECUTOR.submit(_run_manual_sync_job, job_id)
    return job_id, None

def stop_manual_sync_job(job_id, user_email=None, region=None):
    if not job_id:
        return False, "No active manual sync job found."
    with SYNC_JOBS_LOCK:
        state = SYNC_JOBS.get(job_id)
        if not state:
            return False, "Manual sync job not found."
        status = state.get("status")
        if status in ("completed", "failed", "cancelled"):
            return False, f"Manual sync is already {status}."
        if status == "queued":
            state["status"] = "cancelled"
            state["progress"] = 100
            state["message"] = "Manual sync cancelled before start."
            state["ended_at"] = time.time()
            SYNC_JOBS[job_id] = state
        else:
            state["cancel_requested"] = True
            state["message"] = "Cancellation requested..."
            SYNC_JOBS[job_id] = state
    admin_client = get_admin_client()
    if admin_client:
        _insert_system_audit(
            admin_client,
            "Data Sync Cancellation Requested",
            {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
            user_email=user_email or st.session_state.get("email", "System"),
            region=region or st.session_state.get("region", "Global"),
        )
    return True, "Stop request sent. The sync will stop shortly."

def clear_manual_sync_job(job_id, user_email=None, region=None):
    if not job_id:
        return False, "No manual sync job selected."
    with SYNC_JOBS_LOCK:
        state = SYNC_JOBS.get(job_id)
        if state:
            state["status"] = "cancelled"
            state["progress"] = 100
            state["message"] = "Manual sync cleared by user."
            state["ended_at"] = time.time()
            SYNC_JOBS[job_id] = state
    st.session_state.pop("manual_sync_job_id", None)
    admin_client = get_admin_client()
    if admin_client:
        _insert_system_audit(
            admin_client,
            "Data Sync Cleared",
            {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
            user_email=user_email or st.session_state.get("email", "System"),
            region=region or st.session_state.get("region", "Global"),
        )
    return True, "Stuck sync state cleared."

def render_manual_sync_status():
    job_id = st.session_state.get("manual_sync_job_id")
    if not job_id:
        recovered = _find_recent_sync_job_id(st.session_state.get("email"))
        if recovered:
            st.session_state["manual_sync_job_id"] = recovered
            job_id = recovered
        else:
            audit_state = get_latest_manual_sync_state(st.session_state.get("email"))
            if not audit_state:
                return None, False
            st.session_state["manual_sync_job_id"] = audit_state.get("job_id")
            job_id = audit_state.get("job_id")

    state = _get_sync_job_state(job_id)
    if not state:
        recovered = _find_recent_sync_job_id(st.session_state.get("email"))
        if recovered and recovered != job_id:
            st.session_state["manual_sync_job_id"] = recovered
            state = _get_sync_job_state(recovered)
        if not state:
            audit_state = get_latest_manual_sync_state(st.session_state.get("email"))
            if audit_state and audit_state.get("job_id") == job_id:
                state = audit_state
            elif audit_state:
                st.session_state["manual_sync_job_id"] = audit_state.get("job_id")
                state = audit_state
        if not state:
            return None, False

    # Auto-hide finished sync states from sidebar once handled.
    if state.get("status") in ("completed", "failed", "cancelled"):
        st.session_state.pop("manual_sync_job_id", None)
        return state, False

    status = state.get("status", "unknown")
    progress = int(state.get("progress", 0))
    message = state.get("message", "Working...")
    started_at = state.get("started_at")
    ended_at = state.get("ended_at")
    elapsed = None
    if started_at:
        elapsed = (ended_at or time.time()) - started_at

    st.sidebar.markdown("### Manual Sync Status")
    st.sidebar.progress(progress, text=message)
    toast_class = "sync-toast-running"
    if status == "completed":
        toast_class = "sync-toast-complete"
    elif status == "failed":
        toast_class = "sync-toast-failed"
    elif status == "cancelled":
        toast_class = "sync-toast-failed"
    st.sidebar.markdown(
        f"<div class='sync-toast {toast_class}'>Sync {status.title()} | {progress}%<br>{message}</div>",
        unsafe_allow_html=True,
    )
    if status == "running":
        st.sidebar.info(f"Status: Running ({progress}%)")
    elif status == "queued":
        st.sidebar.info("Status: Queued")
    elif status == "completed":
        st.sidebar.success("Status: Completed")
    elif status == "failed":
        st.sidebar.error("Status: Failed")
    elif status == "cancelled":
        st.sidebar.warning("Status: Cancelled")
    else:
        st.sidebar.warning(f"Status: {status}")

    if elapsed is not None:
        st.sidebar.caption(f"Elapsed: {elapsed:.1f}s")
        if status in ("queued", "running") and progress > 3:
            remaining = max(0.0, elapsed * (100 - progress) / progress)
            st.sidebar.caption(f"ETA: {remaining:.1f}s")

    if status == "completed":
        result = state.get("result") or {}
        st.sidebar.caption(
            f"Updated P:{result.get('people', 0)} O:{result.get('organisations', 0)} "
            f"E:{result.get('events', 0)} Pay:{result.get('payments', 0)} G:{result.get('grants', 0)}"
        )
        cache_key = f"_manual_sync_cache_cleared_{job_id}"
        if not st.session_state.get(cache_key):
            st.cache_data.clear()
            st.session_state[cache_key] = True
    if status == "failed" and state.get("error"):
        st.sidebar.caption(f"Error: {state.get('error')}")

    return state, status in ("queued", "running")

def render_manual_sync_main_panel(sync_state):
    if not sync_state:
        return

    status = sync_state.get("status", "unknown")
    progress = int(sync_state.get("progress", 0))
    message = sync_state.get("message", "Working...")
    started_at = sync_state.get("started_at")
    ended_at = sync_state.get("ended_at")

    elapsed = None
    if started_at:
        elapsed = (ended_at or time.time()) - started_at

    st.markdown("**Manual Sync Progress**")
    st.progress(progress, text=f"{progress}% | {message}")
    if status == "running":
        st.info("Sync is running in the background. You can keep using the dashboard.")
    elif status == "queued":
        st.info("Sync is queued and will start shortly.")
    elif status == "completed":
        st.success("Sync completed.")
    elif status == "failed":
        st.error("Sync failed.")
    elif status == "cancelled":
        st.warning("Sync cancelled.")
    else:
        st.warning(f"Sync status: {status}")

    parts = []
    if elapsed is not None:
        parts.append(f"Elapsed: {elapsed:.1f}s")
    if status in ("queued", "running") and elapsed is not None and progress > 3:
        remaining = max(0.0, elapsed * (100 - progress) / progress)
        parts.append(f"ETA: {remaining:.1f}s")
    if parts:
        st.caption(" | ".join(parts))

    if status == "completed":
        result = sync_state.get("result") or {}
        st.caption(
            f"Updated: People {result.get('people', 0)}, Organisations {result.get('organisations', 0)}, "
            f"Events {result.get('events', 0)}, Payments {result.get('payments', 0)}, Grants {result.get('grants', 0)}"
        )
        st.caption(
            f"Durations: Total {result.get('total_duration_ms', 0) / 1000:.1f}s | "
            f"Fetch {result.get('fetch_duration_ms', 0) / 1000:.1f}s | "
            f"Transform {result.get('transform_duration_ms', 0) / 1000:.1f}s | "
            f"Upsert {result.get('upsert_duration_ms', 0) / 1000:.1f}s"
        )
    if status == "failed" and sync_state.get("error"):
        st.caption(f"Error details: {sync_state.get('error')}")

def clear_dashboard_data_except_users(admin_client, progress_callback=None):
    # Deliberately excludes user/auth tables (e.g. user_roles, roles, auth users).
    tables = [
        ("beacon_people", "id"),
        ("beacon_organisations", "id"),
        ("beacon_events", "id"),
        ("beacon_payments", "id"),
        ("beacon_grants", "id"),
        ("case_studies", "id"),
        ("audit_logs", "id"),
    ]
    deleted = {}
    errors = []

    total_tables = len(tables)
    if progress_callback:
        progress_callback(0, "Starting dashboard data reset...")

    for idx, (table, key) in enumerate(tables):
        if progress_callback:
            start_pct = int((idx / total_tables) * 100)
            progress_callback(start_pct, f"Clearing {table}...")
        table_deleted = 0
        while True:
            try:
                rows = admin_client.table(table).select(key).limit(500).execute().data or []
            except Exception as e:
                errors.append(f"{table}: {e}")
                break

            ids = [r.get(key) for r in rows if r.get(key) is not None]
            if not ids:
                break

            try:
                admin_client.table(table).delete().in_(key, ids).execute()
                table_deleted += len(ids)
            except Exception as e:
                errors.append(f"{table}: {e}")
                break

        deleted[table] = table_deleted
        if progress_callback:
            done_pct = int(((idx + 1) / total_tables) * 100)
            progress_callback(done_pct, f"Cleared {table}: {table_deleted} rows.")

    return deleted, errors

# --- UI COMPONENTS ---

ROLE_PRIORITY = ["Admin", "Manager", "ML", "RPL", "Funder"]

def _primary_role_from_list(roles):
    if not roles:
        return None
    normalized = [str(r).strip() for r in roles if r]
    for candidate in ROLE_PRIORITY:
        if candidate in normalized:
            return candidate
    return normalized[0]

def _session_roles():
    roles = st.session_state.get("roles")
    if isinstance(roles, list) and roles:
        return roles
    fallback = st.session_state.get("role")
    return [fallback] if fallback else []

def _gdpr_safe_count(value, threshold=5):
    try:
        n = int(value or 0)
    except Exception:
        n = 0
    if 0 < n < threshold:
        return f"<{threshold}"
    return f"{max(0, n):,}"

def _show_df_limited(df, key, default_limit=150):
    if df is None or df.empty:
        st.caption("No rows found for this selection.")
        return
    total_rows = len(df)
    show_all = st.checkbox(f"Show all rows ({total_rows})", key=f"{key}_show_all", value=False)
    if show_all or total_rows <= default_limit:
        _safe_dataframe(df, width="stretch", hide_index=True)
    else:
        _safe_dataframe(df.head(default_limit), width="stretch", hide_index=True)
        st.caption(f"Showing first {default_limit} of {total_rows} rows. Enable 'Show all rows' to view everything.")

def _can_view_event_attendee_details():
    roles = _session_roles()
    return any(r in ["Admin", "Manager", "ML"] for r in roles if r)

def _sanitize_record_for_role(record):
    if _can_view_event_attendee_details():
        return record
    if not isinstance(record, dict):
        return record
    redacted_keys = {
        "participant_list",
        "participants_list",
        "participant_ids",
        "participant_names",
        "attendee_list",
        "attendees_list",
        "attendee_names",
        "raw_event",
    }
    return {k: v for k, v in record.items() if k not in redacted_keys}

def ml_dashboard():
    st.title("Mountain Leader Dashboard")
    st.caption("Select an event to see attendees plus medical and emergency contact details.")

    region_options = ["Global", "North of England", "South of England", "Midlands", "Wales", "Other"]
    default_region = st.session_state.get("region") or "Global"
    st.sidebar.markdown("### Region Filter")
    ml_all = st.sidebar.checkbox("All Regions", value=True, key="ml_all_regions")
    if ml_all:
        region_val = "Global"
    else:
        default_index = region_options.index(default_region) if default_region in region_options else 0
        region_val = st.sidebar.selectbox("Region", region_options, index=default_index, key="ml_region")
    st.sidebar.caption(f"Region: {region_val}")

    timeframe, start_date, end_date = get_time_filters()

    data = fetch_ml_dashboard_data(region_val, start_date=start_date, end_date=end_date)
    if not data:
        st.error("No event data is available for the selected filters.")
        return

    raw_kpi = data.get("_raw_kpi") or {}
    events = raw_kpi.get("delivery_events") or []
    if not events:
        st.info("No delivery events available for the current region/timeframe.")
        return

    def _format_date(value):
        if not value:
            return "Unknown date"
        try:
            return pd.to_datetime(value).strftime("%Y-%m-%d")
        except Exception:
            return str(value)

    def _event_label(event):
        raw = event.get("raw_event") or {}
        name = _get_row_value(
            event,
            "name",
            "title",
            "event_name",
            "Display Name",
        ) or _get_row_value(raw, "name", "title", "event_name", "Display Name") or str(event.get("id") or raw.get("id") or "Unnamed Event")
        date_value = event.get("date") or raw.get("start_date") or raw.get("date")
        return f"{name} ({_format_date(date_value)})"

    sorted_events = sorted(
        events,
        key=lambda e: _format_date(e.get("date") or (e.get("raw_event") or {}).get("start_date") or ""),
        reverse=True,
    )
    labels = [_event_label(e) for e in sorted_events]
    selected_idx = st.selectbox(
        "Event",
        list(range(len(sorted_events))),
        format_func=lambda idx: labels[idx],
        key="ml_event_select",
    )
    selected_event = sorted_events[selected_idx]
    raw_event = selected_event.get("raw_event") or {}

    def _format_value(value):
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            try:
                return json.dumps(value)
            except Exception:
                return str(value)
        return str(value)

    metadata = []
    def _append_metadata(label, value):
        formatted = _format_value(value)
        if formatted:
            metadata.append({"Field": label, "Value": formatted})

    _append_metadata("Event ID", selected_event.get("id") or raw_event.get("id"))
    _append_metadata("Event Name", _get_row_value(selected_event, "name", "title", "event_name", "Display Name"))
    _append_metadata("Date", selected_event.get("date") or raw_event.get("start_date") or raw_event.get("date"))
    _append_metadata("Region", ", ".join(_to_list(raw_event.get("c_region") or raw_event.get("region") or "")))
    _append_metadata("Event Type", raw_event.get("type") or raw_event.get("category"))
    _append_metadata("Participants (Beacon)", selected_event.get("participants"))
    _append_metadata("Participants (Recorded)", raw_event.get("number_of_attendees") or raw_event.get("Attendees"))
    _append_metadata("Location", raw_event.get("location") or raw_event.get("venue"))
    _append_metadata("Status", raw_event.get("status"))
    _append_metadata("Description", raw_event.get("description"))

    if metadata:
        st.subheader("Event Details")
        _show_df_limited(pd.DataFrame(metadata), key="ml_event_metadata")

    people_rows = raw_kpi.get("region_people") or []
    def _normalize_name(value):
        return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())

    people_by_name = {}
    people_by_id = {}
    for person in people_rows:
        person_id = person.get("id")
        name_val = _get_row_value(person, "name", "full_name", "Display Name", "email") or person_id
        norm = _normalize_name(name_val)
        if norm:
            people_by_name.setdefault(norm, person)
        if person_id:
            people_by_id[str(person_id)] = person

    attendee_records = selected_event.get("attendee_records") or []
    attendee_options = []
    seen_attendees = set()
    attendee_record_by_name = {}
    attendee_record_by_id = {}

    def _add_option(label, name=None, att_id=None, record=None):
        key = (label.strip().lower(), str(att_id or ""), bool(record))
        if key in seen_attendees:
            return
        seen_attendees.add(key)
        display = label or f"Attendee {len(attendee_options)+1}"
        if att_id:
            display = f"{display} ({att_id})"
        attendee_options.append({"label": display, "name": name, "id": att_id, "record": record})

    def _person_id_from_record(rec):
        return _get_row_value(rec, "person_id", "contact_id", "participant_id", "attendee_id", "id")

    for rec in attendee_records:
        name_val = _get_row_value(
            rec,
            "name",
            "full_name",
            "display_name",
            "participant_name",
            "attendee_name",
            "person_name",
            "contact_name",
            "email",
        )
        if name_val:
            display_name = str(name_val).strip()
        else:
            display_name = None
        person_id = _person_id_from_record(rec)
        label = display_name or person_id or f"Attendee {len(attendee_options)+1}"
        if display_name:
            attendee_record_by_name[_normalize_name(display_name)] = rec
        if person_id:
            attendee_record_by_id[str(person_id)] = rec
        _add_option(label, display_name, person_id, record=rec)

    attendee_names = selected_event.get("participant_list") or []
    attendee_ids = selected_event.get("participant_ids") or []
    for idx, name in enumerate(attendee_names):
        idx_id = attendee_ids[idx] if idx < len(attendee_ids) else None
        _add_option(str(name).strip(), name, idx_id)

    if attendee_options:
        st.subheader("Participants")
    elif attendee_names:
        st.subheader("Attendee Names")
        _show_df_limited(pd.DataFrame({"Name": attendee_names}), key="ml_attendee_names", default_limit=250)
    if attendee_ids and not attendee_options:
        st.subheader("Attendee IDs")
        _show_df_limited(pd.DataFrame({"Attendee ID": attendee_ids}), key="ml_attendee_ids", default_limit=250)
    if not attendee_names and not attendee_ids and not attendee_options:
        st.info("Attendee names/IDs are not yet available in this event source.")

    selected_person = None
    selected_record = None
    if attendee_options:
        selected_idx = st.radio(
            "Click a participant to view details",
            list(range(len(attendee_options))),
            format_func=lambda idx: attendee_options[idx]["label"],
            key="ml_attendee_select",
        )
        selected_entry = attendee_options[selected_idx]
        st.markdown(f"**Details for:** {selected_entry['label']}")
        selected_record = selected_entry.get("record")
        person_record = None
        person_id = selected_entry.get("id")
        if not selected_record and person_id and str(person_id) in attendee_record_by_id:
            selected_record = attendee_record_by_id[str(person_id)]
        if not selected_record and selected_entry.get("name"):
            selected_record = attendee_record_by_name.get(_normalize_name(selected_entry["name"]))
        if person_id and str(person_id) in people_by_id:
            person_record = people_by_id[str(person_id)]
        if not person_record and selected_entry.get("name"):
            norm = _normalize_name(selected_entry["name"])
            person_record = people_by_name.get(norm)
        selected_person = person_record or selected_record
    else:
        st.caption("No attendee records available to view details.")

    def _collect_fields(sources, keywords):
        rows = []
        seen = set()
        for record in sources:
            if not isinstance(record, dict):
                continue
            for key, value in record.items():
                if value in [None, "", [], {}]:
                    continue
                key_lower = str(key).lower()
                if any(term in key_lower for term in keywords):
                    label = _pretty_field_name(key)
                    if label in seen:
                        continue
                    seen.add(label)
                    rows.append({"Field": label, "Value": _format_value(value)})
        return rows

    def _collect_scalar_fields(record):
        rows = []
        seen = set()
        if not isinstance(record, dict):
            return rows
        for key, value in record.items():
            if value in [None, "", [], {}]:
                continue
            if isinstance(value, (dict, list, tuple, set)):
                continue
            label = _pretty_field_name(key)
            if label in seen:
                continue
            seen.add(label)
            rows.append({"Field": label, "Value": _format_value(value)})
        return rows

    if selected_person or selected_record:
        sources = [selected_record, selected_person]
        personal_keywords = ("name", "full_name", "display_name", "email", "phone", "mobile", "telephone", "dob", "date_of_birth", "address", "postcode", "gender", "pronoun", "signup", "type")
        medical_keywords = ("medical", "health", "medication", "condition", "allergy", "fitness", "dietary", "doctor", "balance", "chest_pain", "bone_joint")
        emergency_keywords = ("emergency", "emergency_contact", "next_of_kin", "contact_person", "contact_name", "contact_phone")

        personal_rows = _collect_fields(sources, personal_keywords)
        medical_rows = _collect_fields(sources, medical_keywords)
        emergency_rows = _collect_fields(sources, emergency_keywords)
        general_rows = _collect_scalar_fields(selected_record)

        if personal_rows:
            st.subheader("Personal Information")
            _show_df_limited(pd.DataFrame(personal_rows), key="ml_attendee_personal", default_limit=25)
        if medical_rows:
            st.subheader("Medical Information")
            _show_df_limited(pd.DataFrame(medical_rows), key="ml_attendee_medical", default_limit=25)
        if emergency_rows:
            st.subheader("Emergency Contact Details")
            _show_df_limited(pd.DataFrame(emergency_rows), key="ml_attendee_emergency", default_limit=25)
        if general_rows:
            st.subheader("Participant Record")
            _show_df_limited(pd.DataFrame(general_rows), key="ml_attendee_general", default_limit=50)
        if not any((personal_rows, medical_rows, emergency_rows, general_rows)):
            st.info("No additional details were found for this attendee.")

    def _find_fields(record, keywords):
        fields = {}
        if not isinstance(record, dict):
            return fields
        for key, value in record.items():
            if value in [None, "", [], {}]:
                continue
            key_lower = str(key).lower()
            if any(term in key_lower for term in keywords):
                fields[_pretty_field_name(key)] = value
        return fields

    medical_info = _find_fields(raw_event, ("medical", "health", "medication", "condition", "allergy"))
    emergency_info = _find_fields(raw_event, ("emergency", "emergency_contact", "next_of_kin", "contact", "phone"))

    def _render_section(title, info, key_prefix):
        if not info:
            return
        rows = [{"Field": k, "Value": _format_value(v)} for k, v in info.items()]
        st.subheader(title)
        _show_df_limited(pd.DataFrame(rows), key=f"ml_{key_prefix}", default_limit=50)

    _render_section("Medical Information", medical_info, "medical")
    _render_section("Emergency Contact Details", emergency_info, "emergency")

    with st.expander("Raw Event Payload"):
        st.json(raw_event)

def funder_dashboard():
    st.title("Funder Dashboard")
    st.caption("GDPR-safe, aggregated metrics only. No personal data is shown.")

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    st.sidebar.title(f"{greeting}, {st.session_state.get('name', 'User')}")
    st.sidebar.info(f"Role: {st.session_state.get('role', 'Funder')}")

    region_options = ["Global", "North of England", "South of England", "Midlands", "Wales", "Other"]
    role = st.session_state.get("role")
    assigned_scope = st.session_state.get("region") or "Global"
    assigned_funder = _decode_funder_scope(assigned_scope)
    if role == "Funder" and not assigned_funder and assigned_scope not in ("", "Global"):
        assigned_funder = assigned_scope

    c_region, c_tf = st.columns([1, 1])
    with c_region:
        if role == "Funder":
            region_val = "Global"
            st.caption("Region: Global")
        else:
            default_index = region_options.index(assigned_scope) if assigned_scope in region_options else 0
            region_val = st.selectbox("Region", region_options, index=default_index, key="funder_region")
    with c_tf:
        timeframe = st.selectbox("Timeframe", ["All Time", "Year", "Quarter", "Month", "Custom Range"], index=0, key="funder_timeframe")

    today = pd.Timestamp.now().normalize()
    start_date = None
    end_date = None
    if timeframe == "Year":
        start_date = today - pd.DateOffset(years=1)
        end_date = today
    elif timeframe == "Quarter":
        start_date = today - pd.DateOffset(months=3)
        end_date = today
    elif timeframe == "Month":
        start_date = today - pd.DateOffset(months=1)
        end_date = today
    elif timeframe == "Custom Range":
        cc1, cc2 = st.columns(2)
        with cc1:
            custom_start = st.date_input("Start date", value=(today - pd.Timedelta(days=30)).date(), key="funder_start")
        with cc2:
            custom_end = st.date_input("End date", value=today.date(), key="funder_end")
        if custom_end < custom_start:
            st.error("End date must be on or after start date.")
            return
        start_date = pd.Timestamp(custom_start)
        end_date = pd.Timestamp(custom_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    data = fetch_funder_dashboard_data(
        region_val,
        start_date=start_date,
        end_date=end_date,
        include_summary=(role != "Funder"),
    )
    if not data:
        st.error("No dashboard data is available for this public view.")
        return

    def _funder_key(value):
        return _norm_key(value)

    raw_income = data.get("_raw_income", {}) or {}
    payments_all = raw_income.get("payments") or []
    grants_all = raw_income.get("grants") or []
    org_name_lookup = get_organisation_name_lookup()
    funder_map = {}
    for fname in get_assigned_funder_names():
        fk = _funder_key(fname)
        if fk and fk not in funder_map:
            funder_map[fk] = fname
    for row in payments_all + grants_all:
        fname = _extract_funder_name(row, org_name_lookup=org_name_lookup)
        fk = _funder_key(fname)
        if fk and fk not in funder_map:
            funder_map[fk] = fname

    if role == "Funder":
        selected_funder = assigned_funder or "Unknown / Not tagged"
        selected_funder_key = _funder_key(selected_funder)
        st.caption(f"Funder: {selected_funder}")
    else:
        funder_options = ["All Funders"] + sorted(funder_map.values(), key=lambda x: x.lower())
        selected_funder = st.selectbox("Funder", funder_options, index=0, key="funder_selector")
        selected_funder_key = _funder_key(selected_funder)

    def _row_matches_funder(row):
        if selected_funder == "All Funders":
            return True
        return _funder_key(_extract_funder_name(row, org_name_lookup=org_name_lookup)) == selected_funder_key

    filtered_payments = [r for r in payments_all if _row_matches_funder(r)]
    filtered_grants = [r for r in grants_all if _row_matches_funder(r)]

    filtered_total_funds = sum(_coerce_money(r.get("amount")) for r in filtered_payments)
    filtered_total_funds += sum(
        _coerce_money(r.get("amount"))
        for r in filtered_grants
        if str(r.get("stage") or "").strip().lower() == "won"
    )
    filtered_bids_submitted = sum(
        1
        for r in filtered_grants
        if any(x in str(r.get("stage") or "").lower() for x in ["submitted", "review", "pending"])
    )

    last_refresh = get_last_refresh_timestamp()
    if last_refresh:
        st.caption(f"Last Data Refresh (UTC): {last_refresh.strftime('%d/%m/%Y %H:%M')}")
    else:
        st.caption("Last Data Refresh (UTC): Unknown")

    if role != "Funder":
        g = data.get("governance", {})
        p = data.get("partnerships", {})
        d = data.get("delivery", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Active Volunteers", _gdpr_safe_count(g.get("volunteers_new", 0)))
        m2.metric("Active Organisations", _gdpr_safe_count(p.get("active_referrals", 0)))
        m3.metric("Delivery Events", _gdpr_safe_count(d.get("walks_delivered", 0)))
        m4, m5, m6 = st.columns(3)
        m4.metric("Participants Reached", _gdpr_safe_count(d.get("participants", 0)))
        m5.metric("Bids Submitted (Selected Funder)", _gdpr_safe_count(filtered_bids_submitted))
        m6.metric("Total Funds Raised (Selected Funder)", f"£{float(filtered_total_funds or 0):,.2f}")
        st.caption("Funder filter applies to funding metrics and income trend. Non-funding metrics remain region/timeframe totals.")

        st.markdown("### Partnership Mix")
        mix_rows = []
        for sector, count in (p.get("LSP") or {}).items():
            mix_rows.append({"Type": "Strategic", "Sector": str(sector), "Count": int(count or 0)})
        for sector, count in (p.get("LDP") or {}).items():
            mix_rows.append({"Type": "Delivery", "Sector": str(sector), "Count": int(count or 0)})
        mix_df = pd.DataFrame(mix_rows)
        if not mix_df.empty:
            fig_mix = px.bar(mix_df, x="Sector", y="Count", color="Type", barmode="group")
            render_plot_with_export(fig_mix, "funder-partnership-mix", "funder_partnership_mix")
        else:
            st.info("No partnership data available for this selection.")

        st.markdown("### Delivery Demographics (Aggregated)")
        demo_df = pd.DataFrame(
            [{"Group": str(k), "Count": int(v or 0)} for k, v in (d.get("demographics") or {}).items()]
        )
        if not demo_df.empty:
            demo_df = demo_df.sort_values("Count", ascending=False)
            fig_demo = px.bar(demo_df, x="Group", y="Count")
            render_plot_with_export(fig_demo, "funder-demographics", "funder_demographics")
        else:
            st.info("No demographic summary available for this selection.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Bids Submitted", _gdpr_safe_count(filtered_bids_submitted))
        m2.metric("Total Funds Raised", f"£{float(filtered_total_funds or 0):,.2f}")

    st.markdown("### Income Trend (Aggregated, Funder Filtered)")
    income_rows = []
    for row in filtered_payments:
        income_rows.append({
            "date": row.get("payment_date"),
            "source": "Payments",
            "amount": _coerce_money(row.get("amount")),
        })
    for row in filtered_grants:
        income_rows.append({
            "date": row.get("close_date"),
            "source": "Grants",
            "amount": _coerce_money(row.get("amount")),
        })
    if income_rows:
        income_df = pd.DataFrame(income_rows)
        income_df["date"] = pd.to_datetime(income_df["date"], errors="coerce")
        income_df = income_df.dropna(subset=["date"])
        if not income_df.empty:
            monthly = income_df.groupby([pd.Grouper(key="date", freq="ME"), "source"], as_index=False)["amount"].sum()
            fig_income = px.line(monthly, x="date", y="amount", color="source", markers=True)
            render_plot_with_export(fig_income, "funder-income-trend", "funder_income_trend")
        else:
            st.info("No dated income rows available for trend chart.")
    else:
        st.info("No income rows available for trend chart.")

def login_page():
    st.markdown("## Login")
    st.markdown(
        "<div class='neon-callout'>Please sign in with your email address.</div>",
        unsafe_allow_html=True
    )
    if DB_TYPE == 'local':
        st.warning("Running in Local Mode. Add Supabase secrets to enable Cloud Database.")
        
    with st.form("login_form"):
        st.text_input("Email Address", key="login_email")
        st.text_input("Password", type="password", key="login_password")
        c_login, c_forgot = st.columns(2)
        submitted = c_login.form_submit_button("Login", width="stretch")
        forgot_submitted = c_forgot.form_submit_button("Forgot password?", width="stretch")

    if forgot_submitted:
        email = st.session_state.get("login_email", "").strip().lower()
        if not email:
            st.error("Please enter your email address first.")
        else:
            if DB_TYPE == 'supabase':
                try:
                    existing_pending = (
                        DB_CLIENT.table("password_reset_requests")
                        .select("id")
                        .eq("email", email)
                        .eq("status", "pending")
                        .limit(1)
                        .execute()
                    )
                    if existing_pending.data:
                        st.info("A reset request is already pending for this email.")
                    else:
                        DB_CLIENT.table("password_reset_requests").insert({
                            "email": email,
                            "status": "pending"
                        }).execute()
                        st.success("Request sent. An admin will set a temporary password.")
                except Exception as e:
                    st.error(f"Could not submit request: {e}")
            else:
                st.error("Password reset is only available in Supabase mode.")

    if submitted:
        email = st.session_state.get("login_email", "")
        password = st.session_state.get("login_password", "")
        auth_result = verify_user(email, password)
        status = auth_result[0]
        if status == "success":
            _, role, region, name, must_change, roles = auth_result
            st.session_state['logged_in'] = True
            st.session_state['name'] = name
            st.session_state['email'] = email
            st.session_state['role'] = role
            st.session_state['roles'] = roles or [role] if role else []
            st.session_state['region'] = region
            st.session_state['force_password_change'] = bool(must_change)
            st.rerun()
        elif status == "missing_fields":
            st.error("Please enter your email and password.")
        elif status == "user_not_found":
            st.error("User not found.")
        else:
            st.error("Invalid password.")

def password_change_page():
    st.markdown("## Change Password")
    st.info("Please set a new password to continue.")

    temp_password = st.text_input("Temporary Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")

    if st.button("Update Password"):
        if not temp_password or not new_password or not confirm_password:
            st.error("Please complete all fields.")
            return
        if new_password != confirm_password:
            st.error("New passwords do not match.")
            return

        email = st.session_state.get("email")
        try:
            # Verify temp password by re-auth
            auth_resp = DB_CLIENT.auth.sign_in_with_password({"email": email, "password": temp_password})
            if not auth_resp or not auth_resp.user:
                st.error("Temporary password is incorrect.")
                return
            user_id = auth_resp.user.id

            # Update auth password (requires service role key)
            admin_client = get_admin_client()
            if not admin_client:
                st.error("Admin client not available. Check Supabase secrets.")
                return
            admin_client.auth.admin.update_user_by_id(user_id, {"password": new_password})

            # Clear must_change_password flag
            admin_client.table("user_roles").update({"must_change_password": False}).eq("user_id", user_id).execute()

            st.session_state['force_password_change'] = False
            st.success("Password updated. Please continue.")
            st.rerun()
        except Exception as e:
            st.error(f"Password update failed: {e}")

def admin_dashboard():
    st.title("Admin Dashboard")
    st.caption(f"Database Mode: {DB_TYPE.upper()}")
    if st.session_state.get("supabase_role"):
        st.caption(f"Supabase key role: {st.session_state.get('supabase_role')}")

    # --- PASSWORD RESET REQUESTS ---
    with st.expander("Password Reset Requests", expanded=False):
        if DB_TYPE == 'supabase':
            try:
                admin_client = get_admin_client()
                if not admin_client:
                    st.error("Admin client not available. Check Supabase secrets.")
                    reqs = []
                else:
                    reqs = admin_client.table("password_reset_requests") \
                    .select("id, email, status, created_at") \
                    .eq("status", "pending") \
                    .order("created_at", desc=True) \
                    .execute().data or []
            except Exception as e:
                reqs = []
                st.error(f"Could not load requests: {e}")
            if reqs:
                req_emails = [r["email"] for r in reqs]
                selected_email = st.selectbox("Pending requests", req_emails)
                temp_pw = st.text_input("Temporary Password", type="password", key="reset_temp_pw")
                if st.button("Set Temporary Password"):
                    if not temp_pw:
                        st.error("Please enter a temporary password.")
                    else:
                        try:
                            user_row = admin_client.table("user_roles").select("user_id").eq("email", selected_email).execute()
                            if not user_row.data:
                                st.error("User not found for that email.")
                            else:
                                user_id = user_row.data[0]["user_id"]
                                admin_client.auth.admin.update_user_by_id(user_id, {"password": temp_pw})
                                admin_client.table("user_roles").update({"must_change_password": True}).eq("user_id", user_id).execute()
                                admin_client.table("password_reset_requests").update({"status": "completed"}).eq("email", selected_email).execute()
                                st.success("Temporary password set. User will be prompted to change it on next login.")
                        except Exception as e:
                            st.error(f"Failed to reset password: {e}")
            else:
                st.info("No pending requests.")
        else:
            st.info("Password reset requests are available only in Supabase mode.")

    # --- USER MANAGEMENT ---
    with st.expander("Create New User", expanded=False):
        c1, c2 = st.columns(2)
        new_name = c1.text_input("Full Name")
        new_email = c2.text_input("Email")
        c3, c4 = st.columns(2)
        new_pw = c3.text_input("Password", type="password")
        role_choices = ["RPL", "ML", "Manager", "Admin", "Funder"]
        new_roles = c4.multiselect("Roles", role_choices, default=["RPL"])
        selected_funder_name = ""
        if "Funder" in new_roles:
            funder_choices = get_available_funders()
            if funder_choices:
                selected_funder_name = st.selectbox("Funder Name", funder_choices, key="new_user_funder_name")
            manual_funder = st.text_input("Or type funder name", key="new_user_funder_name_manual")
            if manual_funder.strip():
                selected_funder_name = manual_funder.strip()
            new_region = _encode_funder_scope(selected_funder_name)
        else:
            new_region = st.text_input("Region (e.g., North West)")
        
        if st.button("Create User"):
            if new_email and new_pw:
                if not new_roles:
                    st.error("Please assign at least one role.")
                    return
                if "Funder" in new_roles and not selected_funder_name.strip():
                    st.error("Please select or enter a funder name for this Funder user.")
                else:
                    if create_user(new_name, new_email, new_pw, new_roles, new_region):
                        st.success(f"User {new_email} created!")
                        st.rerun()
                    else:
                        st.error("User with this email already exists (or role lookup failed).")
            else:
                st.error("Please fill in email and password.")

    # List Users
    users_data = get_all_users()
    if users_data:
        df_users = pd.DataFrame(users_data)
        with st.expander("Existing Users & Actions", expanded=False):
            _safe_dataframe(df_users, width="stretch")
            
            if not df_users.empty:
                user_emails = df_users['email'].tolist()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.subheader("Reset Password")
                    target_email = st.selectbox("Select User", user_emails, key="reset_sel")
                    reset_pw = st.text_input("New Password", type="password", key="reset_pw")
                    if st.button("Reset Password"):
                        reset_password(target_email, reset_pw)
                        st.success(f"Password updated.")
                
                with col2:
                    st.subheader("Update Role")
                    target_role_email = st.selectbox("Select User", user_emails, key="role_sel")
                    role_choices = ["RPL", "ML", "Manager", "Admin", "Funder"]
                    existing_roles = get_user_roles(target_role_email) or ["RPL"]
                    new_role_update = st.multiselect("New Roles", role_choices, default=existing_roles, key="role_up")
                    selected_update_funder = ""
                    if "Funder" in new_role_update:
                        update_funder_choices = get_available_funders()
                        if update_funder_choices:
                            selected_update_funder = st.selectbox("Funder Name", update_funder_choices, key="role_up_funder_name")
                        manual_update_funder = st.text_input("Or type funder name", key="role_up_funder_name_manual")
                        if manual_update_funder.strip():
                            selected_update_funder = manual_update_funder.strip()
                    role_reason = st.text_input("Reason for role change", key="role_reason")
                    role_confirm = st.checkbox("I confirm this role change", key="role_confirm")
                    if st.button("Update Role"):
                        if not role_reason.strip():
                            st.error("Please provide a reason for the role update.")
                        elif not role_confirm:
                            st.error("Please confirm the role update.")
                        elif not new_role_update:
                            st.error("Select at least one role.")
                        elif "Funder" in new_role_update and not selected_update_funder.strip():
                            st.error("Please select or enter a funder name for this Funder user.")
                        else:
                            update_user_roles(
                                target_role_email,
                                new_role_update,
                                audit_reason=role_reason.strip(),
                                audit_confirmed=True,
                            )
                            if "Funder" in new_role_update:
                                update_user_region(target_role_email, _encode_funder_scope(selected_update_funder))
                            st.success("Roles updated.")
                            st.rerun()

                with col3:
                    st.subheader("Delete User")
                    target_del = st.selectbox("Select User", user_emails, key="del_sel")
                    delete_reason = st.text_input("Reason for deletion", key="delete_reason")
                    delete_confirm = st.checkbox("I confirm this user deletion", key="delete_confirm")
                    if st.button("Delete User", type="primary"):
                        if not delete_reason.strip():
                            st.error("Please provide a reason for deletion.")
                        elif not delete_confirm:
                            st.error("Please confirm user deletion.")
                        else:
                            delete_user(
                                target_del,
                                audit_reason=delete_reason.strip(),
                                audit_confirmed=True,
                            )
                            st.success("User deleted.")
                            st.rerun()

    # --- SYSTEM ACTIONS ---
    st.markdown("---")
    st.subheader("System Actions")
    with st.expander("Sync Performance", expanded=False):
        if DB_TYPE == 'supabase':
            try:
                perf_resp = (
                    DB_CLIENT.table("audit_logs")
                    .select("created_at, action, details")
                    .in_("action", ["Data Sync Completed", "Data Sync Failed"])
                    .order("created_at", desc=True)
                    .limit(100)
                    .execute()
                )
                perf_rows = perf_resp.data or []
            except Exception:
                perf_rows = []

            completed = []
            for row in perf_rows:
                if row.get("action") != "Data Sync Completed":
                    continue
                details = row.get("details") or {}
                if details.get("source") != "beacon_api":
                    continue
                completed.append({
                    "created_at": row.get("created_at"),
                    "details": details,
                })

            if completed:
                latest = completed[0]
                latest_details = latest.get("details") or {}
                c_perf1, c_perf2, c_perf3, c_perf4 = st.columns(4)
                c_perf1.metric("Last Total", f"{latest_details.get('total_duration_ms', 0) / 1000:.1f}s")
                c_perf2.metric("Fetch", f"{latest_details.get('fetch_duration_ms', 0) / 1000:.1f}s")
                c_perf3.metric("Transform", f"{latest_details.get('transform_duration_ms', 0) / 1000:.1f}s")
                c_perf4.metric("Upsert", f"{latest_details.get('upsert_duration_ms', 0) / 1000:.1f}s")

                recent = completed[:10]
                if recent:
                    avg_total = sum(int((x.get("details") or {}).get("total_duration_ms") or 0) for x in recent) / len(recent)
                    st.caption(f"Average total duration (last {len(recent)} successful syncs): {avg_total / 1000:.1f}s")

                last_sync_raw = latest.get("created_at") or latest_details.get("synced_at")
                last_sync_ts = pd.to_datetime(last_sync_raw, utc=True, errors="coerce")
                if pd.isna(last_sync_ts):
                    last_sync_label = "Unknown"
                else:
                    last_sync_label = last_sync_ts.strftime("%d/%m/%Y %H:%M UTC")
                sync_type = "Automatic" if (latest_details.get("trigger") == "github_actions") else "Manual"
                st.caption(f"Last successful sync: {last_sync_label} | Type: {sync_type}")
            else:
                st.info("No completed Beacon sync performance records found yet.")
        else:
            st.info("Sync performance is available only in Supabase mode.")

    st.subheader("Beacon API Sync")
    if DB_TYPE == 'supabase':
        admin_client = get_admin_client()
        if admin_client:
            col_smoke, col_sync = st.columns(2)
            if col_smoke.button("Run Beacon API Smoke Test"):
                try:
                    log_audit_event("Beacon Smoke Test Started", {"source": "beacon_api"})
                    smoke_result = run_beacon_api_smoke_test()
                    log_audit_event("Beacon Smoke Test Completed", {"source": "beacon_api", **smoke_result})
                    if smoke_result.get("checks", {}).get("docs_compliant_shape"):
                        st.success(
                            f"Smoke test passed ({smoke_result['status_code']}) in "
                            f"{smoke_result['response_time_ms']} ms."
                        )
                    else:
                        st.warning(
                            f"Smoke test passed with legacy response shape "
                            f"({smoke_result['status_code']}) in {smoke_result['response_time_ms']} ms."
                        )
                    st.json(smoke_result)
                except Exception as e:
                    log_audit_event("Beacon Smoke Test Failed", {"source": "beacon_api", "error": str(e)})
                    st.error(f"Smoke test failed: {e}")

            if col_sync.button("Sync Beacon API to Database"):
                job_id, err = start_manual_sync_job(
                    st.session_state.get("email", "System"),
                    st.session_state.get("region", "Global"),
                )
                if job_id:
                    st.session_state["manual_sync_job_id"] = job_id
                if err:
                    st.info(err)
                else:
                    st.success("Manual sync started in background. You can switch to KPI Dashboard while it runs.")
                    st.rerun()

            active_job_id = st.session_state.get("manual_sync_job_id")
            active_state = _get_sync_job_state(active_job_id) if active_job_id else None
            if not active_state:
                active_state = get_latest_manual_sync_state(st.session_state.get("email"))
                if active_state and active_state.get("job_id"):
                    st.session_state["manual_sync_job_id"] = active_state.get("job_id")
                    active_job_id = active_state.get("job_id")
            if active_state and active_state.get("status") in ("queued", "running"):
                c_stop, c_clear = st.columns(2)
                if c_stop.button("Stop Manual API Sync", key="stop_manual_sync_btn"):
                    ok, msg = stop_manual_sync_job(
                        active_job_id,
                        user_email=st.session_state.get("email", "System"),
                        region=st.session_state.get("region", "Global"),
                    )
                    if ok:
                        st.warning(msg)
                    else:
                        st.info(msg)
                    st.rerun()
                if c_clear.button("Clear Stuck Sync", key="clear_stuck_sync_btn"):
                    ok, msg = clear_manual_sync_job(
                        active_job_id,
                        user_email=st.session_state.get("email", "System"),
                        region=st.session_state.get("region", "Global"),
                    )
                    if ok:
                        st.warning(msg)
                    else:
                        st.info(msg)
                    st.rerun()
            if active_state:
                with st.expander("Active Sync Progress", expanded=True):
                    render_manual_sync_main_panel(active_state)
        else:
            st.info("Admin client not available. Check Supabase secrets.")
    else:
        st.info("API sync is available only in Supabase mode.")

    st.subheader("Beacon CSV Upload")
    if DB_TYPE == 'supabase':
        admin_client = get_admin_client()
        if admin_client:
            if st.button("Upload Beacon Exports"):
                log_audit_event("CSV Upload Opened", {"source": "beacon_csv"})
                st.session_state["show_upload_dialog"] = True

            if st.session_state.get("show_upload_dialog"):
                @st.dialog("Upload Beacon Exports")
                def _upload_dialog():
                    people_file = st.file_uploader("People CSV", type=["csv"])
                    org_file = st.file_uploader("Organisation CSV", type=["csv"])
                    event_file = st.file_uploader("Event CSV", type=["csv"])
                    payment_file = st.file_uploader("Payment CSV", type=["csv"])
                    grant_file = st.file_uploader("Grant CSV", type=["csv"])

                    if st.button("Import"):
                        log_audit_event("Data Import Started", {"source": "beacon_csv"})
                        uploads = {
                            "people": _read_uploaded_csv(people_file),
                            "organization": _read_uploaded_csv(org_file),
                            "event": _read_uploaded_csv(event_file),
                            "payment": _read_uploaded_csv(payment_file),
                            "grant": _read_uploaded_csv(grant_file),
                        }
                        result = import_beacon_uploads(admin_client, uploads)
                        
                        # --- AUDIT LOG ---
                        log_audit_event("Data Imported", {"source": "beacon_csv", **result})
                        
                        st.success(f"Imported: {result}")
                        st.session_state["show_upload_dialog"] = False
                _upload_dialog()
        else:
            st.info("Admin client not available. Check Supabase secrets.")
    else:
        st.info("CSV upload is available only in Supabase mode.")
    col_sys_1, col_sys_2 = st.columns([1, 3])
    refresh_reason = col_sys_2.text_input("Reason for full refresh", key="refresh_reason")
    refresh_confirm = col_sys_2.checkbox("I confirm full dashboard data reset (users kept)", key="refresh_confirm")
    with col_sys_1:
        if st.button("Refresh All Dashboard Data"):
            if not refresh_reason.strip():
                st.error("Please provide a reason for full refresh.")
            elif not refresh_confirm:
                st.error("Please confirm full dashboard refresh.")
            elif DB_TYPE != 'supabase':
                st.error("Full dashboard data reset is available only in Supabase mode.")
            else:
                refresh_client = get_admin_client()
                if not refresh_client:
                    st.error("Admin client not available. Check Supabase secrets.")
                    return

                refresh_progress = st.progress(0, text="Preparing dashboard data reset...")

                def _refresh_ui_progress(progress, message):
                    refresh_progress.progress(int(max(0, min(100, progress))), text=message)

                deleted_counts, delete_errors = clear_dashboard_data_except_users(
                    refresh_client,
                    progress_callback=_refresh_ui_progress
                )
                log_audit_event(
                    "Dashboard Refresh",
                    {
                        "scope": "all_dashboard_data_except_users",
                        "reason": refresh_reason.strip(),
                        "confirmed": True,
                        "deleted_counts": deleted_counts,
                        "errors": delete_errors,
                    },
                )
                st.cache_data.clear()
                if delete_errors:
                    refresh_progress.progress(100, text="Dashboard data reset finished with errors.")
                    st.warning("Dashboard data reset completed with some errors. Check audit logs for details.")
                else:
                    refresh_progress.progress(100, text="Dashboard data reset complete.")
                    st.success("Dashboard data reset complete (users kept). Reloading...")
                st.rerun()

    # --- AUDIT LOG UI ---
    st.markdown("---")
    with st.expander("System Audit Log", expanded=False):
        if DB_TYPE == 'supabase':
            # 1. Build Query
            query = DB_CLIENT.table("audit_logs").select("*").order("created_at", desc=True).limit(200)

            # 2. Fetch & Display
            try:
                resp = query.execute()
                data = resp.data
                
                if data:
                    df_log = pd.DataFrame(data)
                    if "details" not in df_log.columns:
                        df_log["details"] = ""
                    df_log["details_norm"] = df_log["details"].apply(
                        lambda d: json.dumps(d, sort_keys=True, default=str) if isinstance(d, (dict, list)) else str(d)
                    )

                    # Search & Filter Controls
                    col_search, col_filter = st.columns([3, 1])
                    search_term = col_search.text_input(
                        "Search Logs (User, Action, or Details)",
                        placeholder="e.g. 'Data Sync Completed' or 'scott@...'"
                    )
                    action_options = ["All"] + sorted(df_log["action"].dropna().astype(str).unique().tolist())
                    action_filter = col_filter.selectbox("Filter by Action", action_options)
                    if action_filter != "All":
                        df_log = df_log[df_log["action"] == action_filter]
                    df_log = df_log[df_log["action"] != "Data Sync Progress"]
                    df_log = df_log[~df_log["action"].isin(["Dashboard Filter Changed", "Dashboard View Changed"])]

                    # Convert timestamps to readable format
                    df_log['created_at'] = pd.to_datetime(df_log['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Client-side Search (for flexibility with JSON/Text columns)
                    if search_term:
                        search_term = search_term.lower()
                        mask = (
                            df_log['user_email'].str.lower().str.contains(search_term) |
                            df_log['action'].str.lower().str.contains(search_term) |
                            df_log['details'].astype(str).str.lower().str.contains(search_term)
                        )
                        df_log = df_log[mask]

                    if not df_log.empty:
                        df_log = df_log.drop_duplicates(
                            subset=["user_email", "action", "details_norm", "region"],
                            keep="first"
                        )

                    _safe_dataframe(
                        df_log[['created_at', 'user_email', 'action', 'details', 'region']], 
                        width="stretch",
                        hide_index=True
                    )
                else:
                    st.info("No logs found.")
            except Exception as e:
                st.error(f"Failed to load logs: {e}")
        else:
            st.info("Audit logging is only enabled in Supabase mode.")

def get_time_filters():
    st.sidebar.markdown("### Time Filters")
    timeframe = st.sidebar.selectbox(
        "Timeframe",
        ["All Time", "Year", "Quarter", "Month", "Week", "Custom Range"],
        index=0
    )

    today = datetime.now().date()
    start_date = None
    end_date = None

    def _month_range(year, month):
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1) - pd.Timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - pd.Timedelta(days=1)
        return start, end

    if timeframe == "All Time":
        start_date = None
        end_date = None
    elif timeframe == "Year":
        year = st.sidebar.selectbox("Year", list(range(today.year, today.year - 5, -1)))
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
    elif timeframe == "Quarter":
        year = st.sidebar.selectbox("Year", list(range(today.year, today.year - 5, -1)))
        quarter = st.sidebar.selectbox("Quarter", ["Q1", "Q2", "Q3", "Q4"])
        q_start_month = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[quarter]
        start_date, end_date = _month_range(year, q_start_month)
        _, end_date = _month_range(year, q_start_month + 2)
    elif timeframe == "Month":
        year = st.sidebar.selectbox("Year", list(range(today.year, today.year - 5, -1)))
        month = st.sidebar.selectbox("Month", list(range(1, 13)))
        start_date, end_date = _month_range(year, month)
    elif timeframe == "Week":
        # Week starts on Monday
        current_week_start = today - pd.Timedelta(days=today.weekday())
        week_start = st.sidebar.date_input(
            "Week starting (Monday)",
            value=current_week_start
        )
        if week_start.weekday() != 0:
            st.sidebar.warning("Week start adjusted to Monday.")
            week_start = week_start - pd.Timedelta(days=week_start.weekday())
        week_end = week_start + pd.Timedelta(days=6)
        start_date = datetime.combine(week_start, datetime.min.time())
        end_date = datetime.combine(week_end, datetime.max.time())
        st.sidebar.caption(f"Week: {week_start} to {week_end}")
    else:
        custom_start = st.sidebar.date_input("Start date", value=today - pd.Timedelta(days=30))
        custom_end = st.sidebar.date_input("End date", value=today)
        if custom_end < custom_start:
            st.sidebar.error("End date must be on or after start date.")
        else:
            start_date = datetime.combine(custom_start, datetime.min.time())
            end_date = datetime.combine(custom_end, datetime.max.time())

    if start_date and end_date:
        st.sidebar.caption(f"Filtering: {start_date.date()} to {end_date.date()}")
    elif timeframe == "All Time":
        st.sidebar.caption("Filtering: All time")

    log_audit_state_change(
        "time_filters",
        "Dashboard Filter Changed",
        {
            "timeframe": timeframe,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    )

    return timeframe, start_date, end_date


def main_dashboard():
    # Sidebar Info
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    st.sidebar.title(f"{greeting}, {st.session_state['name']}")
    st.sidebar.info(f"Role: {st.session_state['role']}")
    
    # --- REGION FILTER ---
    st.sidebar.markdown("### Region Filter")
    role = st.session_state.get('role')
    default_region = st.session_state.get('region') or "Global"
    if role in ["Admin", "Manager", "RPL", "ML"]:
        all_regions = st.sidebar.checkbox("All Regions", value=True)
        if all_regions:
            region_val = "Global"
        else:
            region_options = ["North of England", "South of England", "Midlands", "Wales", "Other"]
            default_index = region_options.index(default_region) if default_region in region_options else 0
            region_val = st.sidebar.selectbox("Region", region_options, index=default_index)
    else:
        region_val = default_region
    st.sidebar.caption(f"Region: {region_val}")

    show_global_only_kpis = region_val == "Global"
    section_labels = ["Governance", "Partnerships", "Delivery"]
    if show_global_only_kpis:
        section_labels.extend(["Income", "Comms"])
    section_labels.append("Case Studies")
    active_section = st.sidebar.selectbox(
        "KPI Section",
        section_labels,
        index=0,
        key="kpi_active_section",
    )

    timeframe, start_date, end_date = get_time_filters()

    show_debug = False
    if st.session_state.get("role") in ["Admin", "Manager", "RPL", "ML"]:
        show_debug = st.sidebar.checkbox("Show KPI Debug", value=False, key="kpi_show_debug")

    if active_section == "Case Studies":
        data = {"region": region_val, "_raw_kpi": {}, "_debug": {}}
    elif show_debug:
        data = fetch_supabase_data(region_val, start_date=start_date, end_date=end_date)
    else:
        data = fetch_kpi_section_data(active_section, region_val, start_date=start_date, end_date=end_date)
    if not data:
        st.error("No Supabase data found for the selected filters.")
        return

    st.title(f"Region Dashboard: {data['region']}")
    # Removed header metadata captions per request
    st.markdown('<div class="section-card"><span class="badge">Live KPI Overview</span></div>', unsafe_allow_html=True)

    if show_debug:
        debug = data.get("_debug") or {}
        st.markdown("### KPI Debug Counts")
        st.caption("Debug metrics are shown from the current filtered KPI dataset.")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("People in Region", debug.get("region_people", 0))
        d2.metric("Volunteers", debug.get("volunteers", 0))
        d3.metric("Steering Volunteers", debug.get("steering_volunteers", 0))
        d4.metric("Events in Region", debug.get("region_events", 0))
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Walk Events", debug.get("walk_events", 0))
        e2.metric("Participants", debug.get("participants", 0))
        e3.metric("Grants in Region", debug.get("region_grants", 0))
        e4.metric("Bids Submitted", debug.get("bids_submitted", 0))

    raw_kpi = data.get("_raw_kpi") or {}

    def _rows_to_df(rows, field_map):
        out = []
        for r in rows or []:
            row_out = {}
            for out_col, getter in field_map.items():
                try:
                    row_out[out_col] = getter(r)
                except Exception:
                    row_out[out_col] = None
            out.append(row_out)
        return pd.DataFrame(out)

    def _details_enabled(key, label="Load drill-down details"):
        st.caption(label)
        return True

    def _pretty_field_name(name):
        return str(name).replace("_", " ").strip().title()

    def _render_readable_record(record, key_prefix):
        if not isinstance(record, dict):
            st.write(record)
            return

        scalar_rows = []
        list_rows = []
        nested_rows = []
        for k, v in record.items():
            if k in ("raw_event",):
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                scalar_rows.append((_pretty_field_name(k), v))
            elif isinstance(v, list):
                list_rows.append((k, v))
            elif isinstance(v, dict):
                nested_rows.append((k, v))

        if scalar_rows:
            scalar_df = pd.DataFrame(
                [{"Field": k, "Value": ("" if v is None else v)} for k, v in scalar_rows]
            )
            _safe_dataframe(scalar_df, width="stretch", hide_index=True)

        for k, v in list_rows:
            label = _pretty_field_name(k)
            st.markdown(f"**{label}**")
            if not v:
                st.caption("None")
                continue
            if all(not isinstance(item, dict) for item in v):
                list_df = pd.DataFrame({label: [str(item) for item in v]})
                _show_df_limited(list_df, key=f"{key_prefix}_{k}", default_limit=250)
            else:
                dict_rows = [item for item in v if isinstance(item, dict)]
                if dict_rows:
                    _show_df_limited(pd.DataFrame(dict_rows), key=f"{key_prefix}_{k}", default_limit=100)
                else:
                    st.caption("Complex list data available.")

        for k, v in nested_rows:
            label = _pretty_field_name(k)
            st.markdown(f"**{label}**")
            nested_scalars = {kk: vv for kk, vv in v.items() if not isinstance(vv, (dict, list))}
            if nested_scalars:
                nested_df = pd.DataFrame(
                    [{"Field": _pretty_field_name(kk), "Value": ("" if vv is None else vv)} for kk, vv in nested_scalars.items()]
                )
                _safe_dataframe(nested_df, width="stretch", hide_index=True)
            else:
                st.caption("Nested structured data available.")

    def _render_deep_drilldown(rows, label_getter, key, empty_msg="No records available for deeper drill-down."):
        if not rows:
            st.caption(empty_msg)
            return None
        labels = []
        for i, row in enumerate(rows):
            try:
                label = label_getter(row)
            except Exception:
                label = None
            label = str(label).strip() if label is not None else ""
            if not label:
                label = f"Record {i + 1}"
            labels.append(label)
        selected_idx = st.selectbox(
            "Select a row for more detail",
            list(range(len(rows))),
            key=key,
            format_func=lambda idx: labels[idx],
        )
        st.caption(f"Selected: {labels[selected_idx]}")
        selected = _sanitize_record_for_role(rows[selected_idx])
        _render_readable_record(selected, key_prefix=f"{key}_record")
        with st.expander("Technical View (JSON)"):
            st.json(selected, expanded=False)
        return selected
    

    if not show_global_only_kpis:
        st.info("Income & Funding and Communications & Profile are now tracked as global-only KPIs and are shown only when the region filter is set to Global.")

    # --- A. Governance ---
    if active_section == "Governance":
        st.header("Governance & Infrastructure")
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.popover(
                f"Steering Group Active\n{'Yes' if data['governance']['steering_group_active'] else 'No'}",
                width="stretch",
            ):
                st.caption("Derived from steering volunteer tags in current filtered data.")
                if _details_enabled("lazy_gov_steering_active"):
                    _render_deep_drilldown(
                        raw_kpi.get("steering_volunteers") or [],
                        lambda r: _get_row_value(r, "name", "full_name", "Display Name", "email") or r.get("id"),
                        key="dd_gov_steering_active",
                        empty_msg="No steering source rows found for deeper drill-down.",
                    )
        with c2:
            with st.popover(
                f"Active Volunteers\n{data['governance']['steering_members']}",
                width="stretch",
            ):
                if _details_enabled("lazy_gov_steering_members"):
                    steering_df = _rows_to_df(
                        raw_kpi.get("steering_volunteers") or [],
                        {
                            "Name": lambda r: _get_row_value(r, "name", "full_name", "Display Name", "email") or r.get("id"),
                            "Type": lambda r: ", ".join(_to_list(r.get("type"))),
                            "Region": lambda r: ", ".join(_to_list(r.get("c_region"))),
                            "Created": lambda r: r.get("created_at"),
                        },
                    )
                    if steering_df.empty:
                        st.caption("No steering-tagged volunteers found; this metric may use volunteer proxy logic.")
                    else:
                        _show_df_limited(steering_df, key="tbl_gov_steering_members")
                    _render_deep_drilldown(
                        raw_kpi.get("steering_volunteers") or [],
                        lambda r: _get_row_value(r, "name", "full_name", "Display Name", "email") or r.get("id"),
                        key="dd_gov_steering_members",
                        empty_msg="No steering source rows found for deeper drill-down.",
                    )
        with c3:
            with st.popover(
                f"New Volunteers\n{data['governance']['volunteers_new']}",
                width="stretch",
            ):
                if _details_enabled("lazy_gov_new_volunteers"):
                    volunteers_df = _rows_to_df(
                        raw_kpi.get("volunteers") or [],
                        {
                            "Name": lambda r: _get_row_value(r, "name", "full_name", "Display Name", "email") or r.get("id"),
                            "Type": lambda r: ", ".join(_to_list(r.get("type"))),
                            "Region": lambda r: ", ".join(_to_list(r.get("c_region"))),
                            "Created": lambda r: r.get("created_at"),
                        },
                    )
                    if volunteers_df.empty:
                        st.caption("No volunteer rows found for this selection.")
                    else:
                        _show_df_limited(volunteers_df, key="tbl_gov_new_volunteers")
                    _render_deep_drilldown(
                        raw_kpi.get("volunteers") or [],
                        lambda r: _get_row_value(r, "name", "full_name", "Display Name", "email") or r.get("id"),
                        key="dd_gov_new_volunteers",
                        empty_msg="No volunteer source rows found for deeper drill-down.",
                    )
        st.caption("Click a metric above to open its drill-down popup.")

    # --- B. Partnerships ---
    if active_section == "Partnerships":
        st.header("Partnerships & Influence")
        data_lsp = [{"Sector": k, "Count": v, "Type": "Strategic (LSP)"} for k, v in data['partnerships']['LSP'].items()]
        data_ldp = [{"Sector": k, "Count": v, "Type": "Delivery (LDP)"} for k, v in data['partnerships']['LDP'].items()]
        
        if not data_lsp and not data_ldp:
            st.info("No Organisation data found for this region.")
        else:
            st.caption("Charts are disabled on KPI Dashboard. Use Custom Reports Dashboard for charts.")
        
        c1, c2 = st.columns(2)
        with c1:
            with st.popover(
                f"Active Orgs in Region\n{data['partnerships']['active_referrals']}",
                width="stretch",
            ):
                st.markdown("**List of Organisations**")
                if _details_enabled("lazy_part_active_orgs"):
                    org_df = _rows_to_df(
                        raw_kpi.get("region_orgs") or [],
                        {
                            "Organisation": lambda r: _get_row_value(r, "name", "Organisation", "Organization", "Display Name") or r.get("id"),
                            "Type": lambda r: str(r.get("type") or ""),
                            "Region": lambda r: ", ".join(_to_list(r.get("c_region"))),
                            "Created": lambda r: r.get("created_at"),
                        },
                    )
                    if org_df.empty:
                        st.caption("No organisation rows found for this selection.")
                    else:
                        _show_df_limited(org_df, key="tbl_part_active_orgs")
                    _render_deep_drilldown(
                        raw_kpi.get("region_orgs") or [],
                        lambda r: _get_row_value(r, "name", "Organisation", "Organization", "Display Name") or r.get("id"),
                        key="dd_part_active_orgs",
                        empty_msg="No organisation source rows found for deeper drill-down.",
                    )
        with c2:
            with st.popover(
                f"Network Memberships\n{data['partnerships']['networks_sat_on']}",
                width="stretch",
            ):
                st.markdown("**Network Memberships**")
                st.caption("No direct source field is currently mapped for this metric.")
                st.caption("No deeper drill-down source rows are mapped for this metric yet.")
        st.caption("Click a metric above to open its drill-down popup.")

    # --- C. Delivery ---
    if active_section == "Delivery":
        st.header("Delivery, Reach & Impact")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            with st.popover(
                f"Events\n{data['delivery']['walks_delivered']}",
                width="stretch",
            ):
                st.markdown("**List of Attendees by Event**")
                if _details_enabled("lazy_del_events"):
                    delivery_events = raw_kpi.get("delivery_events") or []
                    attendees_rows = []
                    for e in delivery_events:
                        attendees_rows.append({
                            "Event": _get_row_value(e, "name", "title", "event_name", "Display Name") or e.get("id"),
                            "Date": _get_row_value(e, "start_date", "date", "created_at"),
                            "Attendees": _coerce_int(_get_row_value(e, "number_of_attendees", "Number of attendees", "attendees", "participant_count")),
                        })
                    attendees_df = pd.DataFrame(attendees_rows)
                    if attendees_df.empty:
                        st.caption("No event rows found for this selection.")
                    else:
                        _show_df_limited(attendees_df, key="tbl_del_events")
                    _render_deep_drilldown(
                        delivery_events,
                        lambda r: _get_row_value(r, "name", "title", "event_name", "Display Name") or r.get("id"),
                        key="dd_del_events",
                        empty_msg="No event source rows found for deeper drill-down.",
                    )
        with m2:
            with st.popover(
                f"Total Participants\n{data['delivery']['participants']}",
                width="stretch",
            ):
                if _details_enabled("lazy_del_participants"):
                    delivery_events = raw_kpi.get("delivery_events") or []
                    delivery_df = pd.DataFrame(delivery_events)
                    if delivery_df.empty:
                        st.caption("No delivery-tagged event rows found for this filtered period.")
                    else:
                        _show_df_limited(delivery_df, key="tbl_del_participants")
                    selected_event = _render_deep_drilldown(
                        delivery_events,
                        lambda r: _get_row_value(r, "name", "title", "event_name", "Display Name") or r.get("id"),
                        key="dd_del_participants",
                        empty_msg="No event source rows found for deeper drill-down.",
                    )
                    if selected_event:
                        can_view_attendee_details = _can_view_event_attendee_details()
                        participant_list = selected_event.get("participant_list") or []
                        participant_ids = selected_event.get("participant_ids") or []
                        participant_count = _coerce_int(selected_event.get("participants"))
                        if can_view_attendee_details and not participant_list:
                            with st.spinner("Checking live attendee feed for this event..."):
                                live = fetch_live_event_attendees(selected_event.get("id"))
                            if live.get("names"):
                                participant_list = live.get("names") or []
                                participant_ids = (participant_ids or []) + (live.get("ids") or [])
                                endpoint_used = live.get("endpoint")
                                if endpoint_used:
                                    st.caption(f"Live attendee source used: {endpoint_used}")
                        if not can_view_attendee_details:
                            participant_list = []
                            participant_ids = []
                        attendee_status = "Count only (no attendee names available)"
                        if participant_list:
                            attendee_status = "Attendee names available"
                        elif participant_ids:
                            attendee_status = "Attendee IDs available (names unavailable)"
                        st.caption(f"Attendee source status: {attendee_status}")
                        st.markdown("**Participants in selected event**")
                        if participant_list:
                            participants_df = pd.DataFrame({"Participant": participant_list})
                            _show_df_limited(participants_df, key="tbl_del_participants_list", default_limit=250)
                        elif participant_ids:
                            ids_df = pd.DataFrame({"Participant ID": participant_ids})
                            _show_df_limited(ids_df, key="tbl_del_participants_ids", default_limit=250)
                            st.caption("Participant IDs found but names are not available in the current source rows.")
                        elif participant_count > 0:
                            if can_view_attendee_details:
                                placeholder_rows = [f"Participant {i} (name unavailable)" for i in range(1, participant_count + 1)]
                                placeholder_df = pd.DataFrame({"Participant": placeholder_rows})
                                _show_df_limited(placeholder_df, key="tbl_del_participants_placeholder", default_limit=250)
                                st.caption("Names are not included in current event source rows. Showing participant count placeholders.")
                            else:
                                st.metric("Total Attendees", participant_count)
                                st.caption("Your role can view attendee totals only.")
                        else:
                            st.caption("No participant names are available for this event in the current source data.")
        with m3:
            with st.popover(
                f"Bursary Participants\n{data['delivery']['bursary_participants']}",
                width="stretch",
            ):
                st.caption("No raw source fields are currently mapped for this metric in Beacon.")
                st.caption("No deeper drill-down source rows are mapped for this metric yet.")
        with m4:
            with st.popover(
                f"Avg Wellbeing Change\n+{data['delivery']['wellbeing_change_score']}",
                width="stretch",
            ):
                st.caption("No raw source fields are currently mapped for this metric in Beacon.")
                st.caption("No deeper drill-down source rows are mapped for this metric yet.")
        
        st.subheader("Demographics")
        df_demo = pd.DataFrame(list(data['delivery']['demographics'].items()), columns=['Group', 'Count'])
        demo_source = (data.get("delivery") or {}).get("demographics_source", "fallback")
        st.caption("Charts are disabled on KPI Dashboard. Use Custom Reports Dashboard for charts.")
        _safe_dataframe(df_demo, width="stretch", hide_index=True)
        if demo_source == "event_attendee_gender":
            st.caption("Demographics shown from attendee Gender values synced from Beacon and normalized into dashboard groupings.")
        elif demo_source == "people_type_tags":
            st.caption("Demographics shown from existing people type tags in the filtered region/timeframe.")
        elif demo_source == "event_type_split":
            st.caption("No participant cohort tags found; chart falls back to event type split.")
        else:
            st.caption("Limited demographic fields currently available; chart uses fallback data.")
        st.caption("Click a metric above to open its drill-down popup.")

    # --- D. Income ---
    if show_global_only_kpis and active_section == "Income":
            st.header("Income & Funding")
            c1, c2 = st.columns(2)
            with c1:
                with st.popover(
                    f"Total Funds Raised\n£{data['income']['total_funds_raised']:,.2f}",
                    width="stretch",
                ):
                    if _details_enabled("lazy_inc_total_funds"):
                        payment_rows = []
                        for p in raw_kpi.get("region_payments") or []:
                            payment_rows.append({
                                "Source": "Payments",
                                "When": p.get("payment_date") or p.get("date") or p.get("created_at"),
                                "From": _get_row_value(p, "description", "name", "reference") or p.get("id"),
                                "Amount": _coerce_money(_get_row_value(p, "amount", "value", "total")),
                                "Status": _get_row_value(p, "status", "payment_status", "Payment Status") or "",
                            })
                        grant_rows = []
                        for g in raw_kpi.get("region_grants") or []:
                            grant_rows.append({
                                "Source": "Grants",
                                "When": g.get("close_date") or g.get("award_date") or g.get("created_at"),
                                "From": _get_row_value(g, "name", "title", "description") or g.get("id"),
                                "Amount": _coerce_money(_get_row_value(g, "amount", "amount_granted", "value")),
                                "Status": _get_row_value(g, "stage", "status", "Stage", "Status") or "",
                            })
                        funds_df = pd.DataFrame(payment_rows + grant_rows)
                        if funds_df.empty:
                            st.caption("No payment or grant rows found for this filtered period.")
                        else:
                            _show_df_limited(funds_df.sort_values("When", ascending=False), key="tbl_inc_total_funds")
                        _render_deep_drilldown(
                            payment_rows + grant_rows,
                            lambda r: f"{r.get('Source', '')} - {r.get('From', '')}",
                            key="dd_inc_total_funds",
                            empty_msg="No payment or grant source rows found for deeper drill-down.",
                        )
                with st.popover(
                    f"In-Kind Value\n£{data['income']['in_kind_value']:,}",
                    width="stretch",
                ):
                    st.caption("No raw source field is currently mapped for this metric.")
                    st.caption("No deeper drill-down source rows are mapped for this metric yet.")
            with c2:
                with st.popover(
                    f"Bids Submitted\n{data['income']['bids_submitted']}",
                    width="stretch",
                ):
                    if _details_enabled("lazy_inc_bids"):
                        grant_rows = []
                        for g in raw_kpi.get("region_grants") or []:
                            grant_rows.append({
                                "Source": "Grants",
                                "When": g.get("close_date") or g.get("award_date") or g.get("created_at"),
                                "From": _get_row_value(g, "name", "title", "description") or g.get("id"),
                                "Amount": _coerce_money(_get_row_value(g, "amount", "amount_granted", "value")),
                                "Status": _get_row_value(g, "stage", "status", "Stage", "Status") or "",
                            })
                        bids_rows = [r for r in grant_rows if any(x in str(r.get("Status", "")).lower() for x in ["submitted", "review", "pending"])]
                        bids_df = pd.DataFrame(bids_rows)
                        if bids_df.empty:
                            st.caption("No bid rows found for this filtered period.")
                        else:
                            _show_df_limited(bids_df, key="tbl_inc_bids")
                        _render_deep_drilldown(
                            bids_rows,
                            lambda r: f"{r.get('From', '')} ({r.get('Status', '')})",
                            key="dd_inc_bids",
                            empty_msg="No bid source rows found for deeper drill-down.",
                        )
                with st.popover(
                    f"Corporate Partners\n{data['income']['corporate_partners']}",
                    width="stretch",
                ):
                    if _details_enabled("lazy_inc_corp"):
                        corp_rows = raw_kpi.get("corporate_orgs") or []
                        corp_df = _rows_to_df(
                            corp_rows,
                            {
                                "Organisation": lambda r: _get_row_value(r, "name", "Organisation", "Organization", "Display Name") or r.get("id"),
                                "Type": lambda r: str(r.get("type") or ""),
                                "Region": lambda r: ", ".join(_to_list(r.get("c_region"))),
                                "Created": lambda r: r.get("created_at"),
                            },
                        )
                        if corp_df.empty:
                            st.caption("No corporate partner rows found for this filtered period.")
                        else:
                            _show_df_limited(corp_df, key="tbl_inc_corp")
                        _render_deep_drilldown(
                            corp_rows,
                            lambda r: _get_row_value(r, "name", "Organisation", "Organization", "Display Name") or r.get("id"),
                            key="dd_inc_corp",
                            empty_msg="No corporate partner source rows found for deeper drill-down.",
                        )
            st.caption("Click a metric above to open its drill-down popup.")

            st.subheader("Income Over Time")
            raw_income = (data.get("_raw_income") or {})
            payments = raw_income.get("payments") or []
            grants = raw_income.get("grants") or []

            def _to_float(val):
                return _coerce_money(val)

            rows = []
            for p in payments:
                rows.append({
                    "date": p.get("payment_date"),
                    "amount": _to_float(p.get("amount")),
                    "source": "Payments"
                })
            for g in grants:
                rows.append({
                    "date": g.get("close_date"),
                    "amount": _to_float(g.get("amount")),
                    "source": "Grants"
                })

            if rows:
                df_income = pd.DataFrame(rows)
                df_income["date"] = pd.to_datetime(df_income["date"], errors="coerce")
                df_income = df_income.dropna(subset=["date"])

                if not df_income.empty:
                    # Choose grouping based on timeframe selection
                    if timeframe == "Week":
                        freq = "D"
                        title = "Daily Income (Week)"
                    elif timeframe == "Month":
                        freq = "D"
                        title = "Daily Income (Month)"
                    elif timeframe == "Quarter":
                        freq = "W-MON"
                        title = "Weekly Income (Quarter)"
                    elif timeframe == "Year":
                        freq = "ME"
                        title = "Monthly Income (Year)"
                    elif timeframe == "Custom Range" and start_date and end_date:
                        days = (end_date.date() - start_date.date()).days
                        if days <= 31:
                            freq = "D"
                            title = "Daily Income (Custom Range)"
                        else:
                            freq = "W-MON"
                            title = "Weekly Income (Custom Range)"
                    else:
                        freq = "ME"
                        title = "Monthly Income (All Time)"

                    df_income = df_income.groupby([pd.Grouper(key="date", freq=freq), "source"], as_index=False)["amount"].sum()
                    st.caption("Charts are disabled on KPI Dashboard. Use Custom Reports Dashboard for charts.")
                    _safe_dataframe(df_income.sort_values("date", ascending=False), width="stretch", hide_index=True)
                else:
                    st.info("No dated income records found for this period.")
            else:
                st.info("No income records found for this period.")

        # --- E. Comms ---
    if show_global_only_kpis and active_section == "Comms":
            st.header("Communications & Profile")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                with st.popover(f"Press Releases\n{data['comms']['press_releases']}", width="stretch"):
                    st.caption("Comms metrics are currently placeholders and not yet connected to raw source rows.")
            with c2:
                with st.popover(f"Media Coverage\n{data['comms']['media_coverage']}", width="stretch"):
                    st.caption("Comms metrics are currently placeholders and not yet connected to raw source rows.")
            with c3:
                with st.popover(f"Newsletters Sent\n{data['comms']['newsletters_sent']}", width="stretch"):
                    st.caption("Comms metrics are currently placeholders and not yet connected to raw source rows.")
            with c4:
                with st.popover(f"Open Rate\n{data['comms']['open_rate']}%", width="stretch"):
                    st.caption("Comms metrics are currently placeholders and not yet connected to raw source rows.")
            st.caption("Click a metric above to open its drill-down popup.")

    # --- CASE STUDIES ---
    if active_section == "Case Studies":
        case_studies_page(
            allow_upload=False,
            start_date=start_date,
            end_date=end_date,
            region_override=region_val
        )

def case_studies_page(allow_upload=True, start_date=None, end_date=None, region_override=None):
    st.header("Case Studies & Reviews")
    if st.session_state.get("case_study_saved"):
        import random
        variants = [
            "Case study saved. Mind Over Mountains is transforming lives through the outdoors.",
            "Case study saved. Another step forward for mental health with Mind Over Mountains.",
            "Case study saved. This is the impact Mind Over Mountains makes every day.",
            "Case study saved. Proof that Mind Over Mountains is changing lives for the better.",
            "Case study saved. Real stories of hope powered by Mind Over Mountains.",
            "Case study saved. Positive change and stronger wellbeing with Mind Over Mountains.",
            "Case study saved. A reminder of the incredible work Mind Over Mountains delivers.",
        ]
        message = random.choice(variants)
        import streamlit.components.v1 as components
        fireworks_html = """
        <html>
        <body style="margin:0;background:transparent;overflow:hidden;">
          <canvas id="fw"></canvas>
          <script>
          const iframe = window.frameElement;
          if (iframe) {
            iframe.style.position = 'fixed';
            iframe.style.top = '0';
            iframe.style.left = '0';
            iframe.style.width = '100vw';
            iframe.style.height = '100vh';
            iframe.style.zIndex = '9999';
            iframe.style.pointerEvents = 'none';
            iframe.style.border = '0';
          }
          const canvas = document.getElementById('fw');
          const ctx = canvas.getContext('2d');
          function resize(){
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
          }
          resize(); window.addEventListener('resize', resize);
          const colors = ['#00f5d4','#7bff6b','#ff9f1c','#ff3d7f','#5a4dff','#ffd166'];
          const fireworks = [];
          function spawn(){
            const x = Math.random()*canvas.width*0.8 + canvas.width*0.1;
            const y = Math.random()*canvas.height*0.5 + canvas.height*0.1;
            const particles = [];
            for(let i=0;i<120;i++){
              const angle = Math.random()*Math.PI*2;
              const speed = Math.random()*7 + 2;
              particles.push({
                x,y,
                vx: Math.cos(angle)*speed,
                vy: Math.sin(angle)*speed,
                life: Math.random()*60+40,
                color: colors[(Math.random()*colors.length)|0]
              });
            }
            fireworks.push(particles);
          }
          let last = 0;
          function animate(ts){
            if(ts - last > 160){ spawn(); last = ts; }
            ctx.clearRect(0,0,canvas.width,canvas.height);
            for(let f=fireworks.length-1; f>=0; f--){
              const particles = fireworks[f];
              for(let p=particles.length-1; p>=0; p--){
                const part = particles[p];
                part.x += part.vx;
                part.y += part.vy;
                part.vy += 0.05;
                part.life -= 1;
                ctx.fillStyle = part.color;
                ctx.fillRect(part.x, part.y, 3, 3);
                if(part.life <= 0) particles.splice(p,1);
              }
              if(particles.length === 0) fireworks.splice(f,1);
            }
            requestAnimationFrame(animate);
          }
          requestAnimationFrame(animate);
          setTimeout(()=>{ if(iframe) iframe.style.display = 'none'; }, 4500);
          </script>
        </body>
        </html>
        """
        components.html(fireworks_html, height=10, scrolling=False)
        st.markdown(
            f"<div class='overlay-message'>{message}</div>",
            unsafe_allow_html=True
        )
        st.session_state["case_study_saved"] = False
    if allow_upload:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        # Add new
        with st.expander("Upload New Case Study"):
            with st.form("case_study_form"):
                cs_title = st.text_input("Title")
                cs_content = st.text_area("Story / Testimonial")
                cs_date = st.date_input("Case Study Date", value=datetime.now().date())
                cs_region = st.selectbox(
                    "Region",
                    ["North of England", "South of England", "Midlands", "Wales", "Global", "Other"]
                )
                cs_submitted = st.form_submit_button("Submit Case Study")
                
                if cs_submitted:
                    if cs_title and cs_content:
                        add_case_study(cs_title, cs_content, cs_region, cs_date)
                        st.session_state["case_study_saved"] = True
                        st.rerun()
                    else:
                        st.error("Please provide both a title and content.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    # Display Studies (Filtered by Region or All Regions)
    role = st.session_state.get("role")
    view_region = region_override or st.session_state.get("region", "Global")
    if region_override is None and role in ["Admin", "Manager", "RPL", "ML"]:
        st.sidebar.markdown("### Case Studies Region")
        case_all_regions = st.sidebar.checkbox(
            "All Regions",
            value=(str(view_region) == "Global"),
            key="case_studies_all_regions",
        )
        if case_all_regions:
            view_region = "Global"
        else:
            region_options = ["North of England", "South of England", "Midlands", "Wales", "Other"]
            default_index = region_options.index(view_region) if view_region in region_options else 0
            view_region = st.sidebar.selectbox(
                "Region",
                region_options,
                index=default_index,
                key="case_studies_region_select",
            )
        st.sidebar.caption(f"Case Studies Region: {view_region}")

    if view_region == "Global" and role in ["Admin", "Manager", "RPL", "ML"]:
        display_studies = get_case_studies(None, start_date=start_date, end_date=end_date)
    else:
        display_studies = get_case_studies(view_region, start_date=start_date, end_date=end_date)

    if display_studies:
        # Sort by date added (oldest -> newest)
        display_studies.sort(key=lambda x: x.get('date_added', ''), reverse=False)
        for study in display_studies:
            with st.container():
                st.markdown(f"#### {study['title']}")
                st.caption(f"Date: {study.get('date_added','')} | Region: {study.get('region','')}")
                st.info(study['content'])
    else:
        st.write("No case studies found.")
    st.markdown("</div>", unsafe_allow_html=True)

def _normalize_email_list(values):
    if not values:
        return []
    out = []
    seen = set()
    for v in values:
        e = str(v).strip().lower()
        if not e or e in seen:
            continue
        seen.add(e)
        out.append(e)
    return out

def save_custom_report(report_name, config, shared_with):
    report_id = uuid.uuid4().hex[:12]
    details = {
        "source": "custom_reports",
        "report_id": report_id,
        "report_name": (report_name or "").strip() or "Untitled Report",
        "owner_email": st.session_state.get("email", "").strip().lower(),
        "shared_with": _normalize_email_list(shared_with),
        "config": config or {},
    }
    log_audit_event("Custom Report Saved", details)
    get_accessible_custom_reports.clear()
    return report_id

def update_custom_report_sharing(report_id, report_name, shared_with):
    details = {
        "source": "custom_reports",
        "report_id": report_id,
        "report_name": report_name,
        "owner_email": st.session_state.get("email", "").strip().lower(),
        "shared_with": _normalize_email_list(shared_with),
    }
    log_audit_event("Custom Report Share Updated", details)
    get_accessible_custom_reports.clear()

@st.cache_data(show_spinner=False, ttl=60)
def get_accessible_custom_reports(user_email):
    if DB_TYPE != 'supabase':
        return []
    email = (user_email or "").strip().lower()
    if not email:
        return []
    try:
        resp = (
            DB_CLIENT.table("audit_logs")
            .select("created_at, action, details")
            .in_("action", ["Custom Report Saved", "Custom Report Share Updated"])
            .order("created_at", desc=False)
            .limit(1000)
            .execute()
        )
        rows = resp.data or []
    except Exception:
        return []

    reports = {}
    for row in rows:
        details = row.get("details") or {}
        if details.get("source") != "custom_reports":
            continue
        report_id = details.get("report_id")
        if not report_id:
            continue
        rep = reports.get(report_id, {})
        rep["report_id"] = report_id
        rep["name"] = details.get("report_name") or rep.get("name") or "Untitled Report"
        rep["owner_email"] = str(details.get("owner_email") or rep.get("owner_email") or "").strip().lower()
        rep["shared_with"] = _normalize_email_list(details.get("shared_with") or rep.get("shared_with") or [])
        if row.get("action") == "Custom Report Saved":
            rep["config"] = details.get("config") or rep.get("config") or {}
            if not rep.get("created_at"):
                rep["created_at"] = row.get("created_at")
        rep["updated_at"] = row.get("created_at")
        reports[report_id] = rep

    accessible = []
    for rep in reports.values():
        if rep.get("owner_email") == email or email in rep.get("shared_with", []):
            accessible.append(rep)
    accessible.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return accessible

@st.cache_data(show_spinner=False, ttl=300)
def fetch_custom_report_data(dataset_key, start_date=None, end_date=None):
    if DB_TYPE != 'supabase':
        return pd.DataFrame()

    config = {
        "People": {"table": "beacon_people", "date_col": "created_at", "select_cols": "payload, created_at"},
        "Organisations": {"table": "beacon_organisations", "date_col": "created_at", "select_cols": "payload, created_at"},
        "Events": {"table": "beacon_events", "date_col": "start_date", "select_cols": "payload, start_date, region"},
        "Payments": {"table": "beacon_payments", "date_col": "payment_date", "select_cols": "payload, payment_date"},
        "Grants": {"table": "beacon_grants", "date_col": "close_date", "select_cols": "payload, close_date"},
    }
    cfg = config.get(dataset_key)
    if not cfg:
        return pd.DataFrame()

    rows = []
    offset = 0
    batch_size = 1000
    while True:
        q = DB_CLIENT.table(cfg["table"]).select(cfg["select_cols"]).range(offset, offset + batch_size - 1)
        if start_date:
            q = q.gte(cfg["date_col"], start_date.isoformat())
        if end_date:
            q = q.lte(cfg["date_col"], end_date.isoformat())
        chunk = q.execute().data or []
        rows.extend(chunk)
        if len(chunk) < batch_size:
            break
        offset += batch_size

    flattened = []
    for row in rows:
        payload = row.get("payload") or {}
        date_val = (
            row.get(cfg["date_col"])
            or payload.get(cfg["date_col"])
            or payload.get("created_at")
            or payload.get("date")
        )
        region_tags = _to_list(payload.get("c_region"))
        region_name = (
            (region_tags[0] if region_tags else None)
            or row.get("region")
            or payload.get("region")
            or _get_row_value(payload, "Location (region)", "Location Region", "Region")
            or "Other"
        )

        item = {
            "dataset": dataset_key,
            "record_id": payload.get("id") or row.get("id"),
            "date": date_val,
            "region": str(region_name).strip() if region_name else "Other",
            "category": "",
            "label": "",
            "status": "",
            "metric_value": 0.0,
            "record_count": 1,
        }

        if dataset_key == "People":
            types = _to_list(payload.get("type"))
            item["category"] = ", ".join(types) if types else "Unknown"
            item["label"] = str(
                _get_row_value(payload, "name", "full_name", "Name", "Display Name", "email")
                or payload.get("id")
                or "Person"
            )
            item["metric_value"] = 1.0
        elif dataset_key == "Organisations":
            item["category"] = str(_get_row_value(payload, "type", "Organisation type", "Organization type", "Category") or "Unknown")
            item["label"] = str(_get_row_value(payload, "name", "Organisation", "Organization", "Display Name") or payload.get("id") or "Organisation")
            item["metric_value"] = 1.0
        elif dataset_key == "Events":
            item["category"] = str(_get_row_value(payload, "type", "Event type", "Activity type", "Category") or "Event")
            item["label"] = str(_get_row_value(payload, "name", "title", "Event name", "Description") or payload.get("id") or "Event")
            item["metric_value"] = float(
                _get_row_value(
                    payload,
                    "number_of_attendees",
                    "Number of attendees",
                    "Attendees",
                    "Participants",
                    "Participant count",
                ) or 0
            )
        elif dataset_key == "Payments":
            item["category"] = str(_get_row_value(payload, "type", "Payment type", "Category") or "Payment")
            item["label"] = str(_get_row_value(payload, "description", "Name", "Payment", "Reference") or payload.get("id") or "Payment")
            item["status"] = str(_get_row_value(payload, "status", "payment_status", "Payment Status") or "")
            item["metric_value"] = _coerce_money(_get_row_value(payload, "amount", "value", "total", "Amount", "Value"))
        elif dataset_key == "Grants":
            item["category"] = str(_get_row_value(payload, "type", "Category", "Grant type") or "Grant")
            item["label"] = str(_get_row_value(payload, "name", "title", "Grant", "Description") or payload.get("id") or "Grant")
            item["status"] = str(_get_row_value(payload, "stage", "status", "Stage", "Status") or "")
            item["metric_value"] = _coerce_money(_get_row_value(payload, "amount", "amount_granted", "value", "Amount", "Value"))

        flattened.append(item)

    df = pd.DataFrame(flattened)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce").fillna(0.0)
    df["month"] = df["date"].dt.tz_localize(None).dt.to_period("M").astype(str)
    return df

def custom_reports_dashboard():
    st.title("Custom Reports Dashboard")
    st.caption("Build custom reports with table, pie, bar, line, UK map, and comparison analysis outputs.")

    if DB_TYPE != 'supabase':
        st.info("Custom reports are available only in Supabase mode.")
        return

    st.sidebar.markdown("### Report Filters")
    dataset_choices = ["People", "Organisations", "Events", "Payments", "Grants"]
    selected_datasets = st.sidebar.multiselect(
        "Datasets",
        dataset_choices,
        default=["Events", "Payments"],
        key="reports_datasets"
    )
    report_type = st.sidebar.selectbox(
        "Output Type",
        ["Tabular", "Bar", "Line", "Pie", "UK Map", "Comparison Analysis", "Distance Analysis"],
        key="reports_output_type"
    )

    role = st.session_state.get('role')
    default_region = st.session_state.get('region') or "Global"
    if role in ["Admin", "Manager", "RPL", "ML"]:
        all_regions = st.sidebar.checkbox("All Regions", value=True, key="reports_all_regions")
        if all_regions:
            region_val = "Global"
        else:
            region_options = ["North of England", "South of England", "Midlands", "Wales", "Other"]
            idx = region_options.index(default_region) if default_region in region_options else 0
            region_val = st.sidebar.selectbox("Region", region_options, index=idx, key="reports_region")
    else:
        region_val = default_region
    st.sidebar.caption(f"Region: {region_val}")

    timeframe, start_date, end_date = get_time_filters()
    current_filters = {
        "selected_datasets": list(selected_datasets or []),
        "report_type": report_type,
        "region_val": region_val,
        "timeframe": timeframe,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }
    apply_filters = st.sidebar.button("Apply Report Filters", key="reports_apply_filters")
    if apply_filters or "reports_applied_filters" not in st.session_state:
        st.session_state["reports_applied_filters"] = current_filters

    applied_filters = st.session_state.get("reports_applied_filters", current_filters)
    filters_dirty = applied_filters != current_filters
    if filters_dirty:
        st.sidebar.caption("Filters changed. Click Apply Report Filters to refresh the report.")

    selected_datasets = applied_filters.get("selected_datasets") or []
    report_type = applied_filters.get("report_type") or report_type
    region_val = applied_filters.get("region_val") or region_val
    timeframe = applied_filters.get("timeframe") or timeframe
    start_date = pd.to_datetime(applied_filters.get("start_date")) if applied_filters.get("start_date") else None
    end_date = pd.to_datetime(applied_filters.get("end_date")) if applied_filters.get("end_date") else None

    if not selected_datasets:
        st.warning("Select at least one dataset.")
        return

    frames = []
    for ds in selected_datasets:
        frames.append(fetch_custom_report_data(ds, start_date=start_date, end_date=end_date))
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        st.warning("No report data found for the selected filters.")
        return

    if region_val != "Global":
        df = df[df["region"].astype(str).str.lower().str.contains(region_val.lower(), na=False)]
    if df.empty:
        st.warning("No records found for the selected region/date filters.")
        return

    df = df.copy()
    with st.sidebar.expander("Advanced Report Controls", expanded=False):
        dataset_filter = st.multiselect(
            "Limit to datasets",
            sorted(df["dataset"].dropna().astype(str).unique().tolist()),
            default=[],
            key="reports_dataset_filter"
        )
        category_filter = st.multiselect(
            "Category filter",
            sorted([v for v in df["category"].dropna().astype(str).unique().tolist() if v and v != "nan"])[:200],
            default=[],
            key="reports_category_filter"
        )
        status_filter = st.multiselect(
            "Status filter",
            sorted([v for v in df["status"].dropna().astype(str).unique().tolist() if v and v != "nan"])[:200],
            default=[],
            key="reports_status_filter"
        )
        min_value = float(df["metric_value"].min()) if not df.empty else 0.0
        max_value = float(df["metric_value"].max()) if not df.empty else 0.0
        if max_value <= min_value:
            value_range = (min_value, max_value)
            st.caption(f"Metric value range fixed at {min_value:,.2f} because all rows share the same value.")
        else:
            value_range = st.slider(
                "Metric value range",
                min_value=min_value,
                max_value=max_value,
                value=(min_value, max_value),
                key="reports_value_range"
            )
        require_date = st.checkbox("Only include rows with valid date", value=False, key="reports_require_date")

    current_advanced_filters = {
        "dataset_filter": list(dataset_filter or []),
        "category_filter": list(category_filter or []),
        "status_filter": list(status_filter or []),
        "value_range": tuple(value_range),
        "require_date": bool(require_date),
    }
    apply_advanced = st.sidebar.button("Apply Advanced Filters", key="reports_apply_advanced_filters")
    if apply_advanced or "reports_applied_advanced_filters" not in st.session_state:
        st.session_state["reports_applied_advanced_filters"] = current_advanced_filters

    applied_advanced_filters = st.session_state.get("reports_applied_advanced_filters", current_advanced_filters)
    if applied_advanced_filters != current_advanced_filters:
        st.sidebar.caption("Advanced filters changed. Click Apply Advanced Filters to update the results.")

    dataset_filter = applied_advanced_filters.get("dataset_filter") or []
    category_filter = applied_advanced_filters.get("category_filter") or []
    status_filter = applied_advanced_filters.get("status_filter") or []
    value_range = tuple(applied_advanced_filters.get("value_range") or value_range)
    require_date = bool(applied_advanced_filters.get("require_date"))

    if dataset_filter:
        df = df[df["dataset"].astype(str).isin(dataset_filter)]
    if category_filter:
        df = df[df["category"].astype(str).isin(category_filter)]
    if status_filter:
        df = df[df["status"].astype(str).isin(status_filter)]
    df = df[(df["metric_value"] >= value_range[0]) & (df["metric_value"] <= value_range[1])]
    if require_date:
        df = df[df["date"].notna()]
    if df.empty:
        st.warning("No records left after advanced filters.")
        return

    st.caption(f"Rows: {len(df)} | Datasets: {', '.join(selected_datasets)} | Timeframe: {timeframe}")
    st.download_button(
        "Download Report CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{'_'.join([d.lower().replace(' ', '-') for d in selected_datasets])}_custom_report.csv",
        mime="text/csv",
    )

    if report_type == "Distance Analysis":
        st.subheader("Participant Travel Distance")
        road_distance_enabled = bool(_get_openrouteservice_api_key())
        st.caption(
            "Estimates participant travel from home postcode to the selected walk or retreat location "
            "using road distance when routing is configured, with straight-line fallback where needed."
        )
        if road_distance_enabled:
            st.info("Road distance routing is enabled via openrouteservice.")
        else:
            st.info("Road distance routing is not configured. Results are currently straight-line miles only.")
        distance_df = fetch_distance_analysis_data(region=region_val, start_date=start_date, end_date=end_date)
        if distance_df.empty:
            st.warning("No participant-event links were found for the selected filters.")
            return

        event_type_options = sorted([v for v in distance_df["event_type"].dropna().astype(str).unique().tolist() if v])
        default_types = [v for v in event_type_options if any(token in v.lower() for token in ("walk", "retreat"))] or event_type_options
        chosen_event_types = st.multiselect(
            "Event types",
            event_type_options,
            default=default_types,
            key="reports_distance_event_types",
        )
        if chosen_event_types:
            distance_df = distance_df[distance_df["event_type"].astype(str).isin(chosen_event_types)]

        only_geocoded = st.checkbox("Only include rows with resolved distance", value=True, key="reports_distance_only_geocoded")
        if only_geocoded:
            distance_df = distance_df[distance_df["distance_miles"].notna()]
        if distance_df.empty:
            st.warning("No distance rows remain after filtering. Participant or event postcode data is likely missing.")
            return

        distance_df = distance_df.copy()
        band_labels = ["0-10", "10-25", "25-50", "50-100", "100+"]
        distance_df["distance_band"] = pd.cut(
            distance_df["distance_miles"],
            bins=[0, 10, 25, 50, 100, float("inf")],
            labels=band_labels,
            include_lowest=True,
            right=False,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Participant journeys", f"{len(distance_df):,}")
        c2.metric("Avg distance", f"{distance_df['distance_miles'].mean():.1f} miles")
        c3.metric("Median distance", f"{distance_df['distance_miles'].median():.1f} miles")
        c4.metric("Max distance", f"{distance_df['distance_miles'].max():.1f} miles")

        band_df = (
            distance_df.groupby("distance_band", observed=False)
            .size()
            .reindex(band_labels, fill_value=0)
            .rename("journeys")
            .reset_index()
        )
        fig_bands = px.bar(
            band_df,
            x="distance_band",
            y="journeys",
            title="Journey Distance Distribution",
            labels={"distance_band": "Distance band (miles)", "journeys": "Participant journeys"},
        )
        render_plot_with_export(fig_bands, "participant-distance-bands", "reports_distance_bands")

        event_summary = (
            distance_df.groupby(["event_id", "event_name", "event_type", "event_region"], as_index=False)
            .agg(
                participant_journeys=("participant", "count"),
                avg_distance_miles=("distance_miles", "mean"),
                median_distance_miles=("distance_miles", "median"),
                max_distance_miles=("distance_miles", "max"),
            )
            .sort_values(["avg_distance_miles", "participant_journeys"], ascending=[False, False])
        )
        st.markdown("**Events Ranked By Average Travel Distance**")
        summary_display = event_summary.drop(columns=["event_id"]).head(100)
        _safe_dataframe(summary_display, width="stretch", hide_index=True)

        event_summary = event_summary.copy()
        event_summary["event_label"] = event_summary.apply(
            lambda row: (
                f"{row['event_name']} | {row['event_type']} | {row['event_region']} | "
                f"{row['participant_journeys']} journeys | avg {row['avg_distance_miles']:.1f} miles"
            ),
            axis=1,
        )
        event_options = event_summary["event_label"].tolist()
        selected_event_label = st.selectbox(
            "Drill down into event",
            event_options,
            index=0 if event_options else None,
            key="reports_distance_selected_event",
        )
        selected_event_id = event_summary.loc[
            event_summary["event_label"] == selected_event_label, "event_id"
        ].iloc[0] if selected_event_label else None
        event_detail_df = distance_df[
            distance_df["event_id"].astype(str) == str(selected_event_id)
        ].copy() if selected_event_id is not None else pd.DataFrame()

        if not event_detail_df.empty:
            selected_event = event_summary.loc[
                event_summary["event_id"].astype(str) == str(selected_event_id)
            ].iloc[0]
            st.markdown("**Selected Event Journey Detail**")
            st.caption(
                f"{selected_event['event_name']} | {selected_event['event_type']} | "
                f"{selected_event['event_region']}"
            )
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Journeys", f"{len(event_detail_df):,}")
            e2.metric("Avg distance", f"{event_detail_df['distance_miles'].mean():.1f} miles")
            e3.metric("Median distance", f"{event_detail_df['distance_miles'].median():.1f} miles")
            e4.metric("Max distance", f"{event_detail_df['distance_miles'].max():.1f} miles")

        detail_cols = [
            "event_date",
            "event_name",
            "event_type",
            "event_region",
            "event_location",
            "event_postcode",
            "participant",
            "participant_postcode",
            "distance_miles",
            "distance_method",
        ]
        detail_limit = st.number_input("Detail rows", min_value=25, max_value=5000, value=250, step=25, key="reports_distance_detail_limit")
        detail_source_df = event_detail_df if not event_detail_df.empty else distance_df
        detail_df = detail_source_df[detail_cols].sort_values("distance_miles", ascending=False).head(int(detail_limit))
        st.markdown("**Participant-Level Journey Detail**")
        _safe_dataframe(detail_df, width="stretch", hide_index=True)
        if not event_detail_df.empty:
            st.download_button(
                "Download Selected Event CSV",
                data=event_detail_df.to_csv(index=False).encode("utf-8"),
                file_name="participant_distance_selected_event.csv",
                mime="text/csv",
                key="reports_distance_selected_event_csv",
            )
        st.download_button(
            "Download Distance Analysis CSV",
            data=distance_df.to_csv(index=False).encode("utf-8"),
            file_name="participant_distance_analysis.csv",
            mime="text/csv",
            key="reports_distance_csv",
        )
        return

    numeric_cols = [c for c in ["record_count", "metric_value"] if c in df.columns]
    candidate_dims = [c for c in ["region", "category", "status", "month", "label"] if c in df.columns]
    dims = [c for c in candidate_dims if df[c].astype(str).nunique() > 1]
    if not dims:
        dims = ["region"]

    if report_type == "Tabular":
        default_cols = [c for c in ["date", "region", "category", "status", "label", "metric_value"] if c in df.columns]
        cols = st.multiselect("Columns", df.columns.tolist(), default=default_cols, key="reports_table_cols")
        table_df = df[cols] if cols else df
        sort_col = st.selectbox("Sort table by", table_df.columns.tolist(), key="reports_table_sort_col")
        sort_desc = st.checkbox("Sort descending", value=True, key="reports_table_sort_desc")
        row_limit = st.number_input("Max rows", min_value=10, max_value=5000, value=500, step=10, key="reports_table_row_limit")
        table_df = table_df.sort_values(sort_col, ascending=not sort_desc, na_position="last").head(int(row_limit))
        _safe_dataframe(table_df, width="stretch", hide_index=True)
        return

    agg_col = st.selectbox("Group By", dims, key="reports_group_col")
    metric_col = st.selectbox("Metric", numeric_cols, key="reports_metric_col")
    agg_mode = st.selectbox("Aggregation", ["sum", "count", "mean"], key="reports_agg_mode")
    top_n = st.slider("Top N groups", min_value=3, max_value=100, value=20, key="reports_top_n")

    if agg_mode == "count":
        grouped = df.groupby(agg_col, as_index=False).size().rename(columns={"size": "value"})
    elif agg_mode == "mean":
        grouped = df.groupby(agg_col, as_index=False)[metric_col].mean().rename(columns={metric_col: "value"})
    else:
        grouped = df.groupby(agg_col, as_index=False)[metric_col].sum().rename(columns={metric_col: "value"})
    grouped = grouped.sort_values("value", ascending=False).head(int(top_n))

    if report_type == "Bar":
        color_dim_options = ["None"] + [d for d in dims if d != agg_col]
        color_dim = st.selectbox("Bar color split", color_dim_options, key="reports_bar_color_dim")
        if color_dim != "None":
            if agg_mode == "count":
                grouped_color = df.groupby([agg_col, color_dim], as_index=False).size().rename(columns={"size": "value"})
            elif agg_mode == "mean":
                grouped_color = df.groupby([agg_col, color_dim], as_index=False)[metric_col].mean().rename(columns={metric_col: "value"})
            else:
                grouped_color = df.groupby([agg_col, color_dim], as_index=False)[metric_col].sum().rename(columns={metric_col: "value"})
            fig = px.bar(grouped_color, x=agg_col, y="value", color=color_dim, barmode="group", title=f"{', '.join(selected_datasets)}: {agg_mode} of {metric_col} by {agg_col}")
        else:
            fig = px.bar(grouped, x=agg_col, y="value", title=f"{', '.join(selected_datasets)}: {agg_mode} of {metric_col} by {agg_col}")
        render_plot_with_export(fig, "custom-report-bar", "reports_bar")
    elif report_type == "Pie":
        fig = px.pie(grouped, names=agg_col, values="value", title=f"{', '.join(selected_datasets)}: {agg_mode} of {metric_col}")
        render_plot_with_export(fig, "custom-report-pie", "reports_pie")
    elif report_type == "Line":
        line_df = df.copy()
        if line_df["date"].isna().all():
            st.warning("No date values available for line output in this dataset.")
            return
        freq = st.selectbox("Line Interval", ["Daily", "Weekly", "Monthly"], key="reports_line_freq")
        freq_code = {"Daily": "D", "Weekly": "W-MON", "Monthly": "ME"}[freq]
        line_df = line_df.dropna(subset=["date"])
        split_options = ["None"] + dims
        line_split = st.selectbox("Line split", split_options, key="reports_line_split")
        if line_split != "None":
            group_cols = [pd.Grouper(key="date", freq=freq_code), line_split]
        else:
            group_cols = [pd.Grouper(key="date", freq=freq_code)]
        if agg_mode == "count":
            trend = line_df.groupby(group_cols, as_index=False).size().rename(columns={"size": "value"})
        elif agg_mode == "mean":
            trend = line_df.groupby(group_cols, as_index=False)[metric_col].mean().rename(columns={metric_col: "value"})
        else:
            trend = line_df.groupby(group_cols, as_index=False)[metric_col].sum().rename(columns={metric_col: "value"})
        if line_split != "None":
            fig = px.line(trend, x="date", y="value", color=line_split, markers=True, title=f"{', '.join(selected_datasets)}: {freq} trend")
        else:
            fig = px.line(trend, x="date", y="value", markers=True, title=f"{', '.join(selected_datasets)}: {freq} trend")
        render_plot_with_export(fig, "custom-report-line", "reports_line")
    elif report_type == "UK Map":
        region_map = grouped[grouped[agg_col].notna()].copy()
        if agg_col != "region":
            region_map = df.groupby("region", as_index=False)["metric_value"].sum().rename(columns={"metric_value": "value"})
        coords = {
            "north of england": (54.8, -2.2),
            "south of england": (51.4, -0.5),
            "midlands": (52.6, -1.7),
            "wales": (52.5, -3.7),
            "other": (53.5, -1.2),
            "global": (54.2, -2.5),
        }
        region_map["key"] = region_map["region"].astype(str).str.lower()
        region_map["lat"] = region_map["key"].map(lambda k: coords.get(k, (53.5, -1.2))[0])
        region_map["lon"] = region_map["key"].map(lambda k: coords.get(k, (53.5, -1.2))[1])
        fig = px.scatter_geo(
            region_map,
            lat="lat",
            lon="lon",
            size="value",
            color="region",
            hover_name="region",
            hover_data={"value": True, "lat": False, "lon": False},
            title=f"{', '.join(selected_datasets)}: UK regional distribution",
        )
        fig.update_geos(scope="europe", projection_type="natural earth", center={"lat": 54.0, "lon": -2.0}, lataxis_range=[49, 60], lonaxis_range=[-8, 3])
        render_plot_with_export(fig, "custom-report-uk-map", "reports_map")
    else:
        compare_dim = st.selectbox("Compare By", dims, key="reports_compare_dim")
        compare_vals = sorted(df[compare_dim].dropna().astype(str).unique().tolist())
        if len(compare_vals) < 2:
            st.warning("Not enough distinct values to run comparison analysis.")
            return
        base_val = st.selectbox("Baseline", compare_vals, index=0, key="reports_compare_base")
        alt_default = 1 if len(compare_vals) > 1 else 0
        alt_val = st.selectbox("Compare Against", compare_vals, index=alt_default, key="reports_compare_alt")
        base = df[df[compare_dim].astype(str) == str(base_val)]
        alt = df[df[compare_dim].astype(str) == str(alt_val)]

        base_total = float(base[metric_col].sum()) if metric_col in base.columns else float(len(base))
        alt_total = float(alt[metric_col].sum()) if metric_col in alt.columns else float(len(alt))
        delta = alt_total - base_total
        pct = (delta / base_total * 100.0) if base_total else None

        c1, c2, c3 = st.columns(3)
        c1.metric(f"{base_val}", f"{base_total:,.2f}")
        c2.metric(f"{alt_val}", f"{alt_total:,.2f}")
        c3.metric("Delta", f"{delta:,.2f}", f"{pct:.1f}%" if pct is not None else "n/a")

        comp_df = pd.DataFrame(
            [
                {"group": str(base_val), "value": base_total, "rows": len(base)},
                {"group": str(alt_val), "value": alt_total, "rows": len(alt)},
            ]
        )
        fig = px.bar(comp_df, x="group", y="value", text="rows", title=f"Comparison: {base_val} vs {alt_val}")
        render_plot_with_export(fig, "custom-report-comparison", "reports_compare")

# --- MAIN APP FLOW ---
def main():
    inject_global_styles()
    init_files()
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_page()
    else:
        if st.session_state.get('force_password_change'):
            password_change_page()
            return
        if st.sidebar.button("Logout", key="logout"):
            log_audit_event("Logout", {"from": "dashboard"})
            st.session_state['logged_in'] = False
            st.rerun()
        
        badge_ts = datetime.now().strftime("%Y%m%d%H%M")
        st.sidebar.markdown(
            f"[![Keep The Dashboard Awake]"
            f"(https://github.com/Scott-MoM/RPL-KPIs/actions/workflows/keep-streamlit-awake.yml/badge.svg?branch=main&t={badge_ts})"
            f"](https://github.com/Scott-MoM/RPL-KPIs/actions/workflows/keep-streamlit-awake.yml)"
        )
        st.sidebar.markdown(
            f"[![Nightly Beacon Sync]"
            f"(https://github.com/Scott-MoM/RPL-KPIs/actions/workflows/nightly-beacon-sync.yml/badge.svg?branch=main&t={badge_ts})"
            f"](https://github.com/Scott-MoM/RPL-KPIs/actions/workflows/nightly-beacon-sync.yml)"
        )
        sync_state, sync_running = render_manual_sync_status()

        # Last Data Refresh card
        last_refresh = get_last_refresh_timestamp()
        if last_refresh:
            hours = (datetime.now(last_refresh.tzinfo) - last_refresh).total_seconds() / 3600.0
            if hours <= 24:
                cls = "refresh-green"
            elif hours <= 72:
                cls = "refresh-amber"
            else:
                cls = "refresh-red"
            ts_str = last_refresh.strftime("%d/%m/%Y %H:%M")
            extra = ""
            if hours > 72:
                extra = "<br><strong>Data refresh needed</strong>"
            st.sidebar.markdown(
                f"<div class='refresh-card {cls}'>Last Data Refresh: {ts_str}{extra}</div>",
                unsafe_allow_html=True
            )
        else:
            st.sidebar.markdown(
                "<div class='refresh-card refresh-red'>Last Data Refresh: Unknown<br><strong>Data refresh needed</strong></div>",
                unsafe_allow_html=True
            )
            
        role = st.session_state.get('role')
        current_view = None
        if role == 'Admin':
            view = st.sidebar.radio("View Mode", ["Admin Dashboard", "KPI Dashboard", "Custom Reports Dashboard", "Case Studies", "Funder Dashboard", "ML Dashboard"])
            current_view = view
            log_audit_state_change("view_mode", "Dashboard View Changed", {"view": view, "role": role})
            if view == "Admin Dashboard":
                admin_dashboard()
            elif view == "KPI Dashboard":
                main_dashboard()
            elif view == "Custom Reports Dashboard":
                custom_reports_dashboard()
            elif view == "Funder Dashboard":
                funder_dashboard()
            elif view == "ML Dashboard":
                ml_dashboard()
            else:
                timeframe, start_date, end_date = get_time_filters()
                case_studies_page(allow_upload=True, start_date=start_date, end_date=end_date)
        elif role == 'Manager':
            view = st.sidebar.radio("View Mode", ["KPI Dashboard", "Custom Reports Dashboard", "Case Studies", "Funder Dashboard", "ML Dashboard"])
            current_view = view
            log_audit_state_change("view_mode", "Dashboard View Changed", {"view": view, "role": role})
            if view == "KPI Dashboard":
                main_dashboard()
            elif view == "Custom Reports Dashboard":
                custom_reports_dashboard()
            elif view == "Funder Dashboard":
                funder_dashboard()
            elif view == "ML Dashboard":
                ml_dashboard()
            else:
                timeframe, start_date, end_date = get_time_filters()
                case_studies_page(allow_upload=True, start_date=start_date, end_date=end_date)
        elif role == 'ML':
            view = st.sidebar.radio("View Mode", ["ML Dashboard", "Case Studies"])
            current_view = view
            log_audit_state_change("view_mode", "Dashboard View Changed", {"view": view, "role": role})
            if view == "ML Dashboard":
                ml_dashboard()
            else:
                timeframe, start_date, end_date = get_time_filters()
                case_studies_page(allow_upload=True, start_date=start_date, end_date=end_date)
        elif role == 'Funder':
            view = st.sidebar.radio("View Mode", ["Funder Dashboard"])
            current_view = view
            log_audit_state_change("view_mode", "Dashboard View Changed", {"view": view, "role": role})
            funder_dashboard()
        else:
            view = st.sidebar.radio("View Mode", ["KPI Dashboard", "Custom Reports Dashboard", "Case Studies"])
            current_view = view
            log_audit_state_change("view_mode", "Dashboard View Changed", {"view": view, "role": role})
            if view == "KPI Dashboard":
                main_dashboard()
            elif view == "Custom Reports Dashboard":
                custom_reports_dashboard()
            else:
                timeframe, start_date, end_date = get_time_filters()
                case_studies_page(allow_upload=True, start_date=start_date, end_date=end_date)

        audit_user_interactions(current_view=current_view)

        if sync_running and role == "Admin" and current_view == "Admin Dashboard":
            time.sleep(1)
            st.rerun()

if __name__ == "__main__":
    main()




