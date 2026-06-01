"""Tests para el escáner de conversaciones abandonadas."""

import json
import time
from unittest.mock import patch

import fakeredis
import pytest


@pytest.fixture
def fake_redis_abandoned():
    return fakeredis.FakeRedis(decode_responses=True)


class TestCheckAbandoned:
    def test_no_abandonados_no_envia_mensaje(self, fake_redis_abandoned):
        from flows.inbound.abandoned import check_abandoned_conversations

        fake_redis_abandoned.set(
            "inbound:5491111111111",
            json.dumps({"state": "awaiting_name", "name": "Juan"}),
        )
        fake_redis_abandoned.set(
            "inbound:5491122222222",
            json.dumps({"state": "idle"}),
        )

        with patch("flows.inbound.abandoned.redis.Redis", return_value=fake_redis_abandoned):
            with patch("flows.inbound.abandoned.evolution_client.send_text") as mock_send:
                check_abandoned_conversations()

        mock_send.assert_not_called()

    def test_abandonado_reciente_no_envia_mensaje(self, fake_redis_abandoned):
        from flows.inbound.abandoned import check_abandoned_conversations

        fake_redis_abandoned.set(
            "inbound:5491111111111",
            json.dumps({
                "state": "awaiting_email",
                "name": "Juan",
                "awaiting_since": time.time() - 60,  # 1 minuto atrás
            }),
        )

        with patch("flows.inbound.abandoned.redis.Redis", return_value=fake_redis_abandoned):
            with patch("flows.inbound.abandoned.evolution_client.send_text") as mock_send:
                check_abandoned_conversations()

        mock_send.assert_not_called()

    def test_abandonado_30min_envia_recordatorio(self, fake_redis_abandoned):
        from flows.inbound.abandoned import check_abandoned_conversations

        fake_redis_abandoned.set(
            "inbound:5491111111111",
            json.dumps({
                "state": "awaiting_email",
                "name": "María",
                "awaiting_since": time.time() - 60 * 31,  # 31 min atrás
            }),
        )

        with patch("flows.inbound.abandoned.redis.Redis", return_value=fake_redis_abandoned):
            with patch("flows.inbound.abandoned.evolution_client.send_text") as mock_send:
                check_abandoned_conversations()

        mock_send.assert_called_once()
        jid = mock_send.call_args[0][0]
        assert "5491111111111" in jid

    def test_abandonado_elimina_estado_redis(self, fake_redis_abandoned):
        from flows.inbound.abandoned import check_abandoned_conversations

        fake_redis_abandoned.set(
            "inbound:5491111111111",
            json.dumps({
                "state": "awaiting_email",
                "name": "Pedro",
                "awaiting_since": time.time() - 60 * 31,
            }),
        )

        with patch("flows.inbound.abandoned.redis.Redis", return_value=fake_redis_abandoned):
            with patch("flows.inbound.abandoned.evolution_client.send_text"):
                check_abandoned_conversations()

        assert fake_redis_abandoned.get("inbound:5491111111111") is None

    def test_abandonado_sin_nombre_manda_saludo_generico(self, fake_redis_abandoned):
        from flows.inbound.abandoned import check_abandoned_conversations

        fake_redis_abandoned.set(
            "inbound:5491111111111",
            json.dumps({
                "state": "awaiting_email",
                "name": "",
                "awaiting_since": time.time() - 60 * 31,
            }),
        )

        with patch("flows.inbound.abandoned.redis.Redis", return_value=fake_redis_abandoned):
            with patch("flows.inbound.abandoned.evolution_client.send_text") as mock_send:
                check_abandoned_conversations()

        mock_send.assert_called_once()
        texto = mock_send.call_args[0][1]
        assert "registro a medio hacer" in texto
        assert "mail" in texto
