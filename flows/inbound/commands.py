from __future__ import annotations

import re
import traceback

from core import evolution_client
from core.alerts import generate_ticker_alert
from core.links import SUSCRIPCION_PREMIUM, SUSCRIPCION_PREMIUM_7D, SUSCRIPCION_PREMIUM_30D

LINKS: dict[str, str] = {
    "Suscripción Premium": SUSCRIPCION_PREMIUM,
    "Suscripción Premium 7 días gratis": SUSCRIPCION_PREMIUM_7D,
    "Suscripción Premium 30 días gratis": SUSCRIPCION_PREMIUM_30D,
}

COMANDOS_AYUDA = (
    "🤖 *Comandos disponibles*\n\n"
    "• `/alerta TICKER1 TICKER2...` — alerta bursátil para uno o más tickers (US o Argentina)\n"
    "• `/links` — links útiles de Impulso Merval\n"
    "• `/ayuda` — muestra esta ayuda"
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

    m = re.match(r"^/alerta\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if m:
        _cmd_alerta(remote_jid, m.group(1))
        return True

    evolution_client.send_text(remote_jid, f"❌ Comando no reconocido: {text}")
    return True


def _cmd_links(remote_jid: str) -> None:
    lines = ["🔗 *Links útiles de Impulso Merval*\n"]
    for name, url in LINKS.items():
        lines.append(f"• *{name}*: {url}")
    evolution_client.send_text(remote_jid, "\n".join(lines))


def _cmd_alerta(remote_jid: str, args: str) -> None:
    tickers = args.upper().split()
    for ticker in tickers:
        try:
            mensaje = generate_ticker_alert(ticker)
            evolution_client.send_text(remote_jid, mensaje)
        except Exception as e:
            evolution_client.send_text(remote_jid, f"❌ Error con {ticker}: {e}")
            traceback.print_exc()
