"""Streamlit recreation of the desktop Viber Outreach Manager."""

from __future__ import annotations

import os
import csv
import urllib.parse
from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

import theme as T
from core import google_sync as google_sync_module
from core.database import (
    add_lead,
    add_template,
    delete_template,
    get_all_leads,
    get_all_templates,
    get_daily_stats,
    get_connection,
    get_setting,
    increment_daily_stat,
    increment_template_usage,
    init_db,
    set_setting,
    update_contact_status,
    update_follow_up,
    update_lead_reply,
    update_sim_assignment,
    update_template,
)
APP_TITLE = "Viber Outreach Manager"
TAB_LABELS = ["Leads", "Pipeline", "Tasks", "Templates", "Analytics", "Settings"]
LEAD_FILTERS = ["Show All", "Uncontacted", "SIM 1", "SIM 2", "Contacted"]
PIPELINE_STATUSES = ["Uncontacted", "Contacted", "Replied", "Call Booked", "Rejected"]
PIPELINE_COLUMNS = [
    ("Uncontacted", T.STATUS_FALSE_BORDER, T.STATUS_FALSE_TEXT),
    ("Contacted", T.STATUS_TRUE_BORDER, T.STATUS_TRUE_TEXT),
    ("Replied", "#d4b106", "#d4b106"),
    ("Call Booked", "#00a86b", "#00a86b"),
    ("Rejected", "#c23b22", "#c23b22"),
]
PRIORITY_COLORS = {"High": "#c23b22", "Medium": "#d4b106", "Low": "#4f9dd9"}
DEFAULT_MESSAGE_TEMPLATES = {
    1: "Hi! We help local businesses turn online interest into booked calls. Want a quick example tailored to your shop?",
    2: "Hello! I noticed your business and wanted to share a simple outreach idea that can help convert more inquiries into appointments.",
    3: "Hey! We work with local service businesses to improve follow-up and booking rates. Happy to send a short custom idea for your shop.",
}
SETTINGS_FIELDS = [
    ("google_sheet_name", "Google Sheet Name", "Spreadsheet tab or workbook name used for sync output."),
    ("backup_sheet_name", "Backup Sheet Name", "Separate Google Sheet used for full SQLite backup snapshots."),
    ("sim1_daily_limit", "SIM 1 Daily Limit", "Maximum outreach actions allowed for SIM 1 each day."),
    ("sim2_daily_limit", "SIM 2 Daily Limit", "Maximum outreach actions allowed for SIM 2 each day."),
    ("credentials_path", "Credentials Path", "Path to the Google service account credentials JSON file."),
]
SETTINGS_DEFAULTS = {
    "google_sheet_name": "Viber Outreach Sync",
    "backup_sheet_name": "Viber CRM Backup",
    "sim1_daily_limit": "40",
    "sim2_daily_limit": "40",
    "credentials_path": "credentials.json",
}
NUMERIC_SETTING_KEYS = {"sim1_daily_limit", "sim2_daily_limit"}
TOAST_ICONS = {
    "success": ":material/check_circle:",
    "error": ":material/error:",
    "warning": ":material/warning:",
    "info": ":material/info:",
}


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":telephone_receiver:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def apply_styles() -> None:
    """Theme Streamlit so it feels like the desktop app from the screenshots."""
    st.markdown(
        f"""
        <style>
            :root {{
                --bg-root: {T.BG_ROOT};
                --bg-row: {T.BG_ROW};
                --bg-nav: {T.BG_NAV};
                --border: {T.BORDER_DEFAULT};
                --border-subtle: {T.BORDER_SUBTLE};
                --text-primary: {T.TEXT_PRIMARY};
                --text-secondary: {T.TEXT_SECONDARY};
                --text-muted: {T.TEXT_MUTED};
                --accent: {T.ACCENT_PRIMARY};
                --accent-hover: {T.ACCENT_HOVER};
            }}

            .stApp {{ background: var(--bg-root); color: var(--text-primary); }}
            [data-testid="stHeader"] {{ background: rgba(0, 0, 0, 0); }}
            .block-container {{
                max-width: 960px;
                padding-top: 0.35rem;
                padding-bottom: 1rem;
                padding-left: 0.7rem;
                padding-right: 0.7rem;
            }}
            .app-title {{
                display: flex;
                align-items: center;
                gap: 0.6rem;
                font-size: 1.08rem;
                font-weight: 700;
                margin-bottom: 0.3rem;
            }}
            .app-badge {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                background: linear-gradient(180deg, #29a0ff 0%, #1182da 100%);
                box-shadow: 0 0 0 3px rgba(17, 130, 218, 0.15);
            }}
            .surface-card {{
                border: 1px solid var(--border-subtle);
                border-radius: 14px;
                background: var(--bg-row);
                padding: 0.9rem 1rem;
            }}
            .section-title {{ font-size: 1.02rem; font-weight: 800; margin-bottom: 0.12rem; }}
            .section-subtitle {{ color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 0.55rem; }}
            .stat-chip {{
                display: inline-flex;
                align-items: center;
                gap: 0.42rem;
                margin-right: 1rem;
                color: var(--text-secondary);
                font-size: 0.92rem;
            }}
            .stat-dot {{
                width: 8px;
                height: 8px;
                border-radius: 999px;
                display: inline-block;
            }}
            .row-shell {{
                padding: 0.7rem 0.75rem;
                border: 1px solid var(--border-subtle);
                border-radius: 12px;
                background: var(--bg-row);
                margin-bottom: 0.55rem;
            }}
            .table-head {{
                color: var(--text-muted);
                font-size: 0.74rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 0.55rem;
            }}
            .phone-main {{ font-size: 1rem; font-weight: 800; color: var(--text-primary); }}
            .subtle-note {{ color: var(--text-secondary); font-size: 0.85rem; }}
            .status-pill {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 110px;
                padding: 0.35rem 0.85rem;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 700;
                border: 1px solid var(--border);
            }}
            .status-uncontacted {{ background: {T.STATUS_FALSE_BG}; color: {T.STATUS_FALSE_TEXT}; border-color: {T.STATUS_FALSE_BORDER}; }}
            .status-contacted {{ background: {T.STATUS_TRUE_BG}; color: {T.STATUS_TRUE_TEXT}; border-color: {T.STATUS_TRUE_BORDER}; }}
            .status-replied {{ background: #332D00; color: #d4b106; border-color: #d4b106; }}
            .status-call-booked {{ background: #003322; color: #00a86b; border-color: #00a86b; }}
            .status-rejected {{ background: #330D08; color: #c23b22; border-color: #c23b22; }}
            .viber-link {{
                display: block;
                width: 100%;
                margin: 0.45rem 0 0.55rem 0;
                padding: 0.72rem 0.9rem;
                text-align: center;
                text-decoration: none;
                border-radius: 14px;
                background: linear-gradient(180deg, {T.ACCENT_PRIMARY} 0%, #5f4be0 100%);
                color: white !important;
                font-size: 0.96rem;
                font-weight: 800;
                box-shadow: 0 10px 24px rgba(115, 96, 242, 0.28);
            }}
            .template-preview {{
                border: 1px solid var(--border-subtle);
                border-radius: 12px;
                background: rgba(0, 0, 0, 0.15);
                padding: 0.8rem;
                color: var(--text-secondary);
                font-size: 0.9rem;
                white-space: pre-wrap;
            }}
            .kanban-card, .metric-card {{
                border: 1px solid var(--border);
                border-radius: 12px;
                background: var(--bg-row);
                padding: 0.8rem 1rem;
                margin-bottom: 0.65rem;
            }}
            .metric-label {{ color: var(--text-secondary); font-size: 0.86rem; margin-bottom: 0.35rem; }}
            .metric-value {{ color: var(--text-primary); font-size: 1.75rem; font-weight: 800; }}
            [data-baseweb="tab-list"] {{ gap: 0.3rem; justify-content: center; margin-bottom: 0.9rem; }}
            button[data-baseweb="tab"] {{
                background: var(--bg-row);
                color: var(--text-primary);
                border-radius: 4px 4px 0 0;
                border: 1px solid var(--border-subtle);
                padding: 0.35rem 0.8rem;
            }}
            button[data-baseweb="tab"][aria-selected="true"] {{ background: {T.ACCENT_PRIMARY}; color: white; }}
            .stTextInput input,
            .stTextArea textarea {{
                background: #000000 !important;
                color: #ffffff !important;
                border: 1px solid #2d2d2d !important;
                border-radius: 10px !important;
            }}
            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {{
                color: #7f7f7f !important;
                opacity: 1 !important;
            }}
            div[data-baseweb="select"] > div {{
                background: #111111 !important;
                color: #ffffff !important;
                border: 1px solid #2d2d2d !important;
                border-radius: 10px !important;
            }}
            .stButton > button {{
                border-radius: 999px;
                min-height: 2.35rem;
                font-weight: 700;
                border: 1px solid var(--border-subtle);
                background: var(--accent);
                color: white;
            }}
            .stButton > button:hover {{ background: var(--accent-hover); color: white; }}
            .stFileUploader section {{ background: rgba(0, 0, 0, 0.12); border-radius: 12px; }}
            .stExpander {{
                border: 1px solid var(--border-subtle);
                border-radius: 12px;
                background: var(--bg-row);
                margin-bottom: 0.5rem;
                overflow: hidden;
            }}
            .stExpander details {{
                background: var(--bg-row);
                border-radius: 12px;
            }}
            .stExpander details summary {{
                padding: 0.55rem 0.8rem;
            }}
            .streamlit-expanderHeader {{
                color: var(--text-primary);
                font-size: 0.92rem;
                font-weight: 700;
                line-height: 1.2;
            }}
            div[data-testid="stExpanderDetails"] {{
                padding-top: 0.15rem;
            }}
            .lead-meta {{
                color: var(--text-secondary);
                font-size: 0.82rem;
                margin-bottom: 0.5rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def maybe_require_password() -> None:
    """Keep optional password support for deployments that set `app_password`."""
    try:
        app_password = st.secrets.get("app_password")
    except Exception:
        app_password = None

    if not app_password or st.session_state.get("authenticated"):
        return

    st.markdown(
        f"""
        <div class="surface-card" style="max-width:420px; margin:5rem auto 0 auto;">
            <div class="section-title">{APP_TITLE}</div>
            <div class="section-subtitle">Enter the password to open the CRM.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    password = st.text_input("Password", type="password", placeholder="Enter app password")
    if st.button("Enter", use_container_width=True):
        if password == app_password:
            st.session_state.authenticated = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()


def init_state() -> None:
    """Seed session state used across tabs."""
    defaults = {
        "lead_filter": "Uncontacted",
        "current_selected_template": None,
        "selected_template_id": None,
        "template_form_name": "",
        "template_form_category": "General",
        "template_form_body": "",
        "settings_values": {},
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def set_flash(message: str, kind: str = "success", *, toast: bool = True) -> None:
    """Queue a toast-like message for the next rerun."""
    st.session_state.flash_message = message
    st.session_state.flash_kind = kind
    st.session_state.flash_toast = toast


def show_flash() -> None:
    """Render the queued message if one exists."""
    message = st.session_state.pop("flash_message", None)
    kind = st.session_state.pop("flash_kind", "success")
    toast = st.session_state.pop("flash_toast", False)
    if not message:
        return
    if toast and hasattr(st, "toast"):
        st.toast(message, icon=TOAST_ICONS.get(kind, TOAST_ICONS["info"]))
    if kind == "error":
        st.error(message)
    elif kind == "warning":
        st.warning(message)


def normalize_phone(phone_number: str | None) -> str:
    """Strip a phone number down to digits and an optional leading plus."""
    return "".join(ch for ch in str(phone_number or "") if ch.isdigit() or ch == "+")


def inject_dynamic_template_values(message_text: str, lead: dict) -> str:
    """Replace supported template placeholders with live lead data."""
    rendered_message = str(message_text or "")
    replacements = {
        "{Shop Name}": str(lead.get("name") or ""),
        "{City}": str(lead.get("city") or ""),
    }
    for placeholder, value in replacements.items():
        rendered_message = rendered_message.replace(placeholder, value)
    return rendered_message


def build_viber_link(phone_number: str | None, message_text: str = "", lead: dict | None = None) -> str:
    """Build a Viber deep link with a safely encoded prefilled draft message."""
    clean_phone = normalize_phone(phone_number)
    final_message = inject_dynamic_template_values(message_text, lead) if lead else str(message_text or "")
    encoded_message = urllib.parse.quote(final_message)
    return f"viber://chat?number={clean_phone}&draft={encoded_message}"


def derive_status(lead: dict) -> str:
    """Use the same status logic as the desktop app."""
    status = lead.get("lead_status") or "Uncontacted"
    if lead.get("is_contacted") and status == "Uncontacted":
        status = "Contacted"
    return status


def status_class(status: str) -> str:
    """Map lead status to a CSS class for the pill badge."""
    return {
        "Uncontacted": "status-uncontacted",
        "Contacted": "status-contacted",
        "Replied": "status-replied",
        "Call Booked": "status-call-booked",
        "Rejected": "status-rejected",
    }.get(status, "status-uncontacted")


def filter_leads(leads: list[dict], active_filter: str) -> list[dict]:
    """Apply the same filter semantics as the desktop Leads tab."""
    if active_filter == "Uncontacted":
        return [lead for lead in leads if not lead.get("is_contacted")]
    if active_filter == "Contacted":
        return [lead for lead in leads if lead.get("is_contacted")]
    if active_filter == "SIM 1":
        return [lead for lead in leads if lead.get("sim_assignment") == "SIM 1"]
    if active_filter == "SIM 2":
        return [lead for lead in leads if lead.get("sim_assignment") == "SIM 2"]
    return leads


def get_template_choices() -> list[tuple[str, int]]:
    """Prefer saved templates, but fall back to the three original quick picks."""
    templates = get_all_templates()
    if templates:
        return [(f'{tpl["name"]} ({tpl.get("category") or "General"})', tpl["id"]) for tpl in templates]
    return [(f"Template {number}", number) for number in (1, 2, 3)]


def get_template_preview(template_id: int) -> str:
    """Return template body text when we have a saved template match."""
    for template in get_all_templates():
        if template["id"] == template_id:
            return template.get("body") or ""
    return DEFAULT_MESSAGE_TEMPLATES.get(template_id, "")


def sync_contact_message_from_template(lead_id: int) -> None:
    """Keep the editable message in sync with the chosen quick template."""
    selected_label = st.session_state.get(f"contact_template_{lead_id}")
    template_id = dict(get_template_choices()).get(selected_label, 1)
    st.session_state[f"contact_message_{lead_id}"] = get_template_preview(template_id)


def ensure_lead_state(lead: dict, template_choices: list[tuple[str, int]] | None = None) -> None:
    """Seed all per-lead Streamlit state values used across tabs."""
    lead_id = lead["id"]
    status = derive_status(lead)
    sim_key = f"sim_assignment_{lead_id}"
    if sim_key not in st.session_state:
        st.session_state[sim_key] = (
            lead.get("sim_assignment") if lead.get("sim_assignment") != "Unassigned" else "None"
        )
    st.session_state.setdefault(
        f"reply_status_{lead_id}",
        status if status in PIPELINE_STATUSES else "Contacted",
    )
    st.session_state.setdefault(
        f"pipeline_status_{lead_id}",
        status if status in PIPELINE_STATUSES else "Uncontacted",
    )
    st.session_state.setdefault(f"reply_notes_{lead_id}", lead.get("reply_notes") or "")
    st.session_state.setdefault(f"follow_up_date_{lead_id}", lead.get("follow_up_date") or "")
    st.session_state.setdefault(f"priority_{lead_id}", lead.get("priority") or "Medium")

    if template_choices is None:
        template_choices = get_template_choices()
    contact_template_key = f"contact_template_{lead_id}"
    if contact_template_key not in st.session_state:
        st.session_state[contact_template_key] = template_choices[0][0]
    contact_message_key = f"contact_message_{lead_id}"
    if contact_message_key not in st.session_state:
        template_id = dict(template_choices).get(st.session_state[contact_template_key], 1)
        st.session_state[contact_message_key] = get_template_preview(template_id)


def apply_lead_update(
    lead: dict,
    *,
    status: str,
    notes: str,
    follow_up_date: str,
    priority: str,
    success_message: str,
) -> None:
    """Persist a lead update with consistent status and metrics behavior."""
    lead_id = lead["id"]
    previous_status = derive_status(lead)
    cleaned_follow_up = follow_up_date.strip() or None

    if status == "Uncontacted":
        update_contact_status(lead_id, 0, lead.get("template_used"))
        update_follow_up(lead_id, cleaned_follow_up, priority)
        set_flash(success_message)
        return

    if not lead.get("is_contacted"):
        update_contact_status(lead_id, 1, lead.get("template_used"))

    update_lead_reply(lead_id, status, notes)
    update_follow_up(lead_id, cleaned_follow_up, priority)

    if status == "Replied" and previous_status != "Replied":
        increment_daily_stat("replies_received")
    if status == "Call Booked" and previous_status != "Call Booked":
        increment_daily_stat("calls_booked")

    set_flash(success_message)


def update_sim_callback(lead_id: int, state_key: str) -> None:
    """Persist SIM changes directly when the selectbox changes."""
    selected = st.session_state.get(state_key, "None")
    update_sim_assignment(lead_id, "Unassigned" if selected == "None" else selected)
    set_flash("SIM assignment updated.")


def save_reply_callback(lead: dict) -> None:
    """Persist a reply/status update and optionally follow-up details."""
    lead_id = lead["id"]
    apply_lead_update(
        lead,
        status=st.session_state.get(f"reply_status_{lead_id}", derive_status(lead)),
        notes=st.session_state.get(f"reply_notes_{lead_id}", ""),
        follow_up_date=st.session_state.get(f"follow_up_date_{lead_id}", ""),
        priority=st.session_state.get(f"priority_{lead_id}", lead.get("priority") or "Medium"),
        success_message="Lead pipeline updated.",
    )


def update_pipeline_status_callback(lead: dict) -> None:
    """Persist a pipeline status change instantly from the kanban card selector."""
    lead_id = lead["id"]
    selected_status = st.session_state.get(f"pipeline_status_{lead_id}", derive_status(lead))
    st.session_state[f"reply_status_{lead_id}"] = selected_status
    apply_lead_update(
        lead,
        status=selected_status,
        notes=st.session_state.get(f"reply_notes_{lead_id}", lead.get("reply_notes") or ""),
        follow_up_date=st.session_state.get(f"follow_up_date_{lead_id}", lead.get("follow_up_date") or ""),
        priority=st.session_state.get(f"priority_{lead_id}", lead.get("priority") or "Medium"),
        success_message="Pipeline stage updated.",
    )
    st.rerun()


def mark_contacted_callback(lead: dict) -> None:
    """Mark a lead as contacted, record the selected template, and count a sent message."""
    lead_id = lead["id"]
    choice = st.session_state.get(f"contact_template_{lead_id}", "Template 1")
    template_choices = dict(get_template_choices())
    template_used = template_choices.get(choice, 1)
    update_contact_status(lead_id, 1, template_used)

    if any(template_id == template_used for _, template_id in get_template_choices() if template_id > 3):
        increment_template_usage(template_used)
    increment_daily_stat("messages_sent")
    set_flash("Lead marked as contacted.")


def import_uploaded_csv(uploaded_file) -> None:
    """Import CSV rows directly into SQLite while ignoring duplicate phone numbers."""
    if uploaded_file is None:
        set_flash("Choose a CSV file to import.", "warning")
        return

    decoded_text = None
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            decoded_text = uploaded_file.getvalue().decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if decoded_text is None:
        set_flash("Could not read that CSV file encoding.", "error")
        return

    try:
        reader = csv.DictReader(decoded_text.splitlines())
        if not reader.fieldnames:
            set_flash("The CSV file is missing a header row.", "error")
            return

        normalized_headers = {header.strip().lower(): header for header in reader.fieldnames if header}
        name_column = next(
            (normalized_headers[key] for key in ("shop name", "name", "shop") if key in normalized_headers),
            None,
        )
        phone_column = next(
            (normalized_headers[key] for key in ("phone", "phone number", "phone_number") if key in normalized_headers),
            None,
        )
        city_column = next(
            (normalized_headers[key] for key in ("city", "town") if key in normalized_headers),
            None,
        )

        if not phone_column:
            set_flash("CSV import requires a Phone column.", "error")
            return

        inserted = 0
        connection = get_connection()
        try:
            for row in reader:
                phone = str(row.get(phone_column, "")).strip()
                if not phone:
                    continue
                shop_name = str(row.get(name_column, "")).strip() if name_column else ""
                city = str(row.get(city_column, "")).strip() if city_column else ""
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO Leads (name, phone_number, city) VALUES (?, ?, ?)",
                    (shop_name or "Unnamed Lead", phone, city),
                )
                inserted += cursor.rowcount
            connection.commit()
        finally:
            connection.close()

        for _ in range(inserted):
            increment_daily_stat("leads_imported")

        if inserted:
            set_flash(f"Imported {inserted} new leads from {uploaded_file.name}.", "success", toast=True)
        else:
            set_flash("No new leads were imported. All phone numbers already exist.", "warning", toast=True)
    except Exception as exc:
        set_flash(f"Import failed: {exc}", "error")


def sync_primary_sheet_to_app() -> None:
    """Pull leads from the primary intake Google Sheet into the local SQLite app."""
    project_root = os.path.dirname(__file__)
    sheet_name = (
        get_setting("google_sheet_name", SETTINGS_DEFAULTS["google_sheet_name"])
        or SETTINGS_DEFAULTS["google_sheet_name"]
    )
    credentials_path = (
        get_setting("credentials_path", SETTINGS_DEFAULTS["credentials_path"])
        or SETTINGS_DEFAULTS["credentials_path"]
    )
    if not os.path.isabs(credentials_path):
        credentials_path = os.path.join(project_root, credentials_path)

    if not os.path.exists(credentials_path):
        set_flash("Sync failed: credentials file was not found.", "error", toast=True)
        return

    try:
        credentials = google_sync_module.Credentials.from_service_account_file(
            credentials_path,
            scopes=google_sync_module.SCOPES,
        )
        client = google_sync_module.gspread.authorize(credentials)

        try:
            spreadsheet = client.open(sheet_name)
        except google_sync_module.gspread.exceptions.SpreadsheetNotFound:
            set_flash(
                f"Primary sheet '{sheet_name}' was not found. Share it with {credentials.service_account_email}.",
                "error",
                toast=True,
            )
            return

        worksheet = spreadsheet.sheet1
        records = worksheet.get_all_records()
        if not records:
            set_flash("No rows were found in the primary intake sheet.", "warning", toast=True)
            return

        inserted = 0
        existing_phones = {str(lead.get("phone_number") or "").strip() for lead in get_all_leads()}
        for record in records:
            normalized_record = {str(key).strip().lower(): value for key, value in record.items()}
            shop_name = str(
                normalized_record.get("shop name")
                or normalized_record.get("name")
                or normalized_record.get("shop")
                or "Unnamed Lead"
            ).strip()
            phone = str(
                normalized_record.get("phone")
                or normalized_record.get("phone number")
                or normalized_record.get("phone_number")
                or ""
            ).strip()
            city = str(normalized_record.get("city") or normalized_record.get("town") or "").strip()

            if not phone or phone in existing_phones:
                continue

            add_lead(shop_name or "Unnamed Lead", phone, city)
            existing_phones.add(phone)
            inserted += 1

        for _ in range(inserted):
            increment_daily_stat("leads_imported")

        if inserted:
            set_flash(f"Synced {inserted} new leads from {sheet_name}.", "success", toast=True)
        else:
            set_flash("No new leads were found to sync from the intake sheet.", "warning", toast=True)
    except Exception as exc:
        set_flash(f"Sync failed: {exc}", "error", toast=True)


def backup_database_to_sheets() -> None:
    """Push the entire local Leads table into the configured backup Google Sheet."""
    project_root = os.path.dirname(__file__)
    backup_sheet_name = (
        get_setting("backup_sheet_name", SETTINGS_DEFAULTS["backup_sheet_name"])
        or SETTINGS_DEFAULTS["backup_sheet_name"]
    )
    credentials_path = (
        get_setting("credentials_path", SETTINGS_DEFAULTS["credentials_path"])
        or SETTINGS_DEFAULTS["credentials_path"]
    )
    if not os.path.isabs(credentials_path):
        credentials_path = os.path.join(project_root, credentials_path)

    if not os.path.exists(credentials_path):
        set_flash("Backup failed: credentials file was not found.", "error", toast=True)
        return

    try:
        credentials = google_sync_module.Credentials.from_service_account_file(
            credentials_path,
            scopes=google_sync_module.SCOPES,
        )
        client = google_sync_module.gspread.authorize(credentials)

        try:
            spreadsheet = client.open(backup_sheet_name)
        except google_sync_module.gspread.exceptions.SpreadsheetNotFound:
            set_flash(
                f"Backup sheet '{backup_sheet_name}' was not found. Share it with {credentials.service_account_email}.",
                "error",
                toast=True,
            )
            return

        leads = get_all_leads()
        if leads:
            frame = pd.DataFrame(leads).fillna("")
        else:
            frame = pd.DataFrame(
                columns=[
                    "id",
                    "name",
                    "phone_number",
                    "city",
                    "sim_assignment",
                    "is_contacted",
                    "contact_timestamp",
                    "template_used",
                    "lead_status",
                    "reply_notes",
                    "follow_up_date",
                    "priority",
                ]
            )

        rows = [frame.columns.tolist()] + frame.astype(str).values.tolist()
        worksheet = spreadsheet.sheet1
        worksheet.clear()
        try:
            worksheet.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")
        except TypeError:
            worksheet.update("A1", rows, value_input_option="USER_ENTERED")

        if hasattr(st, "toast"):
            st.toast("✅ Database successfully backed up to Vault!", icon="🔒")
    except Exception as exc:
        set_flash(f"Backup failed: {exc}", "error", toast=True)


def render_app_header() -> None:
    """Top app title to mimic the desktop window chrome."""
    st.markdown(
        f'<div class="app-title"><span class="app-badge"></span>{APP_TITLE}</div>',
        unsafe_allow_html=True,
    )


def render_stat_chips(items: list[tuple[str, str, str]]) -> None:
    """Compact inline summary chips."""
    html = []
    for label, value, color in items:
        html.append(
            f'<span class="stat-chip"><span class="stat-dot" style="background:{color};"></span>{label}: {value}</span>'
        )
    st.markdown("".join(html), unsafe_allow_html=True)


def render_leads_tab() -> None:
    """Compact, mobile-first Leads workflow using expanders instead of wide rows."""
    all_leads = get_all_leads()

    filter_left, filter_right = st.columns([3.5, 2])
    with filter_left:
        st.selectbox("Lead Filter", LEAD_FILTERS, key="lead_filter", label_visibility="collapsed")
    with filter_right:
        action_a, action_b, action_c = st.columns(3)
        with action_a:
            with st.popover("Import", use_container_width=True):
                upload = st.file_uploader("Upload CSV", type=["csv"], key="lead_csv_upload")
                if st.button("Import CSV", key="confirm_import", use_container_width=True):
                    import_uploaded_csv(upload)
                    st.rerun()
        with action_b:
            if st.button("Sync to Sheets", key="sync_to_sheets", use_container_width=True):
                sync_primary_sheet_to_app()
                st.rerun()
        with action_c:
            if st.button("📤 Backup Database", key="backup_database", use_container_width=True):
                backup_database_to_sheets()

    filtered_leads = filter_leads(all_leads, st.session_state.get("lead_filter", "Uncontacted"))

    template_choices = get_template_choices()

    render_stat_chips(
        [
            ("Visible", str(len(filtered_leads)), T.ACCENT_PRIMARY),
            ("Contacted", str(sum(1 for lead in all_leads if lead.get("is_contacted"))), T.STATUS_TRUE_TEXT),
            ("Pending", str(sum(1 for lead in all_leads if not lead.get("is_contacted"))), T.STATUS_FALSE_BORDER),
        ]
    )

    if not filtered_leads:
        st.markdown(
            '<div class="surface-card" style="text-align:center; color:#5f6675;">No leads match the current filter.</div>',
            unsafe_allow_html=True,
        )
        return

    for lead in filtered_leads:
        lead_id = lead["id"]
        shop_name = lead.get("name") or "Unnamed Lead"
        city = lead.get("city") or "-"
        phone = lead.get("phone_number") or "-"
        status = derive_status(lead)
        ensure_lead_state(lead, template_choices)
        sim_key = f"sim_assignment_{lead_id}"
        contact_template_key = f"contact_template_{lead_id}"
        contact_message_key = f"contact_message_{lead_id}"

        with st.expander(f"💬 {shop_name} | {city} | {phone}", expanded=False):
            st.markdown(
                f'<span class="status-pill {status_class(status)}">{status}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="lead-meta">SIM: {lead.get("sim_assignment") or "Unassigned"}'
                f' &nbsp;&nbsp; Rating: {lead.get("rating") or "-"}'
                f' &nbsp;&nbsp; Reviews: {lead.get("reviews") or "-"}</div>',
                unsafe_allow_html=True,
            )
            st.selectbox(
                "SIM Assignment",
                ["None", "SIM 1", "SIM 2"],
                key=sim_key,
                on_change=update_sim_callback,
                args=(lead_id, sim_key),
            )

            if not lead.get("is_contacted"):
                st.selectbox(
                    "Message Template",
                    [label for label, _ in template_choices],
                    key=contact_template_key,
                    on_change=sync_contact_message_from_template,
                    args=(lead_id,),
                )
                st.text_area(
                    "Message Template",
                    key=contact_message_key,
                    height=140,
                    placeholder="Write or adjust your Viber outreach message here...",
                )
                viber_link = build_viber_link(phone, st.session_state.get(contact_message_key, ""), lead)
                st.markdown(
                    f'<a href="{viber_link}" target="_blank" class="viber-link">Send on Viber</a>',
                    unsafe_allow_html=True,
                )
                if st.button("Mark Contacted", key=f"mark_contacted_{lead_id}", use_container_width=True):
                    mark_contacted_callback(lead)
                    st.rerun()
            else:
                st.selectbox(
                    "Pipeline Status",
                    [status_value for status_value in PIPELINE_STATUSES if status_value != "Uncontacted"],
                    key=f"reply_status_{lead_id}",
                )
                st.text_area("Reply Notes", key=f"reply_notes_{lead_id}", height=110)
                st.text_input(
                    "Follow-up Date",
                    key=f"follow_up_date_{lead_id}",
                    placeholder="YYYY-MM-DD",
                )
                st.selectbox("Priority", ["Low", "Medium", "High"], key=f"priority_{lead_id}")
                viber_link = build_viber_link(phone, st.session_state.get(f"reply_notes_{lead_id}", ""), lead)
                st.markdown(
                    f'<a href="{viber_link}" target="_blank" class="viber-link">Send on Viber</a>',
                    unsafe_allow_html=True,
                )
                if st.button("Save Update", key=f"save_reply_{lead_id}", use_container_width=True):
                    save_reply_callback(lead)
                    st.rerun()


def render_pipeline_tab() -> None:
    """Kanban-style grouped board, closely following the desktop Pipeline tab."""
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown('<div class="section-title">Pipeline  -  Kanban Board</div>', unsafe_allow_html=True)
    with top_right:
        if st.button("Refresh", key="refresh_pipeline", use_container_width=True):
            st.rerun()

    leads = get_all_leads()
    grouped: dict[str, list[dict]] = {status: [] for status, _, _ in PIPELINE_COLUMNS}
    for lead in leads:
        grouped.setdefault(derive_status(lead), []).append(lead)

    columns = st.columns(len(PIPELINE_COLUMNS))
    for streamlit_col, (status, border_color, text_color) in zip(columns, PIPELINE_COLUMNS, strict=False):
        with streamlit_col:
            st.markdown(
                f"""
                <div class="surface-card" style="padding:0.75rem 0.8rem; margin-bottom:0.6rem;">
                    <div class="table-head" style="margin-bottom:0.2rem; color:{text_color};">{status.upper()}</div>
                    <div class="subtle-note">{len(grouped.get(status, []))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not grouped.get(status):
                st.markdown(
                    '<div class="surface-card" style="text-align:center; color:#5f6675;">Empty</div>',
                    unsafe_allow_html=True,
                )
                continue
            for lead in grouped[status]:
                ensure_lead_state(lead)
                meta_parts = []
                if lead.get("city"):
                    meta_parts.append(lead["city"])
                if lead.get("sim_assignment") and lead["sim_assignment"] != "Unassigned":
                    meta_parts.append(lead["sim_assignment"])
                st.markdown(
                    f"""
                    <div class="kanban-card" style="border-color:{border_color};">
                        <div class="phone-main" style="font-size:1rem;">{lead.get("name") or "Unnamed Lead"}</div>
                        <div style="color:{text_color}; font-size:0.95rem; margin-top:0.35rem;">{lead["phone_number"]}</div>
                        <div class="subtle-note" style="margin-top:0.45rem;">{" · ".join(meta_parts) if meta_parts else "No extra details"}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.selectbox(
                    f"Pipeline stage for {lead['id']}",
                    PIPELINE_STATUSES,
                    key=f"pipeline_status_{lead['id']}",
                    label_visibility="collapsed",
                    on_change=update_pipeline_status_callback,
                    args=(lead,),
                )
                pipeline_message = (
                    st.session_state.get(f"reply_notes_{lead['id']}", "")
                    if lead.get("is_contacted")
                    else st.session_state.get(f"contact_message_{lead['id']}", "")
                )
                st.markdown(
                    f'<a href="{build_viber_link(lead.get("phone_number"), pipeline_message, lead)}" target="_blank" class="viber-link" style="margin-top:0.35rem;">Send on Viber</a>',
                    unsafe_allow_html=True,
                )


def render_tasks_tab() -> None:
    """Follow-up dashboard using the same due-date rules as the desktop version."""
    today = datetime.now().strftime("%Y-%m-%d")
    due_leads = get_all_leads(
        "follow_up_date IS NOT NULL AND date(follow_up_date) <= date(?)",
        (today,),
    )
    due_leads.sort(key=lambda lead: (lead.get("follow_up_date") or "", lead.get("priority") or "Medium"))

    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown('<div class="section-title">Tasks & Follow-ups</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle">Leads whose follow-up date is due today or overdue.</div>',
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("Refresh", key="refresh_tasks", use_container_width=True):
            st.rerun()

    overdue_count = sum(1 for lead in due_leads if (lead.get("follow_up_date") or "") < today)
    today_count = sum(1 for lead in due_leads if (lead.get("follow_up_date") or "") == today)
    render_stat_chips(
        [("Due", str(len(due_leads)), T.ACCENT_PRIMARY), ("Overdue", str(overdue_count), "#c23b22"), ("Due today", str(today_count), "#d4b106")]
    )

    header_cols = st.columns([2, 1.5, 1.2, 1.2, 0.9, 1.1, 1.2])
    for col, label in zip(header_cols, ["LEAD", "PHONE", "CITY", "FOLLOW UP", "PRIORITY", "STATUS", "ACTIONS"], strict=False):
        with col:
            st.markdown(f'<div class="table-head">{label}</div>', unsafe_allow_html=True)

    if not due_leads:
        st.markdown(
            '<div class="surface-card" style="text-align:center; color:#5f6675; margin-top:0.4rem;">No follow-ups are due right now.</div>',
            unsafe_allow_html=True,
        )
        return

    for lead in due_leads:
        ensure_lead_state(lead)
        due_date = lead.get("follow_up_date") or "-"
        status = derive_status(lead)
        row_cols = st.columns([2, 1.5, 1.2, 1.2, 0.9, 1.1, 1.2])
        with row_cols[0]:
            st.markdown(f'<div class="row-shell"><div class="phone-main">{lead.get("name") or "Unnamed Lead"}</div></div>', unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(f'<div class="row-shell"><div class="phone-main" style="font-size:0.96rem;">{lead.get("phone_number") or "-"}</div></div>', unsafe_allow_html=True)
        with row_cols[2]:
            st.markdown(f'<div class="row-shell"><div class="phone-main" style="font-size:0.96rem;">{lead.get("city") or "-"}</div></div>', unsafe_allow_html=True)
        with row_cols[3]:
            color = "#c23b22" if due_date < today else T.TEXT_PRIMARY
            st.markdown(f'<div class="row-shell"><div class="phone-main" style="font-size:0.96rem; color:{color};">{due_date}</div></div>', unsafe_allow_html=True)
        with row_cols[4]:
            priority = lead.get("priority") or "Medium"
            st.markdown(f'<div class="row-shell"><div class="phone-main" style="font-size:0.96rem; color:{PRIORITY_COLORS.get(priority, T.TEXT_SECONDARY)};">{priority}</div></div>', unsafe_allow_html=True)
        with row_cols[5]:
            st.markdown(f'<div class="row-shell"><span class="status-pill {status_class(status)}">{status}</span></div>', unsafe_allow_html=True)
        with row_cols[6]:
            viber_link = build_viber_link(
                lead.get("phone_number"),
                st.session_state.get(f"reply_notes_{lead['id']}", ""),
                lead,
            )
            st.markdown(
                f'<a href="{viber_link}" target="_blank" class="viber-link" style="margin-top:0;">Open Viber</a>',
                unsafe_allow_html=True,
            )
            with st.popover("Manage", use_container_width=True):
                st.selectbox(
                    "Pipeline Status",
                    PIPELINE_STATUSES,
                    key=f"reply_status_{lead['id']}",
                )
                st.text_area("Reply Notes", key=f"reply_notes_{lead['id']}", height=100)
                st.text_input(
                    "Follow-up Date",
                    key=f"follow_up_date_{lead['id']}",
                    placeholder="YYYY-MM-DD or blank to clear",
                )
                st.selectbox("Priority", ["Low", "Medium", "High"], key=f"priority_{lead['id']}")
                if st.button(f"Save Task {lead['id']}", key=f"save_task_{lead['id']}", use_container_width=True):
                    apply_lead_update(
                        lead,
                        status=st.session_state.get(f"reply_status_{lead['id']}", derive_status(lead)),
                        notes=st.session_state.get(f"reply_notes_{lead['id']}", ""),
                        follow_up_date=st.session_state.get(f"follow_up_date_{lead['id']}", ""),
                        priority=st.session_state.get(f"priority_{lead['id']}", lead.get("priority") or "Medium"),
                        success_message="Task updated.",
                    )
                    st.rerun()
                if st.button(f"Clear Follow-up {lead['id']}", key=f"clear_follow_up_{lead['id']}", use_container_width=True):
                    st.session_state[f"follow_up_date_{lead['id']}"] = ""
                    apply_lead_update(
                        lead,
                        status=st.session_state.get(f"reply_status_{lead['id']}", derive_status(lead)),
                        notes=st.session_state.get(f"reply_notes_{lead['id']}", ""),
                        follow_up_date="",
                        priority=st.session_state.get(f"priority_{lead['id']}", lead.get("priority") or "Medium"),
                        success_message="Follow-up cleared.",
                    )
                    st.rerun()


def sync_template_editor(template: dict | None) -> None:
    """Push a selected template into the editor state."""
    if template is None:
        st.session_state.current_selected_template = None
        st.session_state.selected_template_id = None
        st.session_state.template_form_name = ""
        st.session_state.template_form_category = "General"
        st.session_state.template_form_body = ""
    else:
        st.session_state.current_selected_template = template["id"]
        st.session_state.selected_template_id = template["id"]
        st.session_state.template_form_name = template.get("name") or ""
        st.session_state.template_form_category = template.get("category") or "General"
        st.session_state.template_form_body = template.get("body") or ""


def render_templates_tab() -> None:
    """Template CRUD layout inspired by the desktop split pane."""
    templates = get_all_templates()
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown('<div class="section-title">Template Library</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-subtitle">{len(templates)} templates available</div>', unsafe_allow_html=True)
    with top_right:
        if st.button("New Template", key="new_template_btn", use_container_width=True):
            sync_template_editor(None)
            st.rerun()

    list_col, editor_col = st.columns([1.1, 1.5])
    with list_col:
        st.markdown('<div class="surface-card"><div class="section-title" style="font-size:1rem;">Saved Templates</div></div>', unsafe_allow_html=True)
        if not templates:
            st.markdown('<div class="surface-card" style="margin-top:0.6rem; text-align:center; color:#5f6675;">No templates saved yet.</div>', unsafe_allow_html=True)
        for template in templates:
            is_selected = template["id"] == st.session_state.get("current_selected_template")
            border = T.ACCENT_PRIMARY if is_selected else T.BORDER_DEFAULT
            st.markdown(
                f"""
                <div class="surface-card" style="margin-top:0.55rem; border-color:{border};">
                    <div class="phone-main" style="font-size:1rem;">{template["name"]}</div>
                    <div class="subtle-note">ID {template["id"]}  |  {template.get("category") or "General"}  |  Used {template.get("usage_count", 0)} times</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f'Open "{template["name"]}"',
                key=f"select_template_{template['id']}",
                use_container_width=True,
            ):
                sync_template_editor(template)
                st.rerun()

    with editor_col:
        st.markdown('<div class="surface-card"><div class="section-title" style="font-size:1rem;">Template Editor</div></div>', unsafe_allow_html=True)
        st.text_input("Template Name", key="template_form_name")
        st.text_input("Category", key="template_form_category")
        st.caption("You can use dynamic placeholders like {Shop Name} or {City} inside the message body.")
        st.text_area("Body", key="template_form_body", height=420)
        st.caption(
            "Create a new template or select one from the list."
            if st.session_state.get("current_selected_template") is None
            else f"Editing template #{st.session_state['current_selected_template']}"
        )
        action_left, action_right = st.columns([1, 1.2])
        with action_left:
            disabled = st.session_state.get("current_selected_template") is None
            if st.button("Delete", key="delete_template", disabled=disabled, use_container_width=True):
                delete_template(st.session_state["current_selected_template"])
                sync_template_editor(None)
                set_flash("Template deleted.")
                st.rerun()
        with action_right:
            if st.button("Save Template", key="save_template_btn", use_container_width=True):
                name = st.session_state.get("template_form_name", "").strip()
                category = st.session_state.get("template_form_category", "").strip() or "General"
                body = st.session_state.get("template_form_body", "").strip()
                if not name:
                    set_flash("Template name is required.", "error")
                    st.rerun()
                if not body:
                    set_flash("Template body cannot be empty.", "error")
                    st.rerun()
                if st.session_state.get("current_selected_template") is None:
                    add_template(name, body, category)
                    sync_template_editor(None)
                    set_flash(f'Created template "{name}".')
                else:
                    update_template(st.session_state["current_selected_template"], name, body, category)
                    st.session_state.template_form_name = name
                    st.session_state.template_form_category = category
                    st.session_state.template_form_body = body
                    set_flash(f'Updated template "{name}".')
                st.rerun()


def render_metric_card(label: str, value: str) -> None:
    """Small metric panel for Analytics."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analytics_tab() -> None:
    """Analytics dashboard based on DailyStats."""
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown('<div class="section-title">Analytics Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Messages sent vs. calls booked across recent DailyStats records.</div>', unsafe_allow_html=True)
    with top_right:
        if st.button("Refresh", key="refresh_analytics", use_container_width=True):
            st.rerun()

    stats = list(reversed(get_daily_stats(limit=14)))
    tracked_days = len(stats)
    total_messages = sum(item.get("messages_sent", 0) or 0 for item in stats)
    total_calls = sum(item.get("calls_booked", 0) or 0 for item in stats)
    conversion = (total_calls / total_messages * 100) if total_messages else 0

    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_metric_card("Tracked Days", str(tracked_days))
    with metric_cols[1]:
        render_metric_card("Messages Sent", str(total_messages))
    with metric_cols[2]:
        render_metric_card("Calls Booked", str(total_calls))
    with metric_cols[3]:
        render_metric_card("Conversion", f"{conversion:.1f}%")

    st.write("")
    st.markdown('<div class="surface-card"><div class="section-title" style="font-size:1rem;">Recent Performance</div></div>', unsafe_allow_html=True)
    if not stats:
        st.markdown('<div class="surface-card" style="margin-top:0.55rem; text-align:center; color:#5f6675;">No DailyStats data yet.</div>', unsafe_allow_html=True)
        return

    chart = (
        alt.Chart(
            alt.Data(
                values=[
                    {"date": item.get("date", "-"), "metric": "Messages Sent", "value": item.get("messages_sent", 0) or 0}
                    for item in stats
                ] + [
                    {"date": item.get("date", "-"), "metric": "Calls Booked", "value": item.get("calls_booked", 0) or 0}
                    for item in stats
                ]
            )
        )
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("date:N", title=""),
            y=alt.Y("value:Q", title=""),
            color=alt.Color(
                "metric:N",
                scale=alt.Scale(domain=["Messages Sent", "Calls Booked"], range=["#A970FF", "#00E676"]),
                legend=alt.Legend(title=None, orient="top-right"),
            ),
            xOffset="metric:N",
            tooltip=["date:N", "metric:N", "value:Q"],
        )
        .properties(height=420)
        .configure(background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(
            gridColor="#2b3038",
            gridOpacity=0.18,
            domainColor="#2b3038",
            tickColor="#2b3038",
            labelColor=T.TEXT_SECONDARY,
            titleColor=T.TEXT_SECONDARY,
        )
        .configure_legend(
            labelColor=T.TEXT_PRIMARY,
            titleColor=T.TEXT_PRIMARY,
            symbolType="square",
        )
    )
    st.altair_chart(chart, use_container_width=True)


def load_settings_into_state() -> None:
    """Pull settings from the database into session state."""
    values = {}
    for key, _, _ in SETTINGS_FIELDS:
        raw_value = get_setting(key, SETTINGS_DEFAULTS.get(key, "")) or ""
        if key in NUMERIC_SETTING_KEYS:
            try:
                parsed_value = int(raw_value)
            except (TypeError, ValueError):
                parsed_value = int(SETTINGS_DEFAULTS.get(key, 0))
            values[key] = parsed_value
        else:
            values[key] = str(raw_value)
        st.session_state[f"settings_input_{key}"] = values[key]
    st.session_state.settings_values = values


def save_settings_from_state() -> None:
    """Persist settings after basic validation."""
    values = st.session_state.get("settings_values", {})
    cleaned_values = {}
    for key, value in values.items():
        if key in NUMERIC_SETTING_KEYS:
            cleaned_values[key] = max(0, int(value))
        else:
            cleaned_values[key] = str(value).strip()
        set_setting(key, str(cleaned_values[key]))
    st.session_state.settings_values = cleaned_values
    if hasattr(st, "toast"):
        st.toast("✅ Settings saved successfully!", icon="💾")


def render_settings_tab() -> None:
    """Settings editor matching the desktop layout."""
    if not st.session_state.get("settings_values"):
        load_settings_into_state()

    top_left, top_right = st.columns([5, 1.4])
    with top_left:
        st.markdown('<div class="section-title">Settings</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Edit saved configuration values from the Settings table.</div>', unsafe_allow_html=True)
    with top_right:
        reload_col, save_col = st.columns(2)
        with reload_col:
            if st.button("Reload", key="reload_settings", use_container_width=True):
                load_settings_into_state()
                st.rerun()
        with save_col:
            if st.button("Save", key="save_settings", use_container_width=True):
                save_settings_from_state()

    for key, label, help_text in SETTINGS_FIELDS:
        current_value = st.session_state.settings_values.get(key, "")
        if key in NUMERIC_SETTING_KEYS:
            updated_value = st.number_input(
                label,
                min_value=0,
                step=1,
                key=f"settings_input_{key}",
            )
        else:
            updated_value = st.text_input(label, value=current_value, key=f"settings_input_{key}")
        st.session_state.settings_values[key] = updated_value
        st.caption(help_text)


def main() -> None:
    """Render the full multi-tab Streamlit CRM."""
    init_db()
    init_state()
    apply_styles()
    maybe_require_password()

    render_app_header()
    show_flash()

    tabs = st.tabs(TAB_LABELS)
    with tabs[0]:
        render_leads_tab()
    with tabs[1]:
        render_pipeline_tab()
    with tabs[2]:
        render_tasks_tab()
    with tabs[3]:
        render_templates_tab()
    with tabs[4]:
        render_analytics_tab()
    with tabs[5]:
        render_settings_tab()


if __name__ == "__main__":
    main()
