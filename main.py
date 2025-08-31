#!/usr/bin/env python3
"""
main.py
Entrada principal de la aplicación WordpressAutoPost.

Objetivos en esta versión:
- Cargar variables de entorno desde .env (si existe).
- Centralizar configuración usada por los módulos (WP_SITE_URL, API KEYS, timeouts).
- Inicializar logging de forma consistente.
- Proveer helpers reutilizables (ej. format_date_for_wp).
- Validar presencia de secretos críticos y fallar de forma clara si faltan.
- Inicializar (de forma segura) el cliente de Google Drive y propagar errores.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Cargar .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv es opcional; si no existe, asumimos que env vars están en el entorno
    pass

# Configuración básica de logging (nivel y formato central)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("WordpressAutoPost")

# === Configuración centralizada (todos los módulos deben importar desde aquí) ===
class Config:
    # WordPress
    WP_SITE_URL: str = os.getenv("WP_SITE_URL", "").rstrip("/")
    WP_USER: str = os.getenv("WP_USER", "")
    WP_PASSWORD: str = os.getenv("WP_PASSWORD", "")  # NO dejar hardcode en repo
    WP_API_BASE: str = ""  # se construye abajo

    # Google Drive / Service Account
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    # OpenRouter / LLM (opcional)
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")

    # Otros services
    EXE_IO_API_KEY: Optional[str] = os.getenv("EXE_IO_API_KEY")

    # Timeouts, paging, etc.
    HTTP_TIMEOUT_SECONDS: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
    DRIVE_PAGE_SIZE: int = int(os.getenv("DRIVE_PAGE_SIZE", "1000"))

    # App behavior
    DEFAULT_SCHEDULE_OFFSET_MINUTES: int = int(os.getenv("DEFAULT_SCHEDULE_OFFSET_MINUTES", "5"))
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "wordpres_autopost.sqlite3")
    BRAND_IMAGES_JSON: str = os.getenv("BRAND_IMAGES_JSON", "brand_images.json")

# Construir campos derivados
if Config.WP_SITE_URL:
    Config.WP_API_BASE = f"{Config.WP_SITE_URL}/wp-json/wp/v2"
else:
    Config.WP_API_BASE = ""

# Validaciones iniciales (no cierres abruptos en entornos de desarrollo; loggear y permitir ejecución parcial)
def validate_critical_config(raise_on_missing: bool = False):
    missing = []
    if not Config.WP_SITE_URL:
        missing.append("WP_SITE_URL")
    if not Config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH:
        logger.warning("No se ha definido GOOGLE_SERVICE_ACCOUNT_JSON_PATH; la funcionalidad de Drive estará limitada.")
    if missing:
        msg = f"Faltan variables de entorno críticas: {', '.join(missing)}"
        if raise_on_missing:
            raise RuntimeError(msg)
        logger.error(msg)

# Helper para formatear fechas para WordPress (usar date_gmt)
def format_date_for_wp(dt: datetime) -> dict:
    """
    Devuelve un dict con 'date_gmt' (UTC ISO) y 'status'='future' si la fecha es futura.
    WordPress espera 'date' en la zona del sitio y 'date_gmt' en UTC; preferimos enviar date_gmt.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    payload = {"date_gmt": dt_utc.isoformat()}
    if dt_utc > datetime.now(timezone.utc):
        payload["status"] = "future"
    return payload

# Inicialización del cliente de Google Drive (se delega a database/drive module,
# pero aquí hay un helper para detectar errores al inicio)
def init_google_drive_service():
    """
    Intenta inicializar el cliente de Google Drive usando la ruta al service account indicada.
    No lanza excepciones si falla; devuelve None y loggea el error para que los módulos superiores lo manejen.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        sa_path = Config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH
        if not sa_path:
            logger.info("No hay GOOGLE_SERVICE_ACCOUNT_JSON_PATH configurado. Omitiendo init Drive.")
            return None

        if not os.path.exists(sa_path):
            logger.error("La ruta GOOGLE_SERVICE_ACCOUNT_JSON_PATH no existe: %s", sa_path)
            return None

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        logger.info("Inicializado cliente de Google Drive correctamente.")
        return service
    except Exception as e:
        logger.exception("No se pudo inicializar Google Drive client: %s", e)
        return None

# Helper para validar/normalizar WP URL (muy útil para detectar trailing slashes, http/https)
def normalize_wp_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.endswith("/"):
        url = url[:-1]
    return url

# Punto de entrada (CLI simple). La GUI o un runner importarán Config, logger e init_google_drive_service
def main(argv=None):
    validate_critical_config(raise_on_missing=False)
    logger.info("Arrancando WordpressAutoPost")
    logger.debug("Configuración: WP_API_BASE=%s, DATABASE=%s", Config.WP_API_BASE, Config.DATABASE_PATH)

    # Intentar inicializar Drive (si está configurado)
    drive_service = init_google_drive_service()
    if Config.GOOGLE_DRIVE_FOLDER_ID and drive_service is None:
        logger.warning(
            "Se ha configurado GOOGLE_DRIVE_FOLDER_ID pero no se pudo inicializar Drive. "
            "Comprueba GOOGLE_SERVICE_ACCOUNT_JSON_PATH y permisos."
        )

    # Aqui podríamos arrancar la GUI o la lógica de CLI/batch según argumentos
    # Para evitar acoplar demasiado main con la GUI, delegamos a otros módulos:
    try:
        # Ejemplo: si se quiere arrancar la GUI
        if len(os.getenv("FORCE_MODE", "").strip()) == 0 and (argv and "--gui" in argv):
            # Import lazy de gui (evita cargar tkinter si no se usa)
            from gui import run_gui
            run_gui(config=Config, drive_service=drive_service)
        else:
            # Modo por defecto: ejecución en batch o scheduler externo.
            # Importa el runner principal (por ejemplo main_runner.process_pending)
            from runner import run_once  # runner.py será el que contenga la lógica batch
            run_once(config=Config, drive_service=drive_service)
    except ImportError as e:
        logger.debug("No se encontró módulo opcional: %s", e)
        logger.info("Modo interactivo no disponible. Ejecuta con --gui o revisa los módulos runner/gui.")
    except Exception as e:
        logger.exception("Error en el flujo principal: %s", e)

if __name__ == "__main__":
    main(sys.argv)
