"""
database.py
Gestión de la base de datos SQLite para trackear archivos y publicaciones.
"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime

from main import Config

logger = logging.getLogger("database")

DB_PATH = Config.DATABASE_PATH


# --- Helpers internos ---
def _connect():
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)


# --- Inicialización ---
def init_db():
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                file_id TEXT PRIMARY KEY,
                file_name TEXT,
                scheduled_date TIMESTAMP NULL,
                published INTEGER DEFAULT 0,
                published_at TIMESTAMP NULL
            )
            """
        )

        conn.commit()
        conn.close()
        logger.info("Base de datos inicializada en %s", DB_PATH)
    except Exception as e:
        logger.exception("Error al inicializar la base de datos: %s", e)


# --- Operaciones CRUD ---
def track_new_file(file_id: str, file_name: str, scheduled_date: Optional[datetime]):
    """
    Registra un nuevo archivo en la base de datos. 
    Si ya existe, no lo sobrescribe.
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO scheduled_posts (file_id, file_name, scheduled_date, published)
            VALUES (?, ?, ?, 0)
            """,
            (file_id, file_name, scheduled_date.isoformat() if scheduled_date else None),
        )
        conn.commit()
        conn.close()
        logger.debug("Trackeado archivo nuevo: %s (%s)", file_name, file_id)
    except Exception as e:
        logger.exception("Error en track_new_file para %s: %s", file_id, e)


def mark_as_published(file_id: str):
    """
    Marca un archivo como publicado.
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE scheduled_posts
            SET published = 1, published_at = CURRENT_TIMESTAMP
            WHERE file_id = ?
            """,
            (file_id,),
        )
        conn.commit()
        conn.close()
        logger.info("Marcado como publicado: %s", file_id)
    except Exception as e:
        logger.exception("Error en mark_as_published para %s: %s", file_id, e)


def is_file_processed(file_id: str) -> bool:
    """
    Devuelve True si el archivo ya fue procesado o publicado.
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT published FROM scheduled_posts WHERE file_id = ?
            """,
            (file_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row is None:
            return False
        return row[0] == 1
    except Exception as e:
        logger.exception("Error en is_file_processed para %s: %s", file_id, e)
        return False


def get_pending_posts() -> list[tuple[str, str, Optional[datetime]]]:
    """
    Obtiene los posts pendientes (no publicados aún).
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT file_id, file_name, scheduled_date
            FROM scheduled_posts
            WHERE published = 0
            ORDER BY scheduled_date ASC
            """
        )
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.exception("Error en get_pending_posts: %s", e)
        return []
