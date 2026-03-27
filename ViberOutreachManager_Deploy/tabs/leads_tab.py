"""Leads Tab — the original CRM dashboard, now inside a tab frame."""

import webbrowser
import threading
import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
import theme as T
from core.database import (
    get_all_leads,
    update_sim_assignment,
    update_contact_status,
    update_lead_reply,
)
from core.data_handler import import_leads_from_csv
from core.google_sync import sync_leads_to_sheets
from ui.popups import TemplatePromptPopup, ReplyPopup

# ---------- status pill styles ----------
STATUS_STYLES = {
    "Uncontacted": {
        "fg": T.STATUS_FALSE_BG, "hover": "#333333",
        "border": T.STATUS_FALSE_BORDER, "border_w": 1,
        "text_color": T.STATUS_FALSE_TEXT, "label": "○  False",
    },
    "Contacted": {
        "fg": T.STATUS_TRUE_BG, "hover": T.STATUS_TRUE_HOVER,
        "border": T.STATUS_TRUE_BORDER, "border_w": 1,
        "text_color": T.STATUS_TRUE_TEXT, "label": "✓  Contacted",
    },
    "Replied": {
        "fg": "#332D00", "hover": "#443D00",
        "border": "#d4b106", "border_w": 1,
        "text_color": "#d4b106", "label": "✓  Replied",
    },
    "Call Booked": {
        "fg": "#003322", "hover": "#004433",
        "border": "#00a86b", "border_w": 1,
        "text_color": "#00a86b", "label": "✓  Call Booked",
    },
    "Rejected": {
        "fg": "#330D08", "hover": "#441510",
        "border": "#c23b22", "border_w": 1,
        "text_color": "#c23b22", "label": "✗  Rejected",
    },
}


class LeadsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self._filter_q = None
        self._filter_p = ()

        # ── Nav bar ──
        nav = ctk.CTkFrame(self, height=T.NAV_HEIGHT, fg_color=T.BG_NAV, corner_radius=0)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        ctk.CTkLabel(
            nav, text="CRM", font=ctk.CTkFont(family=T.FONT_FAMILY, size=15, weight="bold"),
            text_color="#9A95B8",
        ).pack(side="left", padx=(T.PAD_LG, T.PAD_MD))

        self._filter_btns = {}
        for label in ["Show All", "Uncontacted", "SIM 1", "SIM 2", "Contacted"]:
            btn = ctk.CTkButton(
                nav, text=label, width=90, height=28,
                corner_radius=T.CORNER_RADIUS_PILL,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
                fg_color=T.FILTER_DEFAULT_BG, text_color=T.FILTER_DEFAULT_TEXT,
                hover_color="#9585F7",
                command=lambda f=label: self._on_filter(f),
            )
            btn.pack(side="left", padx=3, pady=T.PAD_SM)
            self._filter_btns[label] = btn
        self._filter_btns["Show All"].configure(fg_color=T.FILTER_ACTIVE_BG, text_color=T.FILTER_ACTIVE_TEXT)

        ctk.CTkLabel(nav, text="", fg_color="transparent").pack(side="left", fill="x", expand=True)

        self.btn_sync = ctk.CTkButton(
            nav, text="↻  Sync to Sheets", width=140, height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.SYNC_BTN_BG, text_color=T.SYNC_BTN_TEXT,
            hover_color=T.SYNC_BTN_HOVER, command=self._sync,
        )
        self.btn_sync.pack(side="right", padx=(5, T.PAD_MD), pady=T.PAD_SM)

        ctk.CTkButton(
            nav, text="📥  Import", width=100, height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.SYNC_BTN_BG, text_color=T.SYNC_BTN_TEXT,
            hover_color=T.SYNC_BTN_HOVER, command=self._import,
        ).pack(side="right", padx=3, pady=T.PAD_SM)

        # ── Column headers ──
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=T.PAD_LG)
        for title, w in [("PHONE NUMBER", 170), ("CITY", 130), ("SIM CARD", 140), ("STATUS", 120)]:
            ctk.CTkLabel(hdr, text=title, width=w, anchor="w",
                         font=ctk.CTkFont(family=T.FONT_FAMILY, size=10, weight="bold"),
                         text_color=T.TEXT_MUTED).pack(side="left", padx=T.PAD_SM)

        ctk.CTkFrame(self, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=T.PAD_BASE, pady=(0, T.PAD_SM))

        # ── Scroll area ──
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=T.ACCENT_MUTED,
            scrollbar_button_hover_color=T.ACCENT_PRIMARY,
        )
        self._scroll.pack(fill="both", expand=True, padx=T.PAD_SM)

        # ── Stats bar ──
        stats = ctk.CTkFrame(self, height=32, fg_color=T.BG_ROOT, corner_radius=0)
        stats.pack(fill="x", side="bottom")
        stats.pack_propagate(False)
        self._stat_total = self._mk_stat(stats, T.ACCENT_PRIMARY, "Total: 0")
        self._stat_yes   = self._mk_stat(stats, T.STATUS_TRUE_TEXT, "Contacted: 0")
        self._stat_no    = self._mk_stat(stats, T.STATUS_FALSE_BORDER, "Pending: 0")

        self.load_leads()

    # ── helpers ──
    @staticmethod
    def _mk_stat(parent, dot, text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=T.PAD_MD, pady=4)
        ctk.CTkFrame(f, width=6, height=6, corner_radius=3, fg_color=dot).pack(side="left", padx=(0, 5))
        lbl = ctk.CTkLabel(f, text=text, font=ctk.CTkFont(family=T.FONT_FAMILY, size=11), text_color=T.TEXT_MUTED)
        lbl.pack(side="left")
        return lbl

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
            ctk.CTkLabel(self._scroll, text="No leads match this filter",
                         text_color=T.TEXT_MUTED,
                         font=ctk.CTkFont(family=T.FONT_FAMILY, size=13)).pack(pady=60)
        else:
            for lead in leads:
                self._row(lead)
        self._stats(leads)

    def _stats(self, leads=None):
        if leads is None:
            leads = get_all_leads()
        t = len(leads)
        c = sum(1 for l in leads if l["is_contacted"])
        self._stat_total.configure(text=f"Total: {t}")
        self._stat_yes.configure(text=f"Contacted: {c}")
        self._stat_no.configure(text=f"Pending: {t - c}")

    def _row(self, lead):
        lid, phone = lead["id"], lead["phone_number"]
        status = lead.get("lead_status") or "Uncontacted"
        if lead["is_contacted"] and status == "Uncontacted":
            status = "Contacted"

        row = ctk.CTkFrame(self._scroll, fg_color=T.BG_ROW, corner_radius=T.CORNER_RADIUS_BASE, height=T.ROW_HEIGHT)
        row.pack(fill="x", pady=2, padx=4)
        row.pack_propagate(False)

        ctk.CTkLabel(row, text=phone, width=170, anchor="w",
                     font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left", padx=(T.PAD_MD, T.PAD_SM))
        ctk.CTkLabel(row, text=lead["city"] or "—", width=130, anchor="w",
                     font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
                     text_color=T.TEXT_SECONDARY).pack(side="left", padx=T.PAD_SM)

        sim_var = ctk.StringVar(value=lead["sim_assignment"] if lead["sim_assignment"] != "Unassigned" else "— None")
        def _sim(val, _lid=lid):
            update_sim_assignment(_lid, val if val != "— None" else "Unassigned")
        ctk.CTkOptionMenu(row, values=["— None", "SIM 1", "SIM 2"], variable=sim_var, command=_sim,
                          width=T.DROPDOWN_WIDTH, height=28, corner_radius=T.CORNER_RADIUS_SM,
                          font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
                          fg_color=T.BG_DROPDOWN, button_color=T.BG_DROPDOWN,
                          button_hover_color=T.BG_DROPDOWN_HOVER, text_color=T.TEXT_SECONDARY,
                          ).pack(side="left", padx=T.PAD_SM)

        ctk.CTkLabel(row, text="", fg_color="transparent").pack(side="left", fill="x", expand=True)

        st = STATUS_STYLES.get(status, STATUS_STYLES["Uncontacted"])
        def _click(_lead=lead, _phone=phone, _lid=lid):
            if _lead["is_contacted"]:
                self._reply(_lid, _lead)
            else:
                self._template(_lid, _phone)
        ctk.CTkButton(row, text=st["label"], width=120, height=28,
                      corner_radius=T.CORNER_RADIUS_PILL,
                      font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
                      fg_color=st["fg"], hover_color=st["hover"],
                      border_color=st["border"], border_width=st["border_w"],
                      text_color=st["text_color"], command=_click,
                      ).pack(side="right", padx=(T.PAD_SM, T.PAD_MD))

    def _template(self, lid, phone):
        def cb(n):
            pc = phone.replace(" ", "")
            if pc.startswith("+"):
                pc = pc[1:]
            webbrowser.open(f"viber://chat?number=%2B{pc}")
            update_contact_status(lid, 1, n)
            self.load_leads()
        TemplatePromptPopup(self.winfo_toplevel(), on_confirm=cb)

    def _reply(self, lid, lead):
        def cb(s, n):
            update_lead_reply(lid, s, n)
            self.load_leads()
        ReplyPopup(self.winfo_toplevel(), lead.get("lead_status"), lead.get("reply_notes", ""), on_confirm=cb)

    # ── filters ──
    def _on_filter(self, name):
        for lbl, btn in self._filter_btns.items():
            if lbl == name:
                btn.configure(fg_color=T.FILTER_ACTIVE_BG, text_color=T.FILTER_ACTIVE_TEXT)
            else:
                btn.configure(fg_color=T.FILTER_DEFAULT_BG, text_color=T.FILTER_DEFAULT_TEXT)
        mapping = {"Show All": None, "Uncontacted": ("is_contacted = ?", (0,)),
                   "Contacted": ("is_contacted = ?", (1,)),
                   "SIM 1": ("sim_assignment = ?", ("SIM 1",)),
                   "SIM 2": ("sim_assignment = ?", ("SIM 2",))}
        filt = mapping.get(name)
        if filt is None:
            self.load_leads(filter_query=None, filter_params=())
        else:
            self.load_leads(filter_query=filt[0], filter_params=filt[1])

    # ── import / sync ──
    def _import(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
        if not os.path.isdir(d):
            d = os.getcwd()
        p = filedialog.askopenfilename(title="Select Lead CSV", initialdir=d,
                                        filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("All", "*.*")])
        if not p:
            return
        c = import_leads_from_csv(p)
        messagebox.showinfo("Import", f"Imported {c} leads\n{os.path.basename(p)}")
        self.load_leads()

    def _sync(self):
        self.btn_sync.configure(state="disabled", text="Syncing…")
        def w():
            try:
                ok, msg = sync_leads_to_sheets()
            except Exception as e:
                ok, msg = False, str(e)
            self.after(0, self._sync_done, ok, msg)
        threading.Thread(target=w, daemon=True).start()

    def _sync_done(self, ok, msg):
        self.btn_sync.configure(state="normal", text="↻  Sync to Sheets")
        (messagebox.showinfo if ok else messagebox.showerror)("Sync" if ok else "Error", msg)
