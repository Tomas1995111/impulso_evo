"""Cliente simple para Google Sheets (append)."""

from __future__ import annotations

import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from core import config

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _client_from_service_account_json(
    credentials_path: str | None = None,
) -> gspread.Client:
    if not credentials_path:
        credentials_path = config.CREDENTIALS_FILE
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"No se encontró '{credentials_path}'. Copialo desde mensajes/credenciales.example.json"
        )
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, SCOPES)
    return gspread.authorize(creds)


def append_lead_row(
    *,
    sheet_id: str,
    tab_name: str,
    telefono: str,
    nombre: str,
    mail: str,
    fecha_captura: str,
    origen: str,
    estado: str,
) -> None:
    """Append de una fila en la pestaña indicada con el formato del Sheet 'Maestro'."""
    client = _client_from_service_account_json()
    sh = client.open_by_key(sheet_id)

    # Intenta primero la pestaña exacta y luego variantes tolerantes.
    ws = None
    tried_titles = []
    for candidate in [tab_name, (tab_name or "").strip()]:
        if candidate and candidate not in tried_titles:
            tried_titles.append(candidate)
            try:
                ws = sh.worksheet(candidate)
                break
            except Exception:
                pass

    # Fallback case-insensitive por si hay diferencia de mayúsculas/espacios.
    if ws is None:
        target = (tab_name or "").strip().lower()
        for w in sh.worksheets():
            if (w.title or "").strip().lower() == target:
                ws = w
                break

    # Último fallback: primera hoja para no perder leads por nombre de pestaña.
    if ws is None:
        ws = sh.sheet1

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    row = [
        telefono,
        nombre,
        mail,
        fecha_captura,
        origen,
        estado,
        "",  # Fecha de baja
        "",  # Motivo Baja
        ahora,  # Última Actualización
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")


def append_alert_row(
    fecha: str,
    ticker: str,
    precio: float,
    stop_loss: float,
    sheet_id: str = "",
) -> None:
    """Append de una alerta bursátil a la sheet de alertas."""
    sid = sheet_id or config.SHEET_ID
    client = _client_from_service_account_json()
    sheet = client.open_by_key(sid).sheet1
    sheet.append_row([fecha, ticker, precio, stop_loss])
