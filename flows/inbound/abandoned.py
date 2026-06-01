"""Escanea Redis buscando conversaciones estancadas en awaiting_email > 30 min."""
import json
import time

import redis

from core import config
from core import evolution_client

UMBRAL_MINUTOS = config.ABANDONED_UMBRAL_MINUTOS


def check_abandoned_conversations() -> None:
    r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True,
                    socket_connect_timeout=3, socket_timeout=3)
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match="inbound:*", count=100)
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if data.get("state") != "awaiting_email":
                continue
            awaiting_since = data.get("awaiting_since")
            if awaiting_since is None:
                continue
            elapsed = time.time() - float(awaiting_since)
            if elapsed > UMBRAL_MINUTOS * 60:
                phone = key.split(":")[1]
                nombre = data.get("name", "")
                remote_jid = f"{phone}@s.whatsapp.net"
                msg = (
                    f"¡Hola {nombre}!, te quedó el registro a medio hacer 🙌\n\n"
                    "Pasame tu mail y en un toque te sumo al grupo de prueba."
                )
                if evolution_client.send_text(remote_jid, msg):
                    r.delete(key)
        if cursor == 0:
            break
