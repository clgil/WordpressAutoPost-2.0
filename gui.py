"""
gui.py
Interfaz gráfica (Tkinter) para gestionar la publicación en WordPress.
"""

import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

from main import Config
from database import init_db, track_new_file, mark_as_published, is_file_processed
from google_drive import list_files_in_drive
from openrouter_api import get_brief_description
from exe_io_api import shorten_url
from image_processor import set_featured_image_from_url
from wordpress_api import create_post
from jinja2 import Template


class AutoPostGUI(tk.Tk):
    def __init__(self, drive_service, template_path="template.html"):
        super().__init__()
        self.title("WordPress Auto Poster")
        self.geometry("700x500")

        self.drive_service = drive_service
        self.template = Template(open(template_path, "r", encoding="utf-8").read())

        self.mode_var = tk.StringVar(value="batch")
        self.status_text = tk.StringVar(value="Listo")

        self.create_widgets()
        init_db()

    # ---------------- UI ----------------
    def create_widgets(self):
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(frame, text="Mode:").pack(side="left")
        ttk.Combobox(frame, textvariable=self.mode_var, values=["batch", "queue", "schedule"]).pack(side="left")

        ttk.Button(frame, text="Start", command=self.start_process).pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self, length=600, mode="determinate")
        self.progress.pack(pady=10)

        self.log_box = tk.Text(self, height=20, width=80, wrap="word")
        self.log_box.pack(padx=10, pady=10, fill="both", expand=True)

    # ---------------- Safe UI helpers ----------------
    def thread_safe(self, fn, *args, **kwargs):
        """Ejecuta la función en el hilo principal de Tkinter."""
        self.after(0, lambda: fn(*args, **kwargs))

    def append_status(self, message: str):
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")

    def update_progress(self, current: int, total: int):
        self.progress["value"] = (current / total) * 100
        self.update_idletasks()

    # ---------------- Core ----------------
    def start_process(self):
        threading.Thread(target=self.run_mode, daemon=True).start()

    def run_mode(self):
        mode = self.mode_var.get()
        files = list_files_in_drive(self.drive_service)
        if not files:
            self.thread_safe(self.append_status, "No se encontraron archivos en Drive o fallo la conexión.")
            return

        self.thread_safe(self.progress.configure, maximum=len(files))

        for idx, file in enumerate(files, start=1):
            file_id, file_name = file["id"], file["name"]

            if is_file_processed(file_id):
                self.thread_safe(self.append_status, f"Saltado (ya procesado): {file_name}")
                self.thread_safe(self.update_progress, idx, len(files))
                continue

            try:
                if mode == "batch":
                    self.handle_file(file_id, file_name)
                    mark_as_published(file_id)  # registrar en BD

                elif mode == "queue":
                    # Guardar en cola con fecha NULL
                    track_new_file(file_id, file_name, None)
                    self.thread_safe(self.append_status, f"Agregado a cola: {file_name}")

                elif mode == "schedule":
                    scheduled = datetime.utcnow() + timedelta(minutes=Config.DEFAULT_SCHEDULE_OFFSET_MINUTES)
                    self.handle_file(file_id, file_name, scheduled_date=scheduled)
                    track_new_file(file_id, file_name, scheduled)
                    mark_as_published(file_id)  # registrar en BD

                else:
                    self.thread_safe(self.append_status, f"Modo desconocido: {mode}")

            except Exception as e:
                self.thread_safe(self.append_status, f"Error procesando {file_name}: {e}")

            self.thread_safe(self.update_progress, idx, len(files))

        self.thread_safe(self.append_status, "Proceso completado.")

    # ---------------- File handling ----------------
    def handle_file(self, file_id: str, file_name: str, scheduled_date: datetime = None):
        # Preparar link de descarga
        file_link = f"https://drive.google.com/uc?id={file_id}&export=download"
        short_link = shorten_url(file_link)

        # Descripción generada por LLM
        description = get_brief_description(file_name)

        # Determinar tipo
        is_boardview = "boardview" in file_name.lower()
        download_label = "Download Boardview" if is_boardview else "Download Schematic"

        # Imagen destacada (puede ser None si falla)
        featured_image_id = None
        if is_boardview:
            # Ejemplo de fallback: imagen genérica para boardview
            image_url = f"{Config.WP_SITE_URL}/wp-content/uploads/boardview-default.jpg"
        else:
            image_url = f"{Config.WP_SITE_URL}/wp-content/uploads/schematic-default.jpg"
        featured_image_id = set_featured_image_from_url(image_url, alt_text=file_name)

        # Render del template
        content = self.template.render(
            file_name=file_name,
            download_link=short_link,
            brief_description=description,
            download_label=download_label,
        )

        # Publicar en WP
        result = create_post(
            title=file_name,
            content=content,
            featured_media=featured_image_id,
            publish_date=scheduled_date,
        )

        if result:
            self.thread_safe(self.append_status, f"Publicado: {file_name}")
        else:
            self.thread_safe(self.append_status, f"Fallo publicación: {file_name}")


def run_gui(config: Config, drive_service):
    app = AutoPostGUI(drive_service)
    app.mainloop()
