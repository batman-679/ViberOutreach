import webbrowser
import customtkinter as ctk
import theme as T
from core.database import (
    get_all_leads,
    update_sim_assignment,
    update_contact_status,
    update_lead_reply,
)
from ui.popups import TemplatePromptPopup, ReplyPopup

# ---------- colour map for pipeline statuses ----------
STATUS_STYLES = {
    "Uncontacted": {
        "fg": T.STATUS_FALSE_BG,  "hover": "#333333",
        "border": T.STATUS_FALSE_BORDER, "border_w": 1,
        "text_color": T.STATUS_FALSE_TEXT, "label": "○  False",
    },
    "Contacted": {
        "fg": T.STATUS_TRUE_BG,   "hover": T.STATUS_TRUE_HOVER,
        "border": T.STATUS_TRUE_BORDER,  "border_w": 1,
        "text_color": T.STATUS_TRUE_TEXT, "label": "✓  Contacted",
    },
    "Replied": {
        "fg": "#332D00",          "hover": "#443D00",
        "border": "#d4b106",      "border_w": 1,
        "text_color": "#d4b106",  "label": "✓  Replied",
    },
    "Call Booked": {
        "fg": "#003322",          "hover": "#004433",
        "border": "#00a86b",      "border_w": 1,
        "text_color": "#00a86b",  "label": "✓  Call Booked",
    },
    "Rejected": {
        "fg": "#330D08",          "hover": "#441510",
        "border": "#c23b22",      "border_w": 1,
        "text_color": "#c23b22",  "label": "✗  Rejected",
    },
}


