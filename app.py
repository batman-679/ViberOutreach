"""Streamlit mobile-first CRM backed by Google Sheets.

Required Streamlit secrets:

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"

app_password = "your-secret-password"
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import gspread
import pandas as pd
import streamlit as st

APP_TITLE = "Viber Outreach Manager"
SPREADSHEET_NAME = "Viber Outreach Sync"
PLACEHOLDER_TEMPLATES = {
    "Cold Intro": (
        "Hi, I came across your business and wanted to reach out quickly. "
        "I help local brands generate more qualified leads through direct outreach."
    ),
    "Follow-Up Offer": (
        "Following up in case my last message got buried. "
        "I have a simple idea that could help you bring in more customer conversations this month."
    ),
    "Short CTA": (
        "Would you be open to a quick 10-minute chat this week to see if this could fit your business?"
    ),
}


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":telephone_receiver:",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def apply_styles() -> None:
    """Add light CSS polish while staying compatible with Streamlit dark mode."""
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 760px;
                padding-top: 1.2rem;
                padding-bottom: 3rem;
            }

            .hero-box,
            .template-box {
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 18px;
                padding: 1rem 1rem 1.1rem 1rem;
                background: rgba(255, 255, 255, 0.03);
            }

            .hero-kicker {
                color: #7360F2;
                font-size: 0.82rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }

            .hero-title {
                font-size: 1.75rem;
                font-weight: 800;
                line-height: 1.1;
                margin-bottom: 0.4rem;
            }

            .hero-copy,
            .card-meta {
                opacity: 0.84;
                line-height: 1.45;
            }

            .lead-pill {
                display: inline-block;
                margin: 0.35rem 0.4rem 0.2rem 0;
                padding: 0.2rem 0.65rem;
                border-radius: 999px;
                background: rgba(115, 96, 242, 0.14);
                border: 1px solid rgba(115, 96, 242, 0.38);
                color: #ddd8ff;
                font-size: 0.78rem;
                font-weight: 700;
            }

            .viber-link {
                display: block;
                width: 100%;
                margin: 0.85rem 0 0.7rem 0;
                padding: 0.95rem 1rem;
                text-align: center;
                text-decoration: none;
                border-radius: 16px;
                background: #7360F2;
                color: white !important;
                font-size: 1rem;
                font-weight: 800;
                box-shadow: 0 10px 26px rgba(115, 96, 242, 0.35);
            }

            .viber-link:hover {
                background: #8B7CF6;
            }

            .stButton > button {
                width: 100%;
                min-height: 2.8rem;
                border-radius: 14px;
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def login_gate() -> None:
    """Show a password screen and block the rest of the app until authenticated."""
    if st.session_state.get("authenticated") is True:
        return

    st.markdown(
        f"""
        <div class="hero-box">
            <div class="hero-kicker">Private Access</div>
            <div class="hero-title">{APP_TITLE}</div>
            <div class="hero-copy">Enter the password to open the mobile CRM.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    password = st.text_input("Password", type="password", placeholder="Enter app password")
    if st.button("Enter", use_container_width=True):
        if password == st.secrets["app_password"]:
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Incorrect password.")

    st.stop()


def init_connection() -> gspread.Spreadsheet:
    """Create a Google Sheets connection using Streamlit secrets."""
    client = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    return client.open(SPREADSHEET_NAME)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_leads() -> pd.DataFrame:
    """Load lead data from Google Sheets into a DataFrame and cache it briefly."""
    worksheet = init_connection().sheet1
    records = worksheet.get_all_records()
    frame = pd.DataFrame(records)

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "Shop Name",
                "City",
                "Phone",
                "Rating",
                "Reviews",
                "Status",
                "Contacted_At",
                "_row_index",
            ]
        )

    frame = frame.fillna("")
    frame["_row_index"] = [row_number for row_number in range(2, len(frame) + 2)]
    return frame


def normalize_phone(phone_number: object) -> str:
    """Strip a phone number down to digits and an optional leading + for Viber."""
    return "".join(char for char in str(phone_number) if char.isdigit() or char == "+")


def find_first_column(columns: Iterable[str], candidates: list[str]) -> str | None:
    """Return the first matching column name from a list of possible aliases."""
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        match = lowered.get(candidate.lower())
        if match:
            return match
    return None


def resolve_columns(frame: pd.DataFrame) -> tuple[str, str, str, str, str | None, str | None]:
    """Resolve the columns this app needs and stop early if the sheet shape is invalid."""
    shop_col = find_first_column(frame.columns, ["Shop Name", "Name", "Shop"])
    city_col = find_first_column(frame.columns, ["City"])
    phone_col = find_first_column(frame.columns, ["Phone", "Phone Number", "Phone_Number"])
    status_col = find_first_column(frame.columns, ["Status"])
    rating_col = find_first_column(frame.columns, ["Rating"])
    reviews_col = find_first_column(frame.columns, ["Reviews", "Review Count"])

    missing = []
    if not shop_col:
        missing.append("Shop Name")
    if not city_col:
        missing.append("City")
    if not phone_col:
        missing.append("Phone")
    if not status_col:
        missing.append("Status")

    if missing:
        st.error(
            "Your Google Sheet is missing required columns: " + ", ".join(missing) + ". "
            "Expected at minimum: Shop Name, City, Phone, Status."
        )
        st.stop()

    return shop_col, city_col, phone_col, status_col, rating_col, reviews_col


