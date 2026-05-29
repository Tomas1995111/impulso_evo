from __future__ import annotations

import re
import traceback

from core import evolution_client
from core.alerts import generate_ticker_alert


def handle_command(remote_jid: str, text: str) -> bool:
    """Procesa un comando detectado. Retorna True si se manejó."""
    text = text.strip()

    m = re.match(r"^/alerta\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if m:
        _cmd_alerta(remote_jid, m.group(1))
        return True

    evolution_client.send_text(remote_jid, f"❌ Comando no reconocido: {text}")
    return True


def _cmd_alerta(remote_jid: str, args: str) -> None:
    tickers = args.upper().split()
    for ticker in tickers:
        try:
            mensaje = generate_ticker_alert(ticker)
            evolution_client.send_text(remote_jid, mensaje)
        except Exception as e:
            evolution_client.send_text(remote_jid, f"❌ Error con {ticker}: {e}")
            traceback.print_exc()
