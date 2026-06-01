from __future__ import annotations

import json
import time
from typing import Optional

import redis

from core import config


class ConversationStateStore:
    """Estado mínimo de conversación por teléfono (Redis).

    Estados:
      - idle
      - awaiting_name
      - awaiting_email
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self._r = redis_client or redis.Redis(
            host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True,
            socket_connect_timeout=3, socket_timeout=3,
        )

    def _key(self, phone: str) -> str:
        return f"inbound:{phone}"

    def get_state(self, phone: str) -> str:
        raw = self._r.get(self._key(phone))
        if not raw:
            return "idle"
        try:
            data = json.loads(raw)
        except Exception:
            return "idle"
        return str(data.get("state") or "idle")

    def set_state(self, phone: str, state: str) -> None:
        data = self._get_data(phone) or {}
        data["state"] = state
        self._set_data(phone, data)

    def set_state_with_ts(self, phone: str, state: str) -> None:
        """set_state + timestamp para detectar abandonos."""
        data = self._get_data(phone) or {}
        data["state"] = state
        if state == "awaiting_email":
            data["awaiting_since"] = time.time()
        self._set_data(phone, data)

    def start(self, *, phone: str, origen: str) -> None:
        data = {
            "state": "awaiting_name",
            "origen": origen or "",
            "name": "",
        }
        self._set_data(phone, data, ttl_seconds=config.INBOUND_TTL_SECONDS)  # 6h

    def set_name(self, phone: str, name: str) -> None:
        data = self._get_data(phone) or {}
        data["name"] = name
        self._set_data(phone, data)

    def get_name(self, phone: str) -> Optional[str]:
        return (self._get_data(phone) or {}).get("name")

    def get_origen(self, phone: str) -> Optional[str]:
        return (self._get_data(phone) or {}).get("origen")

    def reset(self, phone: str) -> None:
        self._r.delete(self._key(phone))

    def _get_data(self, phone: str) -> Optional[dict]:
        raw = self._r.get(self._key(phone))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def _set_data(self, phone: str, data: dict, ttl_seconds: int = config.INBOUND_TTL_SECONDS) -> None:
        self._r.set(self._key(phone), json.dumps(data), ex=ttl_seconds) 