"""Templates tab with CRUD controls for the Templates table."""

from tkinter import messagebox

import customtkinter as ctk

import theme as T
from core.database import (
    add_template,
    delete_template,
    get_all_templates,
    update_template,
)


class TemplatesTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self._selected_template_id = None
        self._templates = []

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD_LG, pady=(T.PAD_MD, T.PAD_SM))

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Template Library",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=T.FONT_SIZE_XL, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w")

        self._subtitle = ctk.CTkLabel(
            title_box,
            text="0 templates available",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            text_color=T.TEXT_SECONDARY,
        )
        self._subtitle.pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            top,
            text="New Template",
            width=120,
            height=30,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.ACCENT_PRIMARY,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=self._start_new_template,
        ).pack(side="right")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=T.PAD_LG, pady=(0, T.PAD_LG))
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        list_panel = ctk.CTkFrame(
            content,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_LG,
        )
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, T.PAD_MD))

        ctk.CTkLabel(
            list_panel,
            text="Saved Templates",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=14, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD_MD, pady=(T.PAD_MD, T.PAD_SM))

        self._list_scroll = ctk.CTkScrollableFrame(
            list_panel,
            fg_color="transparent",
            scrollbar_button_color=T.ACCENT_MUTED,
            scrollbar_button_hover_color=T.ACCENT_PRIMARY,
        )
        self._list_scroll.pack(fill="both", expand=True, padx=T.PAD_SM, pady=(0, T.PAD_SM))

        form_panel = ctk.CTkFrame(
            content,
            fg_color=T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_LG,
        )
        form_panel.grid(row=0, column=1, sticky="nsew")
        form_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form_panel,
            text="Template Editor",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=14, weight="bold"),
            text_color=T.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_MD, T.PAD_SM))

        self.name_var = ctk.StringVar()
        self.category_var = ctk.StringVar()

        self._field(form_panel, 1, "Template Name")
        self._entry(form_panel, 2, self.name_var)

        self._field(form_panel, 3, "Category")
        self._entry(form_panel, 4, self.category_var)

        self._field(form_panel, 5, "Body")
        self.body_text = ctk.CTkTextbox(
            form_panel,
            height=260,
            fg_color=T.BG_ROOT,
            border_color=T.BORDER_DEFAULT,
            border_width=1,
            corner_radius=T.CORNER_RADIUS_BASE,
            text_color=T.TEXT_PRIMARY,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
            activate_scrollbars=True,
        )
        self.body_text.grid(row=6, column=0, sticky="nsew", padx=T.PAD_MD)
        form_panel.grid_rowconfigure(6, weight=1)

        self._status_label = ctk.CTkLabel(
            form_panel,
            text="Create a new template or select one from the list.",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        )
        self._status_label.grid(row=7, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 0))

        actions = ctk.CTkFrame(form_panel, fg_color="transparent")
        actions.grid(row=8, column=0, sticky="ew", padx=T.PAD_MD, pady=T.PAD_MD)

        self.delete_btn = ctk.CTkButton(
            actions,
            text="Delete",
            width=100,
            height=32,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color="#4a1f1f",
            hover_color="#612a2a",
            text_color="#ffb3b3",
            command=self._delete_selected,
            state="disabled",
        )
        self.delete_btn.pack(side="left")

        ctk.CTkButton(
            actions,
            text="Save Template",
            width=130,
            height=32,
            corner_radius=T.CORNER_RADIUS_PILL,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            fg_color=T.ACCENT_PRIMARY,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_ON_ACCENT,
            command=self._save_template,
        ).pack(side="right")

        self.refresh_templates()
        self._start_new_template()

    @staticmethod
    def _field(parent, row, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
            text_color=T.TEXT_SECONDARY,
        ).grid(row=row, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 4))

    @staticmethod
    def _entry(parent, row, variable):
        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=34,
            fg_color=T.BG_ROOT,
            border_color=T.BORDER_DEFAULT,
            text_color=T.TEXT_PRIMARY,
            corner_radius=T.CORNER_RADIUS_BASE,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
        )
        entry.grid(row=row, column=0, sticky="ew", padx=T.PAD_MD)
        return entry

    def refresh_templates(self, select_id=None):
        self._templates = get_all_templates()
        self._subtitle.configure(text=f"{len(self._templates)} templates available")

        for child in self._list_scroll.winfo_children():
            child.destroy()

        if not self._templates:
            ctk.CTkLabel(
                self._list_scroll,
                text="No templates saved yet.",
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
                text_color=T.TEXT_MUTED,
            ).pack(pady=T.PAD_XL)
            return

        for template in self._templates:
            self._template_card(template)

        valid_ids = {template["id"] for template in self._templates}
        if select_id is not None:
            self._selected_template_id = select_id if select_id in valid_ids else None
        elif self._selected_template_id not in valid_ids:
            self._selected_template_id = None

    def _template_card(self, template):
        is_selected = template["id"] == self._selected_template_id
        card = ctk.CTkFrame(
            self._list_scroll,
            fg_color=T.BG_ROOT if is_selected else T.BG_ROW,
            corner_radius=T.CORNER_RADIUS_BASE,
            border_width=1,
            border_color=T.ACCENT_PRIMARY if is_selected else T.BORDER_DEFAULT,
        )
        card.pack(fill="x", pady=4, padx=2)

        ctk.CTkButton(
            card,
            text=template["name"],
            anchor="w",
            height=32,
            fg_color="transparent",
            hover_color=T.BG_ROW_HOVER,
            text_color=T.TEXT_PRIMARY,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            command=lambda tpl=template: self._select_template(tpl),
        ).pack(fill="x", padx=T.PAD_SM, pady=(T.PAD_SM, 2))

        meta = f'{template.get("category") or "General"}  |  Used {template.get("usage_count", 0)} times'
        ctk.CTkLabel(
            card,
            text=meta,
            anchor="w",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_SECONDARY,
        ).pack(fill="x", padx=T.PAD_SM)

        preview = (template.get("body") or "").strip().replace("\n", " ")
        if len(preview) > 90:
            preview = preview[:87] + "..."
        ctk.CTkLabel(
            card,
            text=preview or "No content",
            anchor="w",
            justify="left",
            wraplength=280,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            text_color=T.TEXT_MUTED,
        ).pack(fill="x", padx=T.PAD_SM, pady=(4, T.PAD_SM))

    def _select_template(self, template):
        self._selected_template_id = template["id"]
        self.name_var.set(template.get("name") or "")
        self.category_var.set(template.get("category") or "General")
        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", template.get("body") or "")
        self._status_label.configure(text=f'Editing template #{template["id"]}')
        self.delete_btn.configure(state="normal")
        self.refresh_templates()

    def _start_new_template(self, status_message=None):
        self._selected_template_id = None
        self.name_var.set("")
        self.category_var.set("General")
        self.body_text.delete("1.0", "end")
        self._status_label.configure(
            text=status_message or "Create a new template or select one from the list."
        )
        self.delete_btn.configure(state="disabled")
        self.refresh_templates()

    def _save_template(self):
        name = self.name_var.get().strip()
        category = self.category_var.get().strip() or "General"
        body = self.body_text.get("1.0", "end").strip()

        if not name:
            messagebox.showerror("Templates", "Template name is required.")
            return
        if not body:
            messagebox.showerror("Templates", "Template body cannot be empty.")
            return

        if self._selected_template_id is None:
            add_template(name, body, category)
            self._start_new_template(status_message=f'Created template "{name}".')
            return

        update_template(self._selected_template_id, name, body, category)
        current_id = self._selected_template_id
        self._status_label.configure(text=f'Updated template "{name}".')
        self.refresh_templates(select_id=current_id)

    def _delete_selected(self):
        if self._selected_template_id is None:
            return

        if not messagebox.askyesno("Templates", "Delete the selected template?"):
            return

        delete_template(self._selected_template_id)
        self._start_new_template(status_message="Template deleted.")
