from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request

from core import config
from core import evolution_client
from core import sheets_client
from flows.inbound.state import ConversationStateStore

logger = logging.getLogger(__name__)


app = FastAPI()
store = ConversationStateStore()


MSG_ASK_NAME = (
    "¡Qué bueno que quieras sumarte! 📊 "
    "Te voy a dar acceso al grupo de prueba para que arranques con el resumen diario. "
    "Primero, decime tu nombre."
)


def _normalize(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


TRIGGER_PHRASES = [
    "prueba gratis",
    "prueba gratuita",
    "quiero info",
    "me interesa",
    "quiero sumarme",
    "cómo entro",
    "como entro",
    "quiero entrar",
    "dame acceso",
    "info",
]


def _origin_from_text(text: str) -> str:
    t = _normalize(text)
    if "prueba gratis" in t:
        return "Instagram"
    if "prueba gratuita" in t:
        return "TikTok"
    return ""


def _es_trigger(text_norm: str) -> bool:
    if not text_norm:
        return False
    if "impulso" in text_norm or "merval" in text_norm or "mercado" in text_norm:
        return True
    return any(phrase in text_norm for phrase in TRIGGER_PHRASES)


def _extract_text(message_obj: Any) -> str:
    """Intenta extraer texto de distintos tipos de payload."""
    if not isinstance(message_obj, dict):
        return ""
    # Conversación simple
    if isinstance(message_obj.get("conversation"), str):
        return message_obj["conversation"]
    # extendedTextMessage
    ext = message_obj.get("extendedTextMessage")
    if isinstance(ext, dict) and isinstance(ext.get("text"), str):
        return ext["text"]
    # caption de media
    for k in ("imageMessage", "videoMessage", "documentMessage"):
        mm = message_obj.get(k)
        if isinstance(mm, dict) and isinstance(mm.get("caption"), str):
            return mm["caption"]
    return ""


def _safe_get(d: Any, *path: str) -> Optional[Any]:
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _parse_webhook(payload: dict) -> tuple[str, str, bool]:
    """Devuelve (remote_jid, text, from_me)."""
    key = payload.get("key") or _safe_get(payload, "data", "key") or {}
    remote_jid = (
        _safe_get(payload, "data", "key", "remoteJid")
        or _safe_get(payload, "key", "remoteJid")
        or payload.get("remoteJid")
        or key.get("remoteJid")
        or ""
    )
    from_me = bool(
        _safe_get(payload, "data", "key", "fromMe")
        or _safe_get(payload, "key", "fromMe")
        or key.get("fromMe")
        or payload.get("fromMe")
    )

    message_obj = payload.get("message") or _safe_get(payload, "data", "message") or {}
    text = _extract_text(message_obj)

    # En algunos payloads viene messageType, pero acá nos basta con texto.
    return str(remote_jid), str(text or ""), from_me


def _phone_from_remote_jid(remote_jid: str) -> str:
    # 54911...@s.whatsapp.net
    phone = (remote_jid or "").split("@")[0]
    phone = re.sub(r"\D+", "", phone)
    return phone


def _is_group_jid(remote_jid: str) -> bool:
    return (remote_jid or "").endswith("@g.us")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# Evolución docs: si usás webhook "by events", el path suele ser /messages-upsert
@app.post("/messages-upsert")
@app.post("/webhook/messages-upsert")
async def messages_upsert(request: Request) -> dict:
    secret = os.getenv("INBOUND_WEBHOOK_SECRET", "")
    if secret:
        token = request.headers.get("apikey") or request.headers.get("API-KEY") or ""
        if token != secret:
            raise HTTPException(status_code=403, detail="unauthorized")

    payload = await request.json()

    remote_jid, text, from_me = _parse_webhook(payload)

    # Ignorar mensajes enviados por el bot o mensajes de grupos (queremos solo DM)
    if from_me or not remote_jid or _is_group_jid(remote_jid):
        return {"ignored": True}

    phone = _phone_from_remote_jid(remote_jid)
    if not phone:
        return {"ignored": True}

    text_norm = _normalize(text)
    state = store.get_state(phone)

    # 1) Trigger
    if state == "idle":
        # Comandos (ej: /alerta MSFT COME.BA)
        if text.startswith("/"):
            from flows.inbound.commands import handle_command
            handle_command(remote_jid, text)
            return {"ok": True, "state": "idle"}

        if _es_trigger(text_norm):
            try:
                from core.sheets_client import phone_exists
                if phone_exists(phone):
                    return {"ok": True, "state": "idle"}
            except Exception:
                pass
            origen = _origin_from_text(text_norm)
            store.start(phone=phone, origen=origen)
            evolution_client.send_text(remote_jid, MSG_ASK_NAME)
            return {"ok": True, "state": "awaiting_name"}
        return {"ok": True, "state": "idle"}

    # 2) Nombre
    if state == "awaiting_name":
        nombre = text.strip()
        if not nombre:
            evolution_client.send_text(remote_jid, MSG_ASK_NAME)
            return {"ok": True, "state": "awaiting_name"}

        store.set_name(phone, nombre)
        evolution_client.send_text(
            remote_jid,
            f"¡Gracias {nombre}! Ahora pasame tu mail y en un toque estás adentro.",
        )
        store.set_state_with_ts(phone, "awaiting_email")
        return {"ok": True, "state": "awaiting_email"}

    # 3) Mail (sin validación pesada)
    if state == "awaiting_email":
        mail = text.strip()
        nombre = store.get_name(phone) or ""
        origen = store.get_origen(phone) or ""

        fecha_captura = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%d/%m/%Y %H:%M")

        # Agregar al grupo Trial
        trial_group = config.TRIAL_GROUP_JID
        added = evolution_client.add_participant_to_group(trial_group, remote_jid)

        # Guardar en Sheet (append siempre)
        sheet_saved = True
        try:
            sheets_client.append_lead_row(
                sheet_id=config.LEADS_SHEET_ID,
                tab_name=config.LEADS_SHEET_TAB,
                telefono=phone,
                nombre=nombre,
                mail=mail,
                fecha_captura=fecha_captura,
                origen=origen,
                estado="Trial0",
            )
        except Exception as e:
            sheet_saved = False
            logger.error("No se pudo guardar lead en Google Sheets: %s", e)

        final_msg = (
            f"Listo {nombre}, ya estás adentro del grupo de prueba 🚀\n\n"
            "La dinámica acá es simple:\n"
            "📬 Por la mañana te llega el resumen del día con lo más importante del mercado.\n"
            "📈 Estrategias re masticadas para que sepas qué hacer.\n"
            "💬 Cualquier duda, me escribís por acá sin problema.\n\n"
            "¡Bienvenido a Impulso Merval! Mañana arrancamos temprano 📊\n"
            "—Juan"
        )
        if not added:
            final_msg = (
                f"Listo {nombre}, ya cargué tus datos. En un par de minutos te agrego al grupo de prueba.\n\n"
                "Si no aparecés, decime por acá y lo vemos al toque."
            )
        elif not sheet_saved:
            final_msg = (
                f"Ya te sumé al grupo de prueba {nombre}! 🚀\n\n"
                "Cualquier cosa que necesites, respondeme por acá."
            )

        evolution_client.send_text(remote_jid, final_msg)
        store.reset(phone)
        return {"ok": True, "state": "done"}

    # Fallback
    store.reset(phone)
    return {"ok": True, "state": "reset"}
