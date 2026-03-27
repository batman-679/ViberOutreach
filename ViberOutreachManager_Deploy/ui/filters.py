import customtkinter as ctk
import theme as T


class FiltersFrame(ctk.CTkFrame):
    """Purple top-nav bar with ghost-style filter pills and action buttons."""

    def __init__(self, master, on_filter_change=None, on_import=None, on_sync=None):
        super().__init__(master, height=T.NAV_HEIGHT, fg_color=T.BG_NAV, corner_radius=0)
        self.pack(fill="x")
        self.pack_propagate(False)  # lock height

        self.on_filter_change = on_filter_change
        self.on_import = on_import
        self.on_sync = on_sync
        self._active_filter = "All"

        # ── Brand label ──
        ctk.CTkLabel(
            self, text="CRM", font=ctk.CTkFont(family=T.FONT_FAMILY, size=15, weight="bold"),
            text_color="#9A95B8",
        ).pack(side="left", padx=(T.PAD_LG, T.PAD_MD))

        # ── Filter pills ──
        self._filter_btns = {}
        for label in ["Show All", "Uncontacted", "SIM 1", "SIM 2", "Contacted"]:
            btn = ctk.CTkButton(
                self, text=label, width=90, height=28,
                corner_radius=T.CORNER_RADIUS_PILL,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
                fg_color=T.FILTER_DEFAULT_BG, text_color=T.FILTER_DEFAULT_TEXT,
                hover_color="#9585F7",
                command=lambda f=label: self._on_filter(f),
            )
            btn.pack(side="left", padx=3, pady=T.PAD_SM)
            self._filter_btns[label] = btn

        # Mark "Show All" as active at start
        self._filter_btns["Show All"].configure(
            fg_color=T.FILTER_ACTIVE_BG, text_color=T.FILTER_ACTIVE_TEXT
        )

        # ── Spacer ──
        ctk.CTkLabel(self, text="", fg_color="transparent").pack(side="left", fill="x", expand=True)

        # ── Sync button ──
        self.btn_sync = ctk.CTkButton(
            self, text="↻  Sync to Sheets", width=140, height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.SYNC_BTN_BG, text_color=T.SYNC_BTN_TEXT,
            hover_color=T.SYNC_BTN_HOVER,
            command=self._trigger_sync,
        )
        self.btn_sync.pack(side="right", padx=(5, T.PAD_MD), pady=T.PAD_SM)

        # ── Import button ──
        ctk.CTkButton(
            self, text="📥  Import", width=100, height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.SYNC_BTN_BG, text_color=T.SYNC_BTN_TEXT,
            hover_color=T.SYNC_BTN_HOVER,
            command=self._trigger_import,
        ).pack(side="right", padx=3, pady=T.PAD_SM)

    # ── internal helpers ──
    def _on_filter(self, name):
        self._active_filter = name
        # visual toggle
        for lbl, btn in self._filter_btns.items():
            if lbl == name:
                btn.configure(fg_color=T.FILTER_ACTIVE_BG, text_color=T.FILTER_ACTIVE_TEXT)
            else:
                btn.configure(fg_color=T.FILTER_DEFAULT_BG, text_color=T.FILTER_DEFAULT_TEXT)
        # route to parent
        mapping = {"Show All": "All", "Uncontacted": "Uncontacted",
                   "SIM 1": "SIM 1", "SIM 2": "SIM 2", "Contacted": "Contacted"}
        if self.on_filter_change:
            self.on_filter_change(mapping.get(name, "All"))

    def _trigger_import(self):
        if self.on_import:
            self.on_import()

    def _trigger_sync(self):
        if self.on_sync:
            self.on_sync()
