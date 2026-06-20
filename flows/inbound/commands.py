from __future__ import annotations

import logging
import re

from core import evolution_client
from core.alerts import generate_ticker_alert
from core.links import IOL_REFERIDO, SUSCRIPCION_PREMIUM, SUSCRIPCION_PREMIUM_7D, SUSCRIPCION_PREMIUM_30D
from core.precio import generar_cotizacion_precio
from core.sheets_client import search_leads
from mensajes.mensajeBalances import generar_mensaje_balances

logger = logging.getLogger(__name__)

LINKS: dict[str, str] = {
    "Suscripción Premium": SUSCRIPCION_PREMIUM,
    "Suscripción Premium 7 días gratis": SUSCRIPCION_PREMIUM_7D,
    "Suscripción Premium 30 días gratis": SUSCRIPCION_PREMIUM_30D,
}

COMANDOS_AYUDA = (
    "🤖 *Comandos disponibles*\n\n"
    "• `/alerta TICKER1 TICKER2...` — alerta bursátil para uno o más tickers (US o Argentina)\n"
    "• `/balances` — calendario de balances de la semana (empresas clave ARG y USA)\n"
    "• `/ayuda` — muestra esta ayuda\n"
    "• `/links` — links útiles de Impulso Merval\n"
    "• `/perfil NOMBRE o TELÉFONO` — busca y muestra perfil de un cliente\n"
    "• `/precio TICKER` — cotización rápida de una acción (precio, variación, máx/mín)\n"
    "• `/designarasesor` — link de referido IOL y ruta del documento de vinculación AFI"
)


def handle_command(remote_jid: str, text: str) -> bool:
    """Procesa un comando detectado. Retorna True si se manejó."""
    text = text.strip()

    cmd = text.lower()

    if cmd in ("/links", "/link"):
        _cmd_links(remote_jid)
        return True

    if cmd in ("/ayuda", "/help"):
        evolution_client.send_text(remote_jid, COMANDOS_AYUDA)
        return True

    if cmd in ("/balances",):
        _cmd_balances(remote_jid)
        return True

    if cmd.startswith("/perfil"):
        args = text[len("/perfil"):].strip()
        _cmd_perfil(remote_jid, args)
        return True

    if cmd.startswith("/precio"):
        args = text[len("/precio"):].strip()
        _cmd_precio(remote_jid, args)
        return True

    m = re.match(r"^/alerta\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if m:
        _cmd_alerta(remote_jid, m.group(1))
        return True

    if cmd in ("/designarasesor",):
        _cmd_designar_asesor(remote_jid)
        return True

    evolution_client.send_text(remote_jid, f"❌ Comando no reconocido: {text}")
    return True


def _cmd_links(remote_jid: str) -> None:
    lines = ["🔗 *Links útiles de Impulso Merval*\n"]
    for name, url in LINKS.items():
        lines.append(f"• *{name}*: {url}")
    evolution_client.send_text(remote_jid, "\n".join(lines))


def _cmd_balances(remote_jid: str) -> None:
    try:
        mensaje = generar_mensaje_balances()
    except Exception as e:
        mensaje = f"❌ Error al obtener balances: {e}"
        logger.exception("Error al generar mensaje de balances")
    if not mensaje:
        mensaje = "❌ No se pudieron obtener los balances en este momento."
    evolution_client.send_text(remote_jid, mensaje)


def _cmd_precio(remote_jid: str, args: str) -> None:
    if not args:
        evolution_client.send_text(remote_jid, "❌ Ej: /precio AAPL")
        return
    ticker = args.upper().strip()
    try:
        mensaje = generar_cotizacion_precio(ticker)
    except Exception as e:
        mensaje = f"❌ Error al obtener cotización de *{ticker}*: {e}"
    evolution_client.send_text(remote_jid, mensaje)


def _cmd_perfil(remote_jid: str, query: str) -> None:
    if not query:
        evolution_client.send_text(
            remote_jid,
            "❌ Tenés que indicar un nombre o teléfono. Ej: /perfil Juan",
        )
        return

    try:
        results = search_leads(query)
    except Exception as e:
        evolution_client.send_text(
            remote_jid,
            f"❌ Error al buscar en Google Sheets: {e}",
        )
        logger.exception("Error al buscar en Google Sheets")
        return

    if not results:
        evolution_client.send_text(
            remote_jid,
            f'❌ No encontré ningún cliente con "{query}".',
        )
        return

    partes = []
    for r in results:
        nombre = r.get("Nombre") or r.get("nombre") or ""
        telefono = r.get("Teléfono") or r.get("telefono") or list(r.values())[0]
        mail = r.get("Mail") or r.get("mail") or list(r.values())[2]
        captura = r.get("Fecha Captura") or r.get("fecha_captura") or list(r.values())[3]
        origen = r.get("Origen") or r.get("origen") or list(r.values())[4]
        estado = r.get("Estado") or r.get("estado") or list(r.values())[5]
        fecha_baja = r.get("Fecha Baja") or r.get("fecha_baja") or list(r.values())[6] or "—"
        motivo = r.get("Motivo Baja") or r.get("motivo_baja") or list(r.values())[7] or "—"
        ult_act = r.get("Última Actualización") or r.get("ultima_act") or list(r.values())[8] or "—"

        partes.append(
            f"👤 *{nombre}*\n"
            f"📞 {telefono}\n"
            f"📧 {mail}\n"
            f"📅 Captura: {captura}\n"
            f"🎯 Origen: {origen}\n"
            f"📌 Estado: *{estado}*\n"
            f"❌ Baja: {fecha_baja}\n"
            f"💬 Motivo: {motivo}\n"
            f"🔄 Actualización: {ult_act}"
        )

    evolution_client.send_text(remote_jid, "\n\n─────────────\n\n".join(partes))


def _cmd_designar_asesor(remote_jid: str) -> None:
    caption = (
        "👤 *IOL Referido*\n"
        f"{IOL_REFERIDO}"
    )
    evolution_client.send_document(
        jid=remote_jid,
        filepath="documentos/Modelo vinculación AFI.docx",
        filename="Modelo vinculación AFI.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        caption=caption,
    )


def _cmd_alerta(remote_jid: str, args: str) -> None:
    tickers = args.upper().split()
    for ticker in tickers:
        try:
            mensaje = generate_ticker_alert(ticker)
            evolution_client.send_text(remote_jid, mensaje)
        except Exception as e:
            evolution_client.send_text(remote_jid, f"❌ Error con {ticker}: {e}")
            logger.exception("Error con ticker %s", ticker)
