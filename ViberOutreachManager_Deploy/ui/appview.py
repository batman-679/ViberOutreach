import threading
import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
import theme as T

from ui.filters import FiltersFrame
from ui.dashboard import DashboardFrame
from core.google_sync import sync_leads_to_sheets
from core.data_handler import import_leads_from_csv


class AppView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG_ROOT)
        self.pack(fill="both", expand=True)

        # Filters bar (purple nav)
        self.filters_frame = FiltersFrame(
            self,
            on_filter_change=self._apply_filter,
            on_import=self._import_leads,
            on_sync=self._sync_to_sheets,
        )

        # Dashboard
        self.dashboard_frame = DashboardFrame(self)

    # ---------- filter routing ----------
    def _apply_filter(self, f):
        q, p = {
            "All":         (None, ()),
            "Uncontacted": ("is_contacted = ?", (0,)),
            "Contacted":   ("is_contacted = ?", (1,)),
            "SIM 1":       ("sim_assignment = ?", ("SIM 1",)),
            "SIM 2":       ("sim_assignment = ?", ("SIM 2",)),
        }.get(f, (None, ()))
        self.dashboard_frame.load_leads(filter_query=q, filter_params=p)

    # ---------- CSV import ----------
    def _import_leads(self):
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
        if not os.path.isdir(data_dir):
            data_dir = os.getcwd()

        path = filedialog.askopenfilename(
            title="Select Lead CSV File", initialdir=data_dir,
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if not path:
            return
        count = import_leads_from_csv(path)
        messagebox.showinfo("Import Complete", f"Imported {count} new leads\n{os.path.basename(path)}")
        self.dashboard_frame.load_leads()

    # ---------- Google Sheets sync ----------
    def _sync_to_sheets(self):
        btn = self.filters_frame.btn_sync
        btn.configure(state="disabled", text="Syncing…")

        def _worker():
            try:
                ok, msg = sync_leads_to_sheets()
            except Exception as e:
                ok, msg = False, str(e)
            self.after(0, self._on_sync_done, ok, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_sync_done(self, ok, msg):
        self.filters_frame.btn_sync.configure(state="normal", text="↻  Sync to Sheets")
        (messagebox.showinfo if ok else messagebox.showerror)(
            "Sync Complete" if ok else "Sync Failed", msg
        )
