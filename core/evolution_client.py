"""Cliente HTTP hacia Evolution API (envío de texto, consulta de conexión)."""
import logging
import time
from datetime import datetime
from functools import wraps

import requests

from core import config

logger = logging.getLogger(__name__)


def _evolution_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator: reintenta con exponential backoff si falla la request."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Reintento {attempt + 1}/{max_retries} tras {delay}s: {e}")
                        time.sleep(delay)
            logger.error(f"Fallo tras {max_retries} intentos: {last_exc}")
            return None
        return wrapper
    return decorator


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
    while True:
        try:
            res = requests.get(url_connection_state(), headers=headers(), timeout=5)
            estado = res.json().get("instance", {}).get("state", "").lower()
            if estado == "open":
                logger.info("WhatsApp conectado y listo para enviar!")
                return
            logger.info(f"WhatsApp está en estado '{estado}'. Esperando {poll_seconds} segundos...")
        except Exception:
            logger.info(f"Evolution API está cargando... Esperando {poll_seconds} segundos...")
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
            res = requests.post(url, json=payload, headers=hdrs, timeout=15)
            logger.info(f"Enviado a {numero}. Estado: {res.status_code}")
        except Exception as e:
            logger.error(f"No se pudo enviar a {numero}: {e}")


def send_text(jid: str, texto: str) -> bool:
    """Envía texto a un JID exacto (ej: 54911...@s.whatsapp.net o ...@g.us).
    Retorna True si se envió correctamente."""
    if not jid or not texto:
        return False
    payload = {"number": jid, "text": texto}
    try:
        res = requests.post(url_send_text(), json=payload, headers=headers(), timeout=15)
        ok = 200 <= res.status_code < 300
        logger.info(f"Enviado a {jid}. Estado: {res.status_code}")
        return ok
    except Exception as e:
        logger.error(f"No se pudo enviar a {jid}: {e}")
        return False


@_evolution_retry(max_retries=2, base_delay=2.0)
def remove_participant_from_group(group_jid: str, participant_phone: str) -> bool:
    """Remueve un participante del grupo usando Evolution API.

    group_jid: JID del grupo (....@g.us)
    participant_phone: número en formato solo dígitos (ej: 54911...)
    """
    if not group_jid or not participant_phone:
        return False
    participant_jid = f"{participant_phone}@s.whatsapp.net"
    res = requests.post(
        url_group_update_participant(),
        params={"groupJid": group_jid},
        json={"action": "remove", "participants": [participant_jid]},
        headers=headers(),
        timeout=15,
    )
    ok = 200 <= res.status_code < 300
    logger.info(f"remove_participant_from_group({group_jid}, {participant_phone}) -> {res.status_code}")
    return ok


@_evolution_retry(max_retries=2, base_delay=2.0)
def add_participant_to_group(group_jid: str, participant_phone: str) -> bool:
    """Agrega un participante al grupo usando Evolution API.

    group_jid: JID del grupo (....@g.us)
    participant_phone: número en formato solo dígitos (ej: 54911...)
    """
    if not group_jid or not participant_phone:
        return False
    res = requests.post(
        url_group_update_participant(),
        params={"groupJid": group_jid},
        json={"action": "add", "participants": [participant_phone]},
        headers=headers(),
        timeout=15,
    )
    ok = 200 <= res.status_code < 300
    logger.info(f"add_participant_to_group({group_jid}, {participant_phone}) -> {res.status_code}")
    return ok
