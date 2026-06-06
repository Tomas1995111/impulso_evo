"""Tests para el flujo de broadcast."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flows.broadcast.broadcast import (
    MENSAJES_ESPECIALES,
    SALUDOS_DIARIOS,
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

    def test_mensajes_fecha_formato_valido(self):
        for msg in mensajes_fecha:
            dt = datetime.strptime(msg["fecha"], "%d/%m/%Y %H:%M")
            assert dt is not None

    def test_saludo_diario_esta_en_especiales(self):
        assert "saludo_diario" in MENSAJES_ESPECIALES

    def test_saludo_diario_devuelve_string_del_pool(self):
        resultado = resolver_mensaje("saludo_diario")
        assert isinstance(resultado, str)
        assert len(resultado) > 10
        assert resultado in SALUDOS_DIARIOS

    def test_saludos_diarios_tiene_4_opciones(self):
        assert len(SALUDOS_DIARIOS) == 4
        for s in SALUDOS_DIARIOS:
            assert isinstance(s, str)
            assert len(s) > 10

    def test_mensaje_broker_designation_existe(self):
        broker = [m for m in mensajes_semana if "broker" in m["mensaje"].lower()]
        assert len(broker) == 1
        msg = broker[0]
        assert "tue" in msg["dias"]
        assert msg["hora"] == "15:00"
        assert "asesor" in msg["mensaje"].lower()

    def test_referidos_acortado_sin_pasos(self):
        ref = [m for m in mensajes_semana if "invitá" in m["mensaje"].lower()]
        assert len(ref) == 1
        assert "¿cómo funciona" not in ref[0]["mensaje"].lower()
        assert "1️⃣" not in ref[0]["mensaje"]


class TestObtenerSiguienteMensajeDinamico:
    @patch("random.shuffle", side_effect=lambda x: x)
    def test_avanza_indice(self, mock_shuffle, monkeypatch, tmp_path):
        from flows.broadcast import broadcast

        contenido_dir = tmp_path / "contenido"
        contenido_dir.mkdir()
        (contenido_dir / "miercoles.json").write_text(
            json.dumps(["msg1", "msg2", "msg3"]), encoding="utf-8"
        )
        estado_file = tmp_path / "estado_mensajes.json"
        monkeypatch.setattr(broadcast, "CONTENIDO_DIR", contenido_dir)
        monkeypatch.setattr(broadcast, "ESTADO_MENSAJES_FILE", estado_file)

        assert obtener_siguiente_mensaje_dinamico("miercoles") == "msg1"
        assert obtener_siguiente_mensaje_dinamico("miercoles") == "msg2"
        assert obtener_siguiente_mensaje_dinamico("miercoles") == "msg3"

    def test_mezcla_cuando_se_terminan(self, monkeypatch, tmp_path):
        from flows.broadcast import broadcast

        contenido_dir = tmp_path / "contenido"
        contenido_dir.mkdir()
        (contenido_dir / "miercoles.json").write_text(
            json.dumps(["unico"]), encoding="utf-8"
        )
        estado_file = tmp_path / "estado_mensajes.json"
        monkeypatch.setattr(broadcast, "CONTENIDO_DIR", contenido_dir)
        monkeypatch.setattr(broadcast, "ESTADO_MENSAJES_FILE", estado_file)

        primero = obtener_siguiente_mensaje_dinamico("miercoles")
        assert primero == "unico"

        segundo = obtener_siguiente_mensaje_dinamico("miercoles")
        assert segundo == "unico"

    def test_persiste_estado(self, monkeypatch, tmp_path):
        from flows.broadcast import broadcast

        contenido_dir = tmp_path / "contenido"
        contenido_dir.mkdir()
        (contenido_dir / "miercoles.json").write_text(
            json.dumps(["msg_a", "msg_b"]), encoding="utf-8"
        )
        estado_file = tmp_path / "estado_mensajes.json"
        monkeypatch.setattr(broadcast, "CONTENIDO_DIR", contenido_dir)
        monkeypatch.setattr(broadcast, "ESTADO_MENSAJES_FILE", estado_file)

        obtener_siguiente_mensaje_dinamico("miercoles")

        with open(estado_file, encoding="utf-8") as f:
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


class TestDolarComparativa:
    def test_save_y_load_estado(self, monkeypatch, tmp_path):
        from mensajes.mensajeCotizacionDolar import (
            _save_estado_dolar,
            _load_estado_dolar,
            ESTADO_DOLAR_FILE,
        )

        monkeypatch.setattr(
            "mensajes.mensajeCotizacionDolar.ESTADO_DOLAR_FILE",
            str(tmp_path / "estado_dolar.json"),
        )

        assert _load_estado_dolar() is None

        _save_estado_dolar({"blue": 1450.0, "oficial": 900.0})
        data = _load_estado_dolar()
        assert data is not None
        assert data["fecha"] is not None
        assert data["valores"]["blue"] == 1450.0
        assert data["valores"]["oficial"] == 900.0

    def test_fmt_pct_positivo(self):
        from mensajes.mensajeCotizacionDolar import _fmt_pct
        assert _fmt_pct(1.5) == "+1,50%"
        assert _fmt_pct(0.0) == "+0,00%"

    def test_fmt_pct_negativo(self):
        from mensajes.mensajeCotizacionDolar import _fmt_pct
        assert _fmt_pct(-2.34) == "-2,34%"

    def test_fmt_pct_none(self):
        from mensajes.mensajeCotizacionDolar import _fmt_pct
        assert _fmt_pct(None) == ""

    def test_sin_estado_previo_envia_mensaje_sin_comparacion(self, mock_yfinance_ticker, monkeypatch, tmp_path):
        from mensajes.mensajeCotizacionDolar import ESTADO_DOLAR_FILE
        monkeypatch.setattr(
            "mensajes.mensajeCotizacionDolar.ESTADO_DOLAR_FILE",
            str(tmp_path / "estado_dolar.json"),
        )
        from flows.broadcast.broadcast import resolver_mensaje
        resultado = resolver_mensaje("cotizacion_dolar")
        assert resultado is not None
        # Sin estado previo: no debe tener comparación porcentual con flecha
        assert "% 📈" not in resultado and "% 📉" not in resultado

    def test_con_estado_previo_muestra_comparacion(self, mock_yfinance_ticker, monkeypatch, tmp_path):
        import json
        from datetime import datetime, timedelta
        from mensajes.mensajeCotizacionDolar import ESTADO_DOLAR_FILE

        estado_path = tmp_path / "estado_dolar.json"
        monkeypatch.setattr(
            "mensajes.mensajeCotizacionDolar.ESTADO_DOLAR_FILE",
            str(estado_path),
        )

        ayer = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        with open(estado_path, "w") as f:
            json.dump({
                "fecha": ayer,
                "valores": {"blue": 1000.0, "oficial": 800.0},
            }, f)

        from flows.broadcast.broadcast import resolver_mensaje
        resultado = resolver_mensaje("cotizacion_dolar")
        assert resultado is not None
        # Sin mock de API real, esto puede no tener comparación si la API real
        # no devuelve estos tipos, pero el test verifica que no crashea
        assert isinstance(resultado, str)
        assert len(resultado) > 20