def mark_contacted(row_index: int) -> None:
    """Mark a lead as contacted and stamp the current timestamp in Google Sheets."""
    worksheet = init_connection().sheet1
    headers = worksheet.row_values(1)

    if "Status" not in headers or "Contacted_At" not in headers:
        st.error("The sheet must contain both 'Status' and 'Contacted_At' columns.")
        st.stop()

    status_col_index = headers.index("Status") + 1
    contacted_at_col_index = headers.index("Contacted_At") + 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    worksheet.update_cell(row_index, status_col_index, "True")
    worksheet.update_cell(row_index, contacted_at_col_index, timestamp)

    fetch_leads.clear()


def refresh_leads() -> None:
    """Manually clear the cached sheet data so the next read is fresh."""
    fetch_leads.clear()


def logout() -> None:
    """Clear the authenticated session and return to the password gate."""
    st.session_state["authenticated"] = False
    st.session_state.pop("flash_message", None)


def render_templates() -> None:
    """Show the sales template picker and copy-friendly text block."""
    st.markdown('<div class="template-box">', unsafe_allow_html=True)
    st.subheader("Templates")
    selected_template = st.selectbox(
        "Choose a sales template",
        options=list(PLACEHOLDER_TEMPLATES.keys()),
        key="selected_template",
    )
    st.code(PLACEHOLDER_TEMPLATES[selected_template], language="text")
    st.caption("Tap the code block on mobile to copy the template into your clipboard workflow.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_top_actions() -> None:
    """Render quick mobile actions for refreshing data and logging out."""
    left, right = st.columns(2)
    with left:
        if st.button("Sync/Refresh", use_container_width=True):
            refresh_leads()
            st.session_state["flash_message"] = "Lead list refreshed from Google Sheets."
            st.rerun()
    with right:
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()


def render_lead_card(
    row: pd.Series,
    shop_col: str,
    city_col: str,
    phone_col: str,
    rating_col: str | None,
    reviews_col: str | None,
) -> None:
    """Render one lead as a mobile-friendly action card."""
    shop_name = str(row.get(shop_col, "")).strip() or "Unnamed Shop"
    city = str(row.get(city_col, "")).strip() or "Unknown City"
    phone_raw = str(row.get(phone_col, "")).strip()
    rating = str(row.get(rating_col, "")).strip() if rating_col else ""
    reviews = str(row.get(reviews_col, "")).strip() if reviews_col else ""
    phone_number = normalize_phone(phone_raw)
    row_index = int(row["_row_index"])

    with st.expander(f"{shop_name} - {city}", expanded=False):
        meta_pills = [f'<span class="lead-pill">{city}</span>']
        if rating:
            meta_pills.append(f'<span class="lead-pill">Rating: {rating}</span>')
        if reviews:
            meta_pills.append(f'<span class="lead-pill">Reviews: {reviews}</span>')
        meta_pills.append(f'<span class="lead-pill">{phone_raw or "No Phone"}</span>')

        st.markdown(
            f"""
            <div class="card-meta">
                {"".join(meta_pills)}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write(f"**Shop:** {shop_name}")
        st.write(f"**City:** {city}")
        if rating:
            st.write(f"**Rating:** {rating}")
        if reviews:
            st.write(f"**Reviews:** {reviews}")
        st.write(f"**Phone:** {phone_raw or 'N/A'}")

        if phone_number:
            st.markdown(
                f'<a href="viber://chat?number={phone_number}" target="_blank" class="viber-link">💬 Message on Viber</a>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("This lead does not have a valid phone number for a Viber deep link.")

        if st.button("Mark Contacted", key=f"mark_contacted_{row_index}", use_container_width=True):
            mark_contacted(row_index)
            st.session_state["flash_message"] = f"{shop_name} marked as contacted."
            st.rerun()


def main() -> None:
    """App entry point."""
    apply_styles()
    login_gate()

    st.markdown(
        f"""
        <div class="hero-box">
            <div class="hero-kicker">Mobile CRM</div>
            <div class="hero-title">{APP_TITLE}</div>
            <div class="hero-copy">
                Pick a template, tap the Viber deep link, and mark the lead contacted when done.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    render_top_actions()
    st.write("")

    render_templates()
    st.write("")

    try:
        leads = fetch_leads()
    except Exception as exc:
        st.error(f"Unable to load Google Sheet data: {exc}")
        st.stop()

    if leads.empty:
        st.info("No leads found in the Google Sheet yet.")
        return

    shop_col, city_col, phone_col, status_col, rating_col, reviews_col = resolve_columns(leads)

    if st.session_state.get("flash_message"):
        st.success(st.session_state.pop("flash_message"))

    status_series = leads[status_col].astype(str).str.strip().str.lower()
    uncontacted = leads.loc[~status_series.isin({"true", "1", "yes"})].copy()

    st.subheader("Uncontacted Leads")
    st.caption(f"{len(uncontacted)} leads ready for outreach.")

    if uncontacted.empty:
        st.info("All visible leads are already marked as contacted.")
        return

    for _, row in uncontacted.iterrows():
        render_lead_card(row, shop_col, city_col, phone_col, rating_col, reviews_col)


if __name__ == "__main__":
    main()
