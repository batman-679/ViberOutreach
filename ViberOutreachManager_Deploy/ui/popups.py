import customtkinter as ctk
import theme as T


class TemplatePromptPopup(ctk.CTkToplevel):
    """Modal: pick message template (1, 2, or 3)."""

    def __init__(self, master, on_confirm=None):
        super().__init__(master)
        self.title("Select Template")
        self.geometry("320x200")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_MODAL)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.on_confirm = on_confirm

        ctk.CTkLabel(
            self, text="Which template did you use?",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=14, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(pady=(T.PAD_LG, T.PAD_BASE))

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=T.PAD_BASE)
        for t in [1, 2, 3]:
            ctk.CTkButton(
                bf, text=f"Template {t}", width=90, height=32,
                corner_radius=T.CORNER_RADIUS_SM,
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
                fg_color=T.ACCENT_PRIMARY, hover_color=T.ACCENT_HOVER,
                text_color=T.TEXT_ON_ACCENT,
                command=lambda n=t: self._pick(n),
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            self, text="Cancel", width=80, height=28,
            corner_radius=T.CORNER_RADIUS_SM,
            fg_color=T.BG_ROW, hover_color=T.BG_ROW_HOVER,
            text_color=T.TEXT_SECONDARY,
            command=self.destroy,
        ).pack(pady=(T.PAD_BASE, T.PAD_SM))

    def _pick(self, n):
        if self.on_confirm:
            self.on_confirm(n)
        self.destroy()


class HistoryPopup(ctk.CTkToplevel):
    """Read-only view of contact timestamp + template used."""

    def __init__(self, master, timestamp, template_used):
        super().__init__(master)
        self.title("Contact History")
        self.geometry("320x180")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_MODAL)
        self.grab_set()
        self.lift()
        self.focus_force()

        ctk.CTkLabel(
            self, text="Contact Details",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=16, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(pady=(T.PAD_LG, T.PAD_BASE))

        ctk.CTkLabel(
            self,
            text=f"Template Used:  #{template_used}\nTimestamp:  {timestamp}",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(pady=(0, T.PAD_MD))

        ctk.CTkButton(
            self, text="Close", width=80,
            corner_radius=T.CORNER_RADIUS_SM,
            fg_color=T.BG_ROW, hover_color=T.BG_ROW_HOVER,
            text_color=T.TEXT_SECONDARY,
            command=self.destroy,
        ).pack()


class ReplyPopup(ctk.CTkToplevel):
    """Pipeline update: change status + paste reply notes."""

    def __init__(self, master, current_status, current_notes, on_confirm=None):
        super().__init__(master)
        self.title("Update Lead Pipeline")
        self.geometry("400x360")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_MODAL)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.on_confirm = on_confirm

        ctk.CTkLabel(
            self, text="Live Reply & Status",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=16, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(pady=(T.PAD_MD, T.PAD_SM))

        default = current_status if current_status and current_status not in ("Uncontacted", "Contacted") else "Replied"
        self.status_var = ctk.StringVar(value=default)
        ctk.CTkOptionMenu(
            self, values=["Contacted", "Replied", "Call Booked", "Rejected"],
            variable=self.status_var, width=170, height=30,
            corner_radius=T.CORNER_RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            fg_color=T.BG_DROPDOWN, button_color=T.BG_DROPDOWN,
            button_hover_color=T.BG_DROPDOWN_HOVER,
            text_color=T.TEXT_PRIMARY,
        ).pack(pady=T.PAD_BASE)

        ctk.CTkLabel(
            self, text="Paste Viber Reply:", anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD_XL, pady=(T.PAD_SM, 0))

        self.notes = ctk.CTkTextbox(
            self, height=100,
            fg_color=T.BG_ROW, text_color=T.TEXT_PRIMARY,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            border_color=T.BORDER_DEFAULT, border_width=1,
            corner_radius=T.CORNER_RADIUS_SM,
        )
        self.notes.pack(padx=T.PAD_XL, pady=(0, T.PAD_MD), fill="x")
        if current_notes:
            self.notes.insert("1.0", current_notes)

        ctk.CTkButton(
            self, text="Save Update", width=140, height=34,
            corner_radius=T.CORNER_RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            fg_color=T.ACCENT_PRIMARY, hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=self._save,
        ).pack(pady=(0, T.PAD_BASE))

    def _save(self):
        if self.on_confirm:
            self.on_confirm(self.status_var.get(), self.notes.get("1.0", "end").strip())
        self.destroy()
