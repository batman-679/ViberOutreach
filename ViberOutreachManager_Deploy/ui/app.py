"""
ui/app.py
Streamlit dashboard for the Instagram Graph API CRM.

Three tabs:
  1. 💬 Inbox    — contact list + chat thread + reply composer
  2. 📋 Pipeline — 5-column Kanban board
  3. ✂️ Snippets  — CRUD manager for reply snippets

Auto-refreshes every 30 s via st.rerun() so countdown timers stay live.
"""

import time
import sys
import os

import streamlit as st

# ── sys.path fix: allow running from any cwd ──────────────────────────────────
# Streamlit is launched with: streamlit run ui/app.py
# The project root must be on sys.path so imports like `from core.database`
# work regardless of which directory Streamlit was invoked from.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.database import (
    init_db,
    get_contacts,
    get_thread,
    update_pipeline_stage,
    get_snippets,
    save_snippet,
    delete_snippet,
    save_message,
    upsert_contact,
    import_scraped_leads,
)
from core.instagram_api import send_message
from ui.components import format_countdown, render_message_bubble, render_pipeline_card
from config.settings import MESSAGING_WINDOW_HOURS

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Instagram CRM",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Global dark theme tweaks */
    .stApp { background-color: #0d0d1a; color: #e0e0e0; }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* Contact list row */
    .contact-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 12px; border-radius: 8px; margin-bottom: 4px;
        background: #1a1a2e; cursor: pointer; border: 1px solid #2a2a3e;
        transition: background 0.15s;
    }
    .contact-row:hover { background: #252538; }
    .contact-name { font-weight: 600; font-size: 14px; }

    /* Chat container */
    .chat-container {
        height: 480px; overflow-y: auto; padding: 12px;
        background: #111120; border-radius: 12px;
        border: 1px solid #2a2a3e; margin-bottom: 12px;
    }

    /* Snippet dropdown label */
    .snippet-label { font-size: 12px; color: #888; margin-bottom: 4px; }

    /* Kanban column header */
    .kanban-header {
        text-align: center; font-weight: 700; font-size: 13px;
        padding: 6px; margin-bottom: 10px; border-radius: 8px;
        background: #1a1a2e; border: 1px solid #2a2a3e;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Initialise DB and session state
# ─────────────────────────────────────────────────────────────────────────────

init_db()

if "selected_contact_id" not in st.session_state:
    st.session_state["selected_contact_id"] = None

if "snippet_text" not in st.session_state:
    st.session_state["snippet_text"] = ""

if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# Auto-refresh every 30 seconds (safe loop — no busy-waiting)
# ─────────────────────────────────────────────────────────────────────────────

_REFRESH_INTERVAL = 30  # seconds

def _schedule_rerun():
    """Call st.rerun() only after REFRESH_INTERVAL seconds have elapsed."""
    now = time.time()
    if now - st.session_state["last_refresh"] >= _REFRESH_INTERVAL:
        st.session_state["last_refresh"] = now
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## 📸 Instagram CRM", unsafe_allow_html=False)

tab_inbox, tab_pipeline, tab_snippets, tab_import = st.tabs(["💬 Inbox", "📋 Pipeline", "✂️ Snippets", "📥 Import"])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — INBOX
# ═════════════════════════════════════════════════════════════════════════════

with tab_inbox:
    contacts = get_contacts()

    col_list, col_thread = st.columns([1, 2], gap="medium")

    # ── Left panel: contact list ──────────────────────────────────────────────
    with col_list:
        st.markdown("### Contacts")

        if not contacts:
            st.info("No contacts yet. Send a message on Instagram to populate this list.")
        else:
            for contact in contacts:
                cid = contact["id"]
                display_name = contact.get("ig_username") or contact.get("igsid", "Unknown")
                time_str, is_open = format_countdown(contact.get("last_inbound_at"))

                # Color the badge
                if not is_open:
                    badge_color = "#e74c3c"
                elif time_str.startswith("0"):
                    badge_color = "#f39c12"
                else:
                    badge_color = "#2ecc71"

                is_selected = st.session_state["selected_contact_id"] == cid
                btn_label = f"{'▶ ' if is_selected else ''}{display_name}"

                if st.button(btn_label, key=f"contact_{cid}", use_container_width=True):
                    st.session_state["selected_contact_id"] = cid
                    st.session_state["snippet_text"] = ""
                    st.rerun()

                st.markdown(
                    f'<div style="text-align:right; margin-top:-10px; margin-bottom:8px;">'
                    f'<span style="background:{badge_color}22; color:{badge_color}; '
                    f'border:1px solid {badge_color}; border-radius:10px; '
                    f'padding:1px 8px; font-size:11px; font-family:monospace;">'
                    f'{time_str}</span></div>',
                    unsafe_allow_html=True,
                )

    # ── Right panel: thread + reply composer ─────────────────────────────────
    with col_thread:
        selected_id = st.session_state["selected_contact_id"]

        if selected_id is None:
            st.markdown(
                '<div style="text-align:center; padding:80px; color:#444;">'
                '← Select a contact to view the conversation</div>',
                unsafe_allow_html=True,
            )
        else:
            # Find the contact
            contact_data = next(
                (c for c in contacts if c["id"] == selected_id), None
            )
            if not contact_data:
                st.warning("Contact not found.")
            else:
                display_name = (
                    contact_data.get("ig_username") or contact_data.get("igsid", "Unknown")
                )
                time_str, is_open = format_countdown(
                    contact_data.get("last_inbound_at")
                )

                st.markdown(f"### {display_name}")
                if is_open:
                    st.success(f"✅ Window open · {time_str} remaining")
                else:
                    st.error(f"🔒 {time_str}")

                # ── Chat thread ───────────────────────────────────────────────
                thread = get_thread(selected_id)
                bubble_html = "".join(render_message_bubble(m) for m in thread)
                if not bubble_html:
                    bubble_html = '<div style="color:#555; text-align:center; padding:40px;">No messages yet</div>'

                st.markdown(
                    f'<div class="chat-container">{bubble_html}</div>',
                    unsafe_allow_html=True,
                )

                # ── Reply composer ────────────────────────────────────────────
                st.divider()

                # Snippets dropdown
                snippets = get_snippets()
                snippet_names = ["— Select a snippet —"] + [s["name"] for s in snippets]
                chosen_snippet = st.selectbox(
                    "📎 Insert Snippet",
                    options=snippet_names,
                    key=f"snippet_select_{selected_id}",
                )

                # Auto-fill text area when a snippet is chosen
                default_text = st.session_state.get("snippet_text", "")
                if chosen_snippet != "— Select a snippet —":
                    matched = next(
                        (s for s in snippets if s["name"] == chosen_snippet), None
                    )
                    if matched:
                        default_text = matched["body"]
                        st.session_state["snippet_text"] = default_text

                reply_text = st.text_area(
                    "Reply",
                    value=default_text,
                    height=100,
                    placeholder="Type your message…",
                    key=f"reply_text_{selected_id}",
                    disabled=not is_open,
                )

                if not is_open:
                    st.warning(
                        "⚠️ 24-Hour Messaging Window Closed. "
                        "You cannot send messages until this user contacts you again."
                    )

                send_col, _ = st.columns([1, 3])
                with send_col:
                    send_clicked = st.button(
                        "📤 Send Reply",
                        disabled=not is_open,
                        use_container_width=True,
                        key=f"send_{selected_id}",
                    )

                if send_clicked and reply_text.strip():
                    igsid = contact_data["igsid"]
                    try:
                        success, resp = send_message(igsid, reply_text.strip())
                        if success:
                            # Persist outbound message locally so it appears immediately
                            mid = resp.get("message_id")
                            from datetime import datetime
                            save_message(
                                selected_id, mid, "outbound",
                                reply_text.strip(), datetime.utcnow()
                            )
                            st.session_state["snippet_text"] = ""
                            st.success("Message sent!")
                            st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — PIPELINE (Kanban)
# ═════════════════════════════════════════════════════════════════════════════

STAGES = ["New Lead", "Contacted", "Negotiating", "Converted", "Archived"]

with tab_pipeline:
    st.markdown("### 📋 Pipeline")

    contacts = get_contacts()  # fresh fetch
    kanban_cols = st.columns(len(STAGES), gap="small")

    for col, stage in zip(kanban_cols, STAGES):
        stage_contacts = [c for c in contacts if c.get("pipeline_stage") == stage]
        with col:
            st.markdown(
                f'<div class="kanban-header">{stage}<br>'
                f'<span style="font-weight:400; font-size:11px; color:#888;">'
                f'{len(stage_contacts)} contact{"s" if len(stage_contacts) != 1 else ""}'
                f'</span></div>',
                unsafe_allow_html=True,
            )

            if not stage_contacts:
                st.markdown(
                    '<div style="color:#444; font-size:12px; text-align:center; '
                    'padding:16px;">Empty</div>',
                    unsafe_allow_html=True,
                )
            else:
                for contact in stage_contacts:
                    cid = contact["id"]
                    display_name = (
                        contact.get("ig_username") or contact.get("igsid", "Unknown")
                    )
                    st.markdown(render_pipeline_card(contact), unsafe_allow_html=True)

                    # Stage selector
                    new_stage = st.selectbox(
                        f"Move {display_name}",
                        options=STAGES,
                        index=STAGES.index(stage),
                        key=f"pipeline_stage_{cid}",
                        label_visibility="collapsed",
                    )
                    if new_stage != stage:
                        update_pipeline_stage(cid, new_stage)
                        st.rerun()

                    # Quick-nav to Inbox
                    if st.button(
                        "Open in Inbox →",
                        key=f"open_inbox_{cid}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_contact_id"] = cid
                        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — SNIPPETS
# ═════════════════════════════════════════════════════════════════════════════

with tab_snippets:
    st.markdown("### ✂️ Snippets Manager")
    st.caption("Save frequently used reply templates for quick access in the Inbox.")

    # ── Create new snippet ────────────────────────────────────────────────────
    with st.expander("➕ Add New Snippet", expanded=True):
        new_name = st.text_input("Snippet Name (short label)", key="new_snippet_name")
        new_body = st.text_area("Message Body", height=120, key="new_snippet_body")

        if st.button("💾 Save Snippet", key="save_snippet_btn"):
            if not new_name.strip():
                st.error("Please enter a snippet name.")
            elif not new_body.strip():
                st.error("Please enter a message body.")
            else:
                save_snippet(new_name.strip(), new_body.strip())
                st.success(f'Snippet "{new_name.strip()}" saved!')
                st.rerun()

    st.divider()

    # ── List existing snippets ────────────────────────────────────────────────
    snippets = get_snippets()
    if not snippets:
        st.info("No snippets yet. Create one above.")
    else:
        st.markdown(f"**{len(snippets)} snippet{'s' if len(snippets) != 1 else ''}**")
        for snippet in snippets:
            with st.container():
                row_col, del_col = st.columns([5, 1])
                with row_col:
                    st.markdown(f"**{snippet['name']}**")
                    st.caption(snippet["body"][:120] + ("…" if len(snippet["body"]) > 120 else ""))
                with del_col:
                    if st.button("🗑️", key=f"del_snippet_{snippet['id']}", help="Delete snippet"):
                        st.rerun()
                st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — IMPORT
# ═════════════════════════════════════════════════════════════════════════════

with tab_import:
    st.markdown("### 📥 Import Scraped Leads")
    st.caption("Bring in Instagram profiles from your Lead Scraper database.")
    
    scraper_path = "C:/IG_scraper/scraped_leads.db"
    st.info(f"Target Scraper Database: `{scraper_path}`")
    
    if st.button("📥 Import Scraped Leads", use_container_width=True, type="primary"):
        with st.spinner("Connecting to scraper database..."):
            new_leads_count = import_scraped_leads(scraper_path)
            
        if new_leads_count > 0:
            st.success(f"✅ Successfully imported {new_leads_count} new leads!")
            # Brief pause to acknowledge success before refresh
            time.sleep(1.5)
            st.rerun()
        else:
            st.info("No new leads found. All scraped leads may already be imported, or the database is empty.")

# ─────────────────────────────────────────────────────────────────────────────
# Trigger auto-refresh (must be last, after all widgets are rendered)
# ─────────────────────────────────────────────────────────────────────────────

_schedule_rerun()
