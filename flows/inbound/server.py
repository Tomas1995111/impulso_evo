from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import FastAPI, Request

from core import config
from core import evolution_client
from core import sheets_client
from flows.inbound.state import ConversationStateStore


app = FastAPI()
store = ConversationStateStore()


MSG_ASK_NAME = (
    "¡Excelente! Ya estás a un paso de empezar tu prueba. "
    "Para habilitar tu acceso, por favor decime tu nombre completo."
)


def _normalize(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _origin_from_text(text: str) -> str:
    t = _normalize(text)
    if "prueba gratis" in t:
        return "Instagram"
    if "prueba gratuita" in t:
        return "TikTok"
    return ""


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
        origen = _origin_from_text(text_norm)
        if "impulso merval" in text_norm and "prueba" in text_norm:
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
            f"¡Gracias {nombre}! Y por último, ¿cuál es tu correo electrónico?",
        )
        store.set_state(phone, "awaiting_email")
        return {"ok": True, "state": "awaiting_email"}

    # 3) Mail (sin validación pesada)
    if state == "awaiting_email":
        mail = text.strip()
        nombre = store.get_name(phone) or ""
        origen = store.get_origen(phone) or ""
        
        # Forzamos la hora actual menos 3 horas directamente
        fecha_captura = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")

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
            print(f"[ERROR] No se pudo guardar lead en Google Sheets: {e}")

        final_msg = (
            f"¡Excelente, {nombre}! 🚀\n\n"
            "Ya te sumé al grupo para que arranques tus 7 días de prueba gratis.\n\n"
            "Así va a funcionar:\n"
            "🔇 Es silencioso: Solo los administradores mandamos información para no llenarte de notificaciones.\n"
            "📈 Información útil: Recibís el resumen diario del mercado e ideas de inversión explicadas bien simple.\n"
            "💬 Dudas: El grupo no se abre, pero cualquier pregunta me la podés mandar por acá mismo en privado.\n\n"
            "¡Bienvenido a Impulso Merval! Estate atento al grupo que estaremos enviando info. 📊"
        )
        if not added:
            # Si no se pudo agregar al grupo (permisos, admin, etc.), igual no frenamos el flujo
            final_msg = (
                f"¡Excelente, {nombre}! 🚀\n\n"
                "Ya registré tus datos. En unos minutos te sumo al grupo de la prueba.\n\n"
                "Si no te llega la invitación, respondeme por acá y lo resolvemos."
            )
        elif not sheet_saved:
            # No frenamos onboarding por un problema de Sheets.
            final_msg = (
                f"¡Excelente, {nombre}! 🚀\n\n"
                "Ya te sumé al grupo para que arranques tu prueba gratis.\n\n"
                "Si ves algo raro en el alta, escribime por acá y lo resolvemos enseguida."
            )

        evolution_client.send_text(remote_jid, final_msg)
        store.reset(phone)
        return {"ok": True, "state": "done"}

    # Fallback
    store.reset(phone)
    return {"ok": True, "state": "reset"}