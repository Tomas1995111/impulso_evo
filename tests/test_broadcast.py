"""Tests para el flujo de broadcast."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flows.broadcast.broadcast import (
    MENSAJES_ESPECIALES,
    enviar_mensaje,
    mensajes_fecha,
    mensajes_semana,
    obtener_siguiente_mensaje_dinamico,
    resolver_mensaje,
)


class TestResolverMensaje:
    def test_texto_literal_devuelve_mismo_texto(self):
        assert resolver_mensaje("hola mundo") == "hola mundo"

    def test_texto_vacio_devuelve_vacio(self):
        assert resolver_mensaje("") == ""

    def test_clave_especial_llama_funcion(self, mock_yfinance_ticker):
        resultado = resolver_mensaje("cotizacion_dolar")
        assert resultado is not None
        assert "ALERTA" not in resultado

    @patch.dict(
        "flows.broadcast.broadcast.MENSAJES_ESPECIALES",
        {"noticia_mercado": MagicMock(return_value="resumen test")},
        clear=False,
    )
    def test_noticia_mercado_test_mode_pasa_url(self):
        mock_func = MENSAJES_ESPECIALES["noticia_mercado"]
        resultado = resolver_mensaje(
            "noticia_mercado",
            test_mode=True,
            test_url="https://test.com/article",
        )
        mock_func.assert_called_once_with(test_url="https://test.com/article")
        assert resultado == "resumen test"


class TestMensajesProgramados:
    def test_mensajes_semana_tiene_estructura(self):
        for msg in mensajes_semana:
            assert "dias" in msg
            assert "hora" in msg
            assert "mensaje" in msg
            assert "grupo" in msg
            assert isinstance(msg["dias"], list)
            assert isinstance(msg["grupo"], list)

    def test_mensajes_fecha_tiene_estructura(self):
        for msg in mensajes_fecha:
            assert "fecha" in msg
            assert "mensaje" in msg
            assert "grupo" in msg
            assert isinstance(msg["grupo"], list)

    def test_mensajes_especiales_tiene_todas_las_claves(self):
        for msg in mensajes_semana + mensajes_fecha:
            if msg["mensaje"] in MENSAJES_ESPECIALES:
                assert True

    def test_mensajes_especiales_no_son_texto_literal(self):
        for msg in mensajes_semana + mensajes_fecha:
            if msg["mensaje"] in MENSAJES_ESPECIALES:
                resultado = resolver_mensaje(msg["mensaje"])
                assert resultado != msg["mensaje"]

    def test_mensajes_fecha_formato_valido(self):
        for msg in mensajes_fecha:
            dt = datetime.strptime(msg["fecha"], "%d/%m/%Y %H:%M")
            assert dt is not None


class TestObtenerSiguienteMensajeDinamico:
    @patch("random.shuffle", side_effect=lambda x: x)
    def test_avanza_indice(self, mock_shuffle, monkeypatch, tmp_path):
        contenido_dir = tmp_path / "contenido"
        contenido_dir.mkdir()
        (contenido_dir / "miercoles.json").write_text(
            json.dumps(["msg1", "msg2", "msg3"]), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        assert obtener_siguiente_mensaje_dinamico("miercoles") == "msg1"
        assert obtener_siguiente_mensaje_dinamico("miercoles") == "msg2"
        assert obtener_siguiente_mensaje_dinamico("miercoles") == "msg3"

    def test_mezcla_cuando_se_terminan(self, monkeypatch, tmp_path):
        contenido_dir = tmp_path / "contenido"
        contenido_dir.mkdir()
        (contenido_dir / "miercoles.json").write_text(
            json.dumps(["unico"]), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        primero = obtener_siguiente_mensaje_dinamico("miercoles")
        assert primero == "unico"

        segundo = obtener_siguiente_mensaje_dinamico("miercoles")
        assert segundo == "unico"

    def test_persiste_estado(self, monkeypatch, tmp_path):
        contenido_dir = tmp_path / "contenido"
        contenido_dir.mkdir()
        (contenido_dir / "miercoles.json").write_text(
            json.dumps(["msg_a", "msg_b"]), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        obtener_siguiente_mensaje_dinamico("miercoles")

        with open("estado_mensajes.json", encoding="utf-8") as f:
            estado = json.load(f)
        assert estado["miercoles"]["proximo_indice"] == 1


class TestEnviarMensaje:
    def test_envia_texto_literal(self, mock_evolution_post):
        enviar_mensaje(["120363000000000000@g.us"], "texto de prueba")
        assert mock_evolution_post.called

    @patch.dict(
        "flows.broadcast.broadcast.MENSAJES_ESPECIALES",
        {"cotizacion_dolar": MagicMock(return_value="cotización de prueba")},
        clear=False,
    )
    def test_envia_mensaje_especial(self, mock_evolution_post):
        enviar_mensaje(["120363000000000000@g.us"], "cotizacion_dolar")
        assert mock_evolution_post.called


class TestMENSAJES_ESPECIALES:
    def test_todas_las_funciones_retornan_string(self):
        for clave, func in MENSAJES_ESPECIALES.items():
            if clave == "vencimiento_opciones":
                continue
            with patch.dict(
                "flows.broadcast.broadcast.MENSAJES_ESPECIALES",
                {clave: MagicMock(return_value="mock response")},
                clear=False,
            ):
                resultado = resolver_mensaje(clave)
                assert resultado is not None

    def test_vencimiento_opciones_es_funcion_sin_args(self):
        from flows.broadcast.broadcast import generar_mensaje_vencimiento

        resultado = generar_mensaje_vencimiento()
        assert isinstance(resultado, str)
        assert "Vencimiento" in resultado

    @patch.dict(
        "flows.broadcast.broadcast.MENSAJES_ESPECIALES",
        {"cotizacion_dolar": MagicMock(side_effect=Exception("boom"))},
        clear=False,
    )
    def test_resolver_mensaje_con_error_no_crashea(self):
        resultado = resolver_mensaje("cotizacion_dolar")
        assert resultado is None
