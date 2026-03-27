"""Tasks tab showing leads with follow-ups due today or earlier."""

from datetime import datetime
import webbrowser

import customtkinter as ctk

import theme as T
from core.database import get_all_leads

PRIORITY_COLORS = {
    "High": "#c23b22",
    "Medium": "#d4b106",
    "Low": "#4f9dd9",
}


class TasksTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self._today = datetime.now().strftime("%Y-%m-%d")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD_LG, pady=(T.PAD_MD, T.PAD_SM))

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Tasks & Follow-ups",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=T.FONT_SIZE_XL, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Leads whose follow-up date is due today or overdue.",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            top,
            text="Refresh",
            width=100,
            height=28,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.ACCENT_PRIMARY,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=self.load_tasks,
        ).pack(side="right")

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=T.PAD_LG, pady=(0, T.PAD_SM))
        self._stat_due = self._make_stat(stats, T.ACCENT_PRIMARY, "Due: 0")
        self._stat_overdue = self._make_stat(stats, "#c23b22", "Overdue: 0")
        self._stat_today = self._make_stat(stats, "#d4b106", "Due today: 0")

        ctk.CTkFrame(self, height=1, fg_color=T.BORDER_SUBTLE).pack(
            fill="x", padx=T.PAD_BASE, pady=(0, T.PAD_SM)
        )

        headers = ctk.CTkFrame(self, fg_color="transparent")
        headers.pack(fill="x", padx=T.PAD_LG)
        for title, width in [
            ("LEAD", 200),
            ("PHONE", 150),
            ("CITY", 130),
            ("FOLLOW UP", 120),
            ("PRIORITY", 90),
            ("STATUS", 120),
        ]:
            ctk.CTkLabel(
                headers,
                text=title,
                width=width,
                anchor="w",
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=10, weight="bold"),
                text_color=T.TEXT_MUTED,
            ).pack(side="left", padx=(0, T.PAD_SM))

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.ACCENT_MUTED,
            scrollbar_button_hover_color=T.ACCENT_PRIMARY,
        )
        self._scroll.pack(fill="both", expand=True, padx=T.PAD_SM, pady=(T.PAD_SM, T.PAD_SM))

        self.load_tasks()

    @staticmethod
    def _make_stat(parent, dot_color, text):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(side="left", padx=(0, T.PAD_LG))
        ctk.CTkFrame(
            wrap, width=8, height=8, corner_radius=4, fg_color=dot_color
        ).pack(side="left", padx=(0, 6), pady=4)
        label = ctk.CTkLabel(
            wrap,
            text=text,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        )
        label.pack(side="left")
        return label

    def load_tasks(self):
        self._today = datetime.now().strftime("%Y-%m-%d")
        leads = get_all_leads(
            "follow_up_date IS NOT NULL AND date(follow_up_date) <= date(?)",
            (self._today,),
        )
        leads.sort(key=lambda lead: (lead.get("follow_up_date") or "", lead.get("priority") or "Medium"))

        for child in self._scroll.winfo_children():
            child.destroy()

        overdue_count = sum(
            1 for lead in leads if (lead.get("follow_up_date") or "") < self._today
        )
        today_count = sum(
            1 for lead in leads if (lead.get("follow_up_date") or "") == self._today
        )
        self._stat_due.configure(text=f"Due: {len(leads)}")
        self._stat_overdue.configure(text=f"Overdue: {overdue_count}")
        self._stat_today.configure(text=f"Due today: {today_count}")

        if not leads:
            self._empty_state("No follow-ups are due right now.")
            return

        for lead in leads:
            self._task_row(lead)

    def _empty_state(self, text):
        box = ctk.CTkFrame(
            self._scroll,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_BASE,
        )
        box.pack(fill="x", padx=4, pady=T.PAD_MD)
        ctk.CTkLabel(
            box,
            text=text,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_MUTED,
        ).pack(padx=T.PAD_LG, pady=T.PAD_XL)

    def _task_row(self, lead):
        status = lead.get("lead_status") or "Uncontacted"
        priority = lead.get("priority") or "Medium"
        due_date = lead.get("follow_up_date") or "-"
        is_overdue = due_date < self._today
        priority_color = PRIORITY_COLORS.get(priority, T.TEXT_SECONDARY)

        row = ctk.CTkFrame(
            self._scroll,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_BASE,
            height=70,
        )
        row.pack(fill="x", pady=4, padx=4)
        row.pack_propagate(False)

        ctk.CTkLabel(
            row,
            text=lead.get("name") or "Unnamed Lead",
            width=200,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left", padx=(T.PAD_MD, T.PAD_SM))

        ctk.CTkLabel(
            row,
            text=lead.get("phone_number") or "-",
            width=150,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, T.PAD_SM))

        ctk.CTkLabel(
            row,
            text=lead.get("city") or "-",
            width=130,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, T.PAD_SM))

        date_box = ctk.CTkFrame(row, fg_color="transparent", width=120)
        date_box.pack(side="left", padx=(0, T.PAD_SM))
        date_box.pack_propagate(False)
        ctk.CTkLabel(
            date_box,
            text=due_date,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            text_color="#c23b22" if is_overdue else T.TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            date_box,
            text="Overdue" if is_overdue else "Due today",
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=10),
            text_color="#c23b22" if is_overdue else "#d4b106",
        ).pack(anchor="w")

        ctk.CTkLabel(
            row,
            text=priority,
            width=90,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            text_color=priority_color,
        ).pack(side="left", padx=(0, T.PAD_SM))

        ctk.CTkLabel(
            row,
            text=status,
            width=120,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, T.PAD_SM))

        ctk.CTkLabel(row, text="", fg_color="transparent").pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row,
            text="Open Viber",
            width=120,
            height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.ACCENT_PRIMARY,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=lambda phone=lead.get("phone_number", ""): self._open_viber(phone),
        ).pack(side="right", padx=T.PAD_MD)

    @staticmethod
    def _open_viber(phone_number):
        cleaned = "".join(ch for ch in phone_number if ch.isdigit() or ch == "+")
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        webbrowser.open(f"viber://chat?number=%2B{cleaned}")
