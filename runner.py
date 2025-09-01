"""
runner.py
Ejecución en modo batch/scheduler sin GUI para WordpressAutoPost.
"""

import logging
from datetime import datetime, timedelta

from main import Config
from database import init_db, track_new_file, mark_as_published, is_file_processed, get_pending_posts
from google_drive import list_files_in_drive
from openrouter_api import get_brief_description
from google_drive import get_file_metadata
from exe_io_api import shorten_url
from image_processor import set_featured_image_from_url
from wordpress_api import create_post
from jinja2 import Template

logger = logging.getLogger("runner")


def run_once(config: Config, drive_service, template_path="template.html", schedule: bool = False):
    """
    Procesa una pasada de archivos desde Google Drive.
    - Si schedule=True: programa los posts con un offset.
    - Si schedule=False: los publica inmediatamente.
    """
    init_db()

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())
    except Exception as e:
        logger.error("No se pudo cargar template %s: %s", template_path, e)
        return

    files = list_files_in_drive(drive_service)
    if not files:
        logger.warning("No se encontraron archivos en Google Drive.")
        return

    for file in files:
        file_id, file_name = file["id"], file["name"]

        if is_file_processed(file_id):
            logger.debug("Saltado (ya procesado): %s", file_name)
            continue

        try:
            if schedule:
                scheduled = datetime.utcnow() + timedelta(minutes=Config.DEFAULT_SCHEDULE_OFFSET_MINUTES)
                success = process_file(file_id, file_name, template, scheduled_date=scheduled)
                if success:
                    track_new_file(file_id, file_name, scheduled)
                    mark_as_published(file_id)
            else:
                success = process_file(file_id, file_name, template)
                if success:
                    track_new_file(file_id, file_name, datetime.utcnow())
                    mark_as_published(file_id)
        except Exception as e:
            logger.exception("Error procesando %s: %s", file_name, e)


def process_file(file_id: str, file_name: str, template: Template, scheduled_date=None) -> bool:
    """
    Procesa un solo archivo y lo publica en WordPress.
    Devuelve True si fue publicado con éxito.
    """
    # Preparar link de descarga
    file_link = f"https://drive.google.com/uc?id={file_id}&export=download"
    short_link = shorten_url(file_link)

    # Descripción
    description = get_brief_description(file_name)

    # Metadata del archivo
    file_metadata = get_file_metadata(file_id)

    # Determinar tipo de archivo
    is_boardview = "boardview" in file_name.lower()
    download_label = "Download Boardview" if is_boardview else "Download Schematic"

    # Imagen destacada
    if is_boardview:
        image_url = f"{Config.WP_SITE_URL}/{Config.DEFAULT_BOARDVIEW_IMAGE_URL}"
    else:
        image_url = f"{Config.WP_SITE_URL}/{Config.DEFAULT_SCHEMATIC_IMAGE_URL}"
    featured_image_id = set_featured_image_from_url(image_url, alt_text=file_name)

    # Renderizar template
    content = template.render(
        file_name=file_name,
        file_metadata=file_metadata,
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
        logger.info("Publicado en WP: %s", file_name)
        return True
    else:
        logger.error("Fallo al publicar: %s", file_name)
        return False
