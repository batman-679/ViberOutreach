"""Settings tab backed by the Settings key-value table."""

from tkinter import messagebox

import customtkinter as ctk

import theme as T
from core.database import get_setting, set_setting

SETTING_FIELDS = [
    (
        "google_sheet_name",
        "Google Sheet Name",
        "Spreadsheet tab or workbook name used for sync output.",
    ),
    (
        "sim1_daily_limit",
        "SIM 1 Daily Limit",
        "Maximum outreach actions allowed for SIM 1 each day.",
    ),
    (
        "sim2_daily_limit",
        "SIM 2 Daily Limit",
        "Maximum outreach actions allowed for SIM 2 each day.",
    ),
    (
        "credentials_path",
        "Credentials Path",
        "Path to the Google service account credentials JSON file.",
    ),
]

DEFAULTS = {
    "google_sheet_name": "Viber Outreach Sync",
    "sim1_daily_limit": "40",
    "sim2_daily_limit": "40",
    "credentials_path": "credentials.json",
}


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self._vars = {}

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD_LG, pady=(T.PAD_MD, T.PAD_SM))

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Settings",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=T.FONT_SIZE_XL, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Edit saved configuration values from the Settings table.",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(side="right")

        ctk.CTkButton(
            actions,
            text="Reload",
            width=90,
            height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.BG_ROW,
            hover_color=T.BG_ROW_HOVER,
            text_color=T.TEXT_PRIMARY,
            command=self.load_settings,
        ).pack(side="left", padx=(0, T.PAD_SM))

        ctk.CTkButton(
            actions,
            text="Save",
            width=100,
            height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.ACCENT_PRIMARY,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=self.save_settings,
        ).pack(side="left")

        panel = ctk.CTkFrame(
            self,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_LG,
        )
        panel.pack(fill="both", expand=True, padx=T.PAD_LG, pady=(0, T.PAD_LG))
        panel.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(
            panel,
            text="",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        )
        self._status.grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_MD, 0))

        row = 1
        for key, label, help_text in SETTING_FIELDS:
            var = ctk.StringVar()
            self._vars[key] = var

            ctk.CTkLabel(
                panel,
                text=label,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
                text_color=T.TEXT_PRIMARY,
            ).grid(row=row, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_MD, 2))
            row += 1

            ctk.CTkEntry(
                panel,
                textvariable=var,
                height=36,
                fg_color=T.BG_ROOT,
                border_color=T.BORDER_DEFAULT,
                text_color=T.TEXT_PRIMARY,
                corner_radius=T.CORNER_RADIUS_BASE,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            ).grid(row=row, column=0, sticky="ew", padx=T.PAD_MD)
            row += 1

            ctk.CTkLabel(
                panel,
                text=help_text,
                justify="left",
                wraplength=700,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
                text_color=T.TEXT_SECONDARY,
            ).grid(row=row, column=0, sticky="w", padx=T.PAD_MD, pady=(4, 0))
            row += 1

        panel.grid_rowconfigure(row, weight=1)

        self.load_settings()

    def load_settings(self):
        for key in self._vars:
            value = get_setting(key, DEFAULTS.get(key, ""))
            self._vars[key].set(value or "")
        self._status.configure(text="Loaded current settings values.")

    def save_settings(self):
        sim1 = self._vars["sim1_daily_limit"].get().strip()
        sim2 = self._vars["sim2_daily_limit"].get().strip()
        if not sim1.isdigit() or not sim2.isdigit():
            messagebox.showerror("Settings", "SIM daily limits must be whole numbers.")
            return

        for key, value_var in self._vars.items():
            set_setting(key, value_var.get().strip())

        self._status.configure(text="Settings saved successfully.")
        messagebox.showinfo("Settings", "Settings updated successfully.")
