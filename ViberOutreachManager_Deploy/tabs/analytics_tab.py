"""Analytics dashboard powered by DailyStats."""

import customtkinter as ctk

import theme as T
from core.database import get_daily_stats


class AnalyticsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD_LG, pady=(T.PAD_MD, T.PAD_SM))

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Analytics Dashboard",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=T.FONT_SIZE_XL, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Messages sent vs. calls booked across recent DailyStats records.",
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
            command=self.load_stats,
        ).pack(side="right")

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=T.PAD_LG, pady=(0, T.PAD_MD))
        for index in range(4):
            cards.grid_columnconfigure(index, weight=1)

        self._tracked_days = self._metric_card(cards, 0, "Tracked Days")
        self._messages_total = self._metric_card(cards, 1, "Messages Sent")
        self._calls_total = self._metric_card(cards, 2, "Calls Booked")
        self._conversion = self._metric_card(cards, 3, "Conversion")

        chart_panel = ctk.CTkFrame(
            self,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_LG,
        )
        chart_panel.pack(fill="both", expand=True, padx=T.PAD_LG, pady=(0, T.PAD_LG))

        legend = ctk.CTkFrame(chart_panel, fg_color="transparent")
        legend.pack(fill="x", padx=T.PAD_MD, pady=(T.PAD_MD, T.PAD_SM))

        ctk.CTkLabel(
            legend,
            text="Recent Performance",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=14, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        self._legend_chip(legend, T.ACCENT_PRIMARY, "Messages Sent").pack(side="right")
        self._legend_chip(legend, T.STATUS_TRUE_BORDER, "Calls Booked").pack(side="right", padx=(0, T.PAD_MD))

        self._chart_scroll = ctk.CTkScrollableFrame(
            chart_panel,
            fg_color="transparent",
            scrollbar_button_color=T.ACCENT_MUTED,
            scrollbar_button_hover_color=T.ACCENT_PRIMARY,
        )
        self._chart_scroll.pack(fill="both", expand=True, padx=T.PAD_SM, pady=(0, T.PAD_SM))

        self.load_stats()

    def _metric_card(self, parent, column, title):
        card = ctk.CTkFrame(
            parent,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_BASE,
        )
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else T.PAD_SM, 0))

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD_MD, pady=(T.PAD_MD, 2))

        value = ctk.CTkLabel(
            card,
            text="0",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=22, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        )
        value.pack(anchor="w", padx=T.PAD_MD, pady=(0, T.PAD_MD))
        return value

    @staticmethod
    def _legend_chip(parent, color, text):
        chip = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkFrame(chip, width=10, height=10, corner_radius=5, fg_color=color).pack(
            side="left", padx=(0, 6), pady=4
        )
        ctk.CTkLabel(
            chip,
            text=text,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left")
        return chip

    def load_stats(self):
        stats = list(reversed(get_daily_stats(limit=14)))

        for child in self._chart_scroll.winfo_children():
            child.destroy()

        tracked_days = len(stats)
        total_messages = sum(row.get("messages_sent", 0) or 0 for row in stats)
        total_calls = sum(row.get("calls_booked", 0) or 0 for row in stats)
        conversion = (total_calls / total_messages * 100) if total_messages else 0

        self._tracked_days.configure(text=str(tracked_days))
        self._messages_total.configure(text=str(total_messages))
        self._calls_total.configure(text=str(total_calls))
        self._conversion.configure(text=f"{conversion:.1f}%")

        if not stats:
            ctk.CTkLabel(
                self._chart_scroll,
                text="No DailyStats data yet.",
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
                text_color=T.TEXT_MUTED,
            ).pack(pady=T.PAD_XL)
            return

        max_value = max(
            max((row.get("messages_sent", 0) or 0) for row in stats),
            max((row.get("calls_booked", 0) or 0) for row in stats),
            1,
        )

        for row in stats:
            self._chart_row(row, max_value)

    def _chart_row(self, row, max_value):
        wrap = ctk.CTkFrame(
            self._chart_scroll,
            fg_color=T.BG_ROOT,
            corner_radius=T.CORNER_RADIUS_BASE,
        )
        wrap.pack(fill="x", padx=4, pady=4)

        ctk.CTkLabel(
            wrap,
            text=row.get("date", "-"),
            width=100,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left", padx=(T.PAD_MD, T.PAD_SM), pady=T.PAD_MD)

        bars = ctk.CTkFrame(wrap, fg_color="transparent")
        bars.pack(side="left", fill="x", expand=True, pady=T.PAD_MD)

        self._bar_line(
            bars,
            "Messages",
            row.get("messages_sent", 0) or 0,
            max_value,
            T.ACCENT_PRIMARY,
        ).pack(fill="x", pady=(0, 6))
        self._bar_line(
            bars,
            "Calls",
            row.get("calls_booked", 0) or 0,
            max_value,
            T.STATUS_TRUE_BORDER,
        ).pack(fill="x")

    def _bar_line(self, parent, label, value, max_value, color):
        line = ctk.CTkFrame(parent, fg_color="transparent")

        ctk.CTkLabel(
            line,
            text=label,
            width=70,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, T.PAD_SM))

        track = ctk.CTkFrame(
            line,
            width=320,
            height=14,
            fg_color=T.BORDER_SUBTLE,
            corner_radius=7,
        )
        track.pack(side="left", padx=(0, T.PAD_SM))
        track.pack_propagate(False)

        fill_width = max(8 if value > 0 else 0, int((value / max_value) * 320))
        if value > 0:
            ctk.CTkFrame(
                track,
                width=fill_width,
                height=14,
                fg_color=color,
                corner_radius=7,
            ).pack(side="left")

        ctk.CTkLabel(
            line,
            text=str(value),
            width=40,
            anchor="e",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")
        return line
