"""Tests para el flujo de inbound webhook."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import fakeredis
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client(fake_redis) -> TestClient:
    from flows.inbound.inbound import app, store

    store._r = fake_redis
    app.state.store = store

    with TestClient(app) as c:
        yield c


def _payload(
    text: str = "Quiero prueba gratis de Impulso Merval",
    remote_jid: str = "5491123456789@s.whatsapp.net",
    from_me: bool = False,
    nested: bool = False,
) -> dict:
    msg = {"conversation": text}
    key = {"remoteJid": remote_jid, "fromMe": from_me}
    if nested:
        return {"data": {"key": key, "message": msg}}
    return {"key": key, "message": msg}


class TestWebhookSeguridad:
    @patch.dict("os.environ", {"INBOUND_WEBHOOK_SECRET": "mi-secreto"}, clear=False)
    def test_rechaza_sin_token(self, client):
        resp = client.post("/messages-upsert", json=_payload("hola"))
        assert resp.status_code == 403

    @patch.dict("os.environ", {"INBOUND_WEBHOOK_SECRET": "mi-secreto"}, clear=False)
    def test_rechaza_token_incorrecto(self, client):
        resp = client.post(
            "/messages-upsert",
            json=_payload("hola"),
            headers={"apikey": "token-malo"},
        )
        assert resp.status_code == 403

    @patch.dict("os.environ", {"INBOUND_WEBHOOK_SECRET": "mi-secreto"}, clear=False)
    def test_acepta_token_correcto(self, client):
        with patch("flows.inbound.inbound.evolution_client.send_text") as mock_send:
            resp = client.post(
                "/messages-upsert",
                json=_payload("simple text"),
                headers={"apikey": "mi-secreto"},
            )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "state": "idle"}

    @patch.dict("os.environ", {"INBOUND_WEBHOOK_SECRET": ""}, clear=False)
    def test_funciona_sin_token_configurado(self, client):
        with patch("flows.inbound.inbound.evolution_client.send_text") as mock_send:
            resp = client.post("/messages-upsert", json=_payload("simple text"))
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "state": "idle"}


class TestConversationFlow:
    def test_trigger_idle_to_awaiting_name(self, client, mock_evolution_post):
        resp = client.post("/messages-upsert", json=_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "awaiting_name"

    def test_trigger_con_extended_text_message(self, client, mock_evolution_post):
        payload = {
            "key": {"remoteJid": "5491123456789@s.whatsapp.net", "fromMe": False},
            "message": {
                "extendedTextMessage": {
                    "text": "Quiero una prueba gratis de Impulso Merval"
                }
            },
        }
        resp = client.post("/messages-upsert", json=payload)
        assert resp.status_code == 200
        assert resp.json()["state"] == "awaiting_name"

    def test_awaiting_name_sends_ask_name(self, client, mock_evolution_post):
        client.post("/messages-upsert", json=_payload())
        resp = client.post(
            "/messages-upsert",
            json=_payload(text="Juan Perez"),
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "awaiting_email"

    def test_full_flow_to_done(self, client, mock_evolution_post, mock_sheets_append):
        client.post("/messages-upsert", json=_payload())
        client.post("/messages-upsert", json=_payload(text="Juan Perez"))
        resp = client.post(
            "/messages-upsert",
            json=_payload(text="juan@mail.com"),
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "done"
        mock_sheets_append.assert_called_once()

    def test_awaiting_name_empty_retries(self, client, mock_evolution_post):
        client.post("/messages-upsert", json=_payload())
        resp = client.post(
            "/messages-upsert",
            json=_payload(text="   "),
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "awaiting_name"

    def test_done_resets_state(self, client, mock_evolution_post, mock_sheets_append):
        client.post("/messages-upsert", json=_payload())
        client.post("/messages-upsert", json=_payload(text="Juan Perez"))
        client.post("/messages-upsert", json=_payload(text="juan@mail.com"))
        resp = client.post(
            "/messages-upsert",
            json=_payload(text="otro mensaje"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "idle"


class TestFilters:
    def test_from_me_ignored(self, client):
        payload = _payload(from_me=True)
        resp = client.post("/messages-upsert", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"ignored": True}

    def test_mensaje_de_grupo_ignored(self, client):
        payload = _payload(remote_jid="120363000000000000@g.us")
        resp = client.post("/messages-upsert", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"ignored": True}

    def test_sin_texto_ignored(self, client):
        payload = {
            "key": {"remoteJid": "5491123456789@s.whatsapp.net", "fromMe": False},
            "message": {"imageMessage": {"mimetype": "image/jpeg", "caption": ""}},
        }
        resp = client.post("/messages-upsert", json=payload)
        assert resp.status_code == 200

    def test_payload_anidado_data(self, client, mock_evolution_post):
        payload = _payload(nested=True)
        resp = client.post("/messages-upsert", json=payload)
        assert resp.status_code == 200


class TestToleranciaFallos:
    def test_fallo_en_add_to_group_continua(self, client, mock_evolution_post, mock_sheets_append):
        mock_evolution_post.return_value.status_code = 500

        client.post("/messages-upsert", json=_payload())
        client.post("/messages-upsert", json=_payload(text="Juan Perez"))
        resp = client.post(
            "/messages-upsert",
            json=_payload(text="juan@mail.com"),
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "done"
        mock_sheets_append.assert_called_once()

    def test_fallo_en_sheets_continua(self, client, mock_evolution_post, mock_sheets_append):
        mock_sheets_append.side_effect = Exception("Sheet error")

        client.post("/messages-upsert", json=_payload())
        client.post("/messages-upsert", json=_payload(text="Juan Perez"))
        resp = client.post(
            "/messages-upsert",
            json=_payload(text="juan@mail.com"),
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "done"


class TestOrigenDetection:
    @pytest.mark.parametrize("text,expected_state", [
        ("prueba gratis de Impulso Merval", "awaiting_name"),
        ("PRUEBA GRATUITA impulso merval", "awaiting_name"),
        ("Quiero info de Impulso Merval", "idle"),
        ("Hola como estas", "idle"),
    ])
    def test_detecta_origen(self, text, expected_state, client, mock_evolution_post):
        resp = client.post("/messages-upsert", json=_payload(text=text))
        assert resp.status_code == 200
        assert resp.json()["state"] == expected_state

    def test_origin_instagram_detectado(self, client, mock_evolution_post):
        payload = _payload(text="prueba gratis impulso merval")
        resp = client.post("/messages-upsert", json=payload)
        assert resp.status_code == 200
        assert resp.json()["state"] == "awaiting_name"