class DashboardFrame(ctk.CTkFrame):
    """Scrollable lead table + stats bar, fully themed."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.pack(fill="both", expand=True)

        self._filter_q = None
        self._filter_p = ()

        # ── Column header row ──
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.pack(fill="x", padx=T.PAD_LG)
        for col, (title, w) in enumerate([
            ("PHONE NUMBER", 170), ("CITY", 130), ("SIM CARD", 140), ("STATUS", 120),
        ]):
            ctk.CTkLabel(
                self._header, text=title, width=w, anchor="w",
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=10, weight="bold"),
                text_color=T.TEXT_MUTED,
            ).pack(side="left", padx=T.PAD_SM)

        # ── Separator ──
        ctk.CTkFrame(self, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=T.PAD_BASE, pady=(0, T.PAD_SM))

        # ── Scrollable list area ──
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=T.ACCENT_MUTED,
            scrollbar_button_hover_color=T.ACCENT_PRIMARY,
        )
        self._scroll.pack(fill="both", expand=True, padx=T.PAD_SM, pady=(0, 0))

        # ── Stats bar at the bottom ──
        self._stats = ctk.CTkFrame(self, height=32, fg_color=T.BG_ROOT, corner_radius=0)
        self._stats.pack(fill="x", side="bottom")
        self._stats.pack_propagate(False)

        self._stat_total = self._make_stat(self._stats, T.ACCENT_PRIMARY, "Total: 0")
        self._stat_yes   = self._make_stat(self._stats, T.STATUS_TRUE_TEXT, "Contacted: 0")
        self._stat_no    = self._make_stat(self._stats, T.STATUS_FALSE_BORDER, "Pending: 0")

        self.load_leads()

    # ── helpers ──
    @staticmethod
    def _make_stat(parent, dot_color, text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=T.PAD_MD, pady=4)
        ctk.CTkFrame(f, width=6, height=6, corner_radius=3, fg_color=dot_color).pack(side="left", padx=(0, 5))
        lbl = ctk.CTkLabel(f, text=text, font=ctk.CTkFont(family=T.FONT_FAMILY, size=11), text_color=T.TEXT_MUTED)
        lbl.pack(side="left")
        return lbl

    # ── clear / load ──
    def _clear(self):
        for w in self._scroll.winfo_children():
            w.destroy()

    def load_leads(self, filter_query=None, filter_params=()):
        if filter_query is not None:
            self._filter_q = filter_query
            self._filter_p = filter_params
        self._clear()
        leads = get_all_leads(self._filter_q, self._filter_p)

        if not leads:
            ctk.CTkLabel(
                self._scroll, text="No leads match this filter",
                text_color=T.TEXT_MUTED,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            ).pack(pady=60)
            self._update_stats(leads)
            return

        for lead in leads:
            self._render_row(lead)
        self._update_stats(leads)

    # ── stats ──
    def _update_stats(self, leads=None):
        if leads is None:
            leads = get_all_leads()
        total = len(leads)
        contacted = sum(1 for l in leads if l["is_contacted"])
        self._stat_total.configure(text=f"Total: {total}")
        self._stat_yes.configure(text=f"Contacted: {contacted}")
        self._stat_no.configure(text=f"Pending: {total - contacted}")

    # ── single row ──
    def _render_row(self, lead):
        lead_id = lead["id"]
        phone   = lead["phone_number"]
        status  = lead.get("lead_status") or "Uncontacted"
        if lead["is_contacted"] and status == "Uncontacted":
            status = "Contacted"

        row = ctk.CTkFrame(self._scroll, fg_color=T.BG_ROW, corner_radius=T.CORNER_RADIUS_BASE, height=T.ROW_HEIGHT)
        row.pack(fill="x", pady=2, padx=4)
        row.pack_propagate(False)

        # Phone
        ctk.CTkLabel(
            row, text=phone, width=170, anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left", padx=(T.PAD_MD, T.PAD_SM))

        # City
        ctk.CTkLabel(
            row, text=lead["city"] or "—", width=130, anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=T.PAD_SM)

        # SIM dropdown
        sim_var = ctk.StringVar(value=lead["sim_assignment"] if lead["sim_assignment"] != "Unassigned" else "— None")
        def _sim_cb(val, _lid=lead_id):
            actual = val if val != "— None" else "Unassigned"
            update_sim_assignment(_lid, actual)
        ctk.CTkOptionMenu(
            row, values=["— None", "SIM 1", "SIM 2"],
            variable=sim_var, command=_sim_cb,
            width=T.DROPDOWN_WIDTH, height=28,
            corner_radius=T.CORNER_RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            fg_color=T.BG_DROPDOWN, button_color=T.BG_DROPDOWN,
            button_hover_color=T.BG_DROPDOWN_HOVER,
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=T.PAD_SM)

        # Spacer
        ctk.CTkLabel(row, text="", fg_color="transparent").pack(side="left", fill="x", expand=True)

        # Status pill
        st = STATUS_STYLES.get(status, STATUS_STYLES["Uncontacted"])
        def _status_cb(_lead=lead, _phone=phone, _lid=lead_id):
            if _lead["is_contacted"]:
                self._open_reply(_lid, _lead)
            else:
                self._open_template(_lid, _phone)
        ctk.CTkButton(
            row, text=st["label"], width=120, height=28,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
            fg_color=st["fg"], hover_color=st["hover"],
            border_color=st["border"], border_width=st["border_w"],
            text_color=st["text_color"],
            command=_status_cb,
        ).pack(side="right", padx=(T.PAD_SM, T.PAD_MD))

    # ── popups ──
    def _open_template(self, lead_id, phone):
        def cb(template_num):
            phone_clean = phone.replace(" ", "")
            if phone_clean.startswith("+"):
                phone_clean = phone_clean[1:]
            webbrowser.open(f"viber://chat?number=%2B{phone_clean}")
            update_contact_status(lead_id, 1, template_num)
            self.load_leads()
        TemplatePromptPopup(self.winfo_toplevel(), on_confirm=cb)

    def _open_reply(self, lead_id, lead):
        def cb(status, notes):
            update_lead_reply(lead_id, status, notes)
            self.load_leads()
        ReplyPopup(
            self.winfo_toplevel(),
            current_status=lead.get("lead_status"),
            current_notes=lead.get("reply_notes", ""),
            on_confirm=cb,
        )
