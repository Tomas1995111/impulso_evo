"""Cliente HTTP hacia Evolution API (envío de texto, consulta de conexión)."""
from datetime import datetime

import requests

from core import config


def url_send_text() -> str:
    return (
        f"{config.EVOLUTION_API_URL}/message/sendText/"
        f"{config.EVOLUTION_INSTANCE_NAME}"
    )

def url_group_update_participant() -> str:
    return (
        f"{config.EVOLUTION_API_URL}/group/updateParticipant/"
        f"{config.EVOLUTION_INSTANCE_NAME}"
    )


def headers() -> dict:
    return {"apikey": config.EVOLUTION_API_KEY}


def url_connection_state() -> str:
    return (
        f"{config.EVOLUTION_API_URL}/instance/connectionState/"
        f"{config.EVOLUTION_INSTANCE_NAME}"
    )


def wait_whatsapp_open(poll_seconds: int = 5) -> None:
    """Espera hasta que la instancia reporte estado 'open' (modo test)."""
    import time

    while True:
        try:
            res = requests.get(url_connection_state(), headers=headers(), timeout=5)
            estado = res.json().get("instance", {}).get("state", "").lower()
            if estado == "open":
                print("✅ ¡WhatsApp conectado y listo para enviar!")
                return
            print(f"⏳ WhatsApp está en estado '{estado}'. Esperando {poll_seconds} segundos...")
        except Exception:
            print(f"⏳ Evolution API está cargando... Esperando {poll_seconds} segundos...")
        time.sleep(poll_seconds)


def send_text_to_destinations(grupo, texto: str) -> None:
    """Envía el mismo texto a uno o varios destinatarios (JID o número sin @)."""
    if not texto:
        return

    destinatarios = [grupo] if isinstance(grupo, str) else grupo
    url = url_send_text()
    hdrs = headers()

    for dest in destinatarios:
        numero = dest if "@" in dest else f"{dest}@g.us"
        payload = {"number": numero, "text": texto}
        try:
            res = requests.post(url, json=payload, headers=hdrs)
            print(f"[{datetime.now()}] Enviado a {numero}. Estado: {res.status_code}")
        except Exception as e:
            print(f"[ERROR] No se pudo enviar a {numero}: {e}")


def send_text(jid: str, texto: str) -> None:
    """Envía texto a un JID exacto (ej: 54911...@s.whatsapp.net o ...@g.us)."""
    if not jid or not texto:
        return
    payload = {"number": jid, "text": texto}
    try:
        res = requests.post(url_send_text(), json=payload, headers=headers())
        print(f"[{datetime.now()}] Enviado a {jid}. Estado: {res.status_code}")
    except Exception as e:
        print(f"[ERROR] No se pudo enviar a {jid}: {e}")


def add_participant_to_group(group_jid: str, participant_phone: str) -> bool:
    """Agrega un participante al grupo usando Evolution API.

    group_jid: JID del grupo (....@g.us)
    participant_phone: número en formato solo dígitos (ej: 54911...)
    """
    if not group_jid or not participant_phone:
        return False
    try:
        res = requests.post(
            url_group_update_participant(),
            params={"groupJid": group_jid},
            json={"action": "add", "participants": [participant_phone]},
            headers=headers(),
            timeout=15,
        )
        ok = 200 <= res.status_code < 300
        print(
            f"[{datetime.now()}] add_participant_to_group({group_jid}, {participant_phone}) -> {res.status_code}"
        )
        return ok
    except Exception as e:
        print(f"[ERROR] No se pudo agregar participante al grupo: {e}")
        return False
