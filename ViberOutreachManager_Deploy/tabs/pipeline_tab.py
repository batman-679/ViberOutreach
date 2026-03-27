"""Pipeline Tab — Visual Kanban board grouped by lead_status."""

import customtkinter as ctk
import theme as T
from core.database import get_all_leads

# Columns in the kanban — ordered left-to-right
COLUMNS = [
    ("Uncontacted", T.STATUS_FALSE_BORDER, T.STATUS_FALSE_TEXT),
    ("Contacted",   T.STATUS_TRUE_BORDER,  T.STATUS_TRUE_TEXT),
    ("Replied",     "#d4b106",             "#d4b106"),
    ("Call Booked", "#00a86b",             "#00a86b"),
    ("Rejected",    "#c23b22",             "#c23b22"),
]


class PipelineTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)

        # ── Title bar ──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD_LG, pady=(T.PAD_MD, T.PAD_SM))

        ctk.CTkLabel(
            top, text="Pipeline  —  Kanban Board",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=T.FONT_SIZE_XL, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            top, text="↻  Refresh", width=100, height=28,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.ACCENT_PRIMARY, hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=self.load,
        ).pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=T.PAD_BASE, pady=(0, T.PAD_SM))

        # ── Column container ──
        self._columns_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._columns_frame.pack(fill="both", expand=True, padx=T.PAD_SM, pady=(0, T.PAD_SM))

        # Make columns expand equally
        for i in range(len(COLUMNS)):
            self._columns_frame.grid_columnconfigure(i, weight=1)
        self._columns_frame.grid_rowconfigure(1, weight=1)  # row 1 = scroll areas

        # Build column headers + scrollable card areas
        self._col_scrolls = []
        self._col_counts = []
        for i, (title, border_color, text_color) in enumerate(COLUMNS):
            # Header
            hdr = ctk.CTkFrame(self._columns_frame, fg_color=T.BG_ROW, corner_radius=T.CORNER_RADIUS_BASE)
            hdr.grid(row=0, column=i, padx=4, pady=(0, 4), sticky="ew")

            # Colored dot
            dot_frame = ctk.CTkFrame(hdr, fg_color="transparent")
            dot_frame.pack(fill="x", padx=T.PAD_SM, pady=T.PAD_SM)
            ctk.CTkFrame(dot_frame, width=8, height=8, corner_radius=4, fg_color=border_color).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                dot_frame, text=title.upper(),
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=10, weight="bold"),
                text_color=text_color,
            ).pack(side="left")

            count_lbl = ctk.CTkLabel(
                dot_frame, text="0",
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=10, weight="bold"),
                text_color=T.TEXT_MUTED,
            )
            count_lbl.pack(side="right")
            self._col_counts.append(count_lbl)

            # Scrollable card list
            scroll = ctk.CTkScrollableFrame(
                self._columns_frame, fg_color="transparent",
                scrollbar_button_color=T.ACCENT_MUTED,
                scrollbar_button_hover_color=T.ACCENT_PRIMARY,
            )
            scroll.grid(row=1, column=i, padx=4, pady=0, sticky="nsew")
            self._col_scrolls.append(scroll)

        self.load()

    def load(self):
        """Fetch all leads and distribute into columns."""
        leads = get_all_leads()

        # Clear all columns
        for scroll in self._col_scrolls:
            for w in scroll.winfo_children():
                w.destroy()

        # Group leads by status
        grouped = {}
        for lead in leads:
            status = lead.get("lead_status") or "Uncontacted"
            if lead["is_contacted"] and status == "Uncontacted":
                status = "Contacted"
            grouped.setdefault(status, []).append(lead)

        for i, (col_status, border_color, text_color) in enumerate(COLUMNS):
            col_leads = grouped.get(col_status, [])
            self._col_counts[i].configure(text=str(len(col_leads)))

            if not col_leads:
                ctk.CTkLabel(
                    self._col_scrolls[i], text="Empty",
                    font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
                    text_color=T.TEXT_MUTED,
                ).pack(pady=T.PAD_LG)
                continue

            for lead in col_leads:
                self._card(self._col_scrolls[i], lead, border_color, text_color)

    def _card(self, parent, lead, border_color, text_color):
        """Single lead card inside a kanban column."""
        card = ctk.CTkFrame(
            parent, fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_BASE,
            border_color=border_color, border_width=1,
        )
        card.pack(fill="x", pady=3, padx=2)

        # Name
        ctk.CTkLabel(
            card, text=lead["name"],
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD_SM, pady=(T.PAD_SM, 2))

        # Phone
        ctk.CTkLabel(
            card, text=lead["phone_number"],
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=text_color,
        ).pack(anchor="w", padx=T.PAD_SM)

        # City  +  SIM
        meta_parts = []
        if lead["city"]:
            meta_parts.append(lead["city"])
        if lead["sim_assignment"] and lead["sim_assignment"] != "Unassigned":
            meta_parts.append(lead["sim_assignment"])
        if meta_parts:
            ctk.CTkLabel(
                card, text="  ·  ".join(meta_parts),
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
                text_color=T.TEXT_MUTED,
            ).pack(anchor="w", padx=T.PAD_SM, pady=(2, T.PAD_SM))
        else:
            # bottom padding
            ctk.CTkFrame(card, height=T.PAD_SM, fg_color="transparent").pack()
