"""Tests para el CRM worker."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from flows.crm.crm_worker import (
    COL_ESTADO,
    COL_ULTIMA_ACT,
    get_days_diff,
    get_message,
    process_crm,
)


class TestGetDaysDiff:
    def test_formato_completo(self):
        hoy = datetime.now()
        ayer = hoy - timedelta(days=1)
        assert get_days_diff(ayer.strftime("%d/%m/%Y %H:%M:%S")) == 1

    def test_formato_solo_fecha(self):
        assert get_days_diff((datetime.now() - timedelta(days=5)).strftime("%d/%m/%Y")) == 5

    def test_fecha_vacia_retorna_menos1(self):
        assert get_days_diff("") == -1

    def test_fecha_none_retorna_menos1(self):
        assert get_days_diff(None) == -1

    def test_formato_invalido_retorna_menos1(self):
        assert get_days_diff("no-es-una-fecha") == -1


class TestGetMessage:
    @pytest.mark.parametrize("msg_id,nombre,expected_substring", [
        (1, "Juan", "3 días"),
        (2, "María", "recta final"),
        (3, "Pedro", "últimas 24"),
        (4, "Ana", "te removió"),
        (5, "Luis", "30% de descuento"),
        (6, "Sofía", "estrategias"),
        (7, "Carlos", "precio anterior"),
    ])
    def test_mensajes_existentes(self, msg_id, nombre, expected_substring):
        msg = get_message(msg_id, nombre)
        assert nombre in msg
        assert expected_substring.lower() in msg.lower()

    def test_mensaje_inexistente_retorna_vacio(self):
        assert get_message(99, "Test") == ""
        assert get_message(0, "Test") == ""


class TestProcessCRM:
    @pytest.fixture
    def mock_worksheet(self):
        ws = MagicMock()
        ws.get_all_values.return_value = []
        return ws

    def _make_row(
        self,
        telefono="5491111111111",
        nombre="Test",
        mail="test@mail.com",
        fecha_captura=None,
        origen="Instagram",
        estado="Trial0",
        fecha_baja="",
    ):
        if fecha_captura is None:
            fecha_captura = (datetime.now() - timedelta(days=3)).strftime("%d/%m/%Y %H:%M:%S")
        return [
            telefono, nombre, mail, fecha_captura, origen, estado, fecha_baja,
            "", "",
        ]

    def test_sheet_vacio(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = []
        with patch("flows.crm.crm_worker._get_worksheet", return_value=mock_worksheet):
            process_crm()
        mock_worksheet.update_cells.assert_not_called()

    def test_solo_header(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["telefono", "nombre", "mail", "fecha", "origen", "estado", "fecha_baja", "", "ultima_act"],
        ]
        with patch("flows.crm.crm_worker._get_worksheet", return_value=mock_worksheet):
            process_crm()
        mock_worksheet.update_cells.assert_not_called()

    @pytest.mark.parametrize("estado_inicial,estado_esperado,msg_id_esperado,remueve_grupo", [
        ("Trial0", "Trial3", 1, False),
        ("Trial 0", "Trial3", 1, False),
        ("Trial3", "Trial5", 2, False),
        ("Trial5", "Trial6", 3, False),
        ("Trial6", "Eliminado", 4, True),
        ("Eliminado", "Retargeting 15", 5, False),
        ("Retargeting 15", "Retargeting Final", 6, False),
    ])
    def test_transicion_estados(
        self,
        mock_worksheet,
        estado_inicial,
        estado_esperado,
        msg_id_esperado,
        remueve_grupo,
    ):
        dias = 3 if estado_inicial in ("Trial0", "Trial 0") else (
            5 if estado_inicial == "Trial3" else
            6 if estado_inicial == "Trial5" else
            7 if estado_inicial == "Trial6" else
            22 if estado_inicial == "Eliminado" else
            47
        )
        fecha = (datetime.now() - timedelta(days=dias)).strftime("%d/%m/%Y %H:%M:%S")

        mock_worksheet.get_all_values.return_value = [
            ["tel", "nombre", "mail", "fecha", "origen", "estado", "fecha_baja", "", "ult"],
            self._make_row(fecha_captura=fecha, estado=estado_inicial),
        ]

        def cell_side_effect(row, col):
            c = MagicMock()
            if estado_inicial == "Trial0":
                c.value = estado_esperado if col == COL_ESTADO else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            else:
                c.value = "valor"
            return c

        mock_worksheet.cell.side_effect = cell_side_effect

        with patch("flows.crm.crm_worker._get_worksheet", return_value=mock_worksheet):
            with patch("flows.crm.crm_worker.evolution_client.send_text") as mock_send:
                with patch("flows.crm.crm_worker.evolution_client.remove_participant_from_group") as mock_remove:
                    process_crm()

        assert mock_worksheet.update_cells.called
        if remueve_grupo:
            mock_remove.assert_called_once()

    def test_premium_se_skip(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["tel", "nombre", "mail", "fecha", "origen", "estado", "fecha_baja", "", "ult"],
            self._make_row(estado="Premium"),
            self._make_row(estado="Baja Final"),
            self._make_row(estado="Retargeting Final"),
            self._make_row(estado="Eliminado Definitivo"),
        ]
        with patch("flows.crm.crm_worker._get_worksheet", return_value=mock_worksheet):
            with patch("flows.crm.crm_worker.evolution_client.send_text") as mock_send:
                process_crm()

        mock_send.assert_not_called()
        mock_worksheet.update_cells.assert_not_called()

    def test_transicion_baja_a_baja_final(self, mock_worksheet):
        fecha_baja = (datetime.now() - timedelta(days=60)).strftime("%d/%m/%Y %H:%M:%S")
        fecha_captura = (datetime.now() - timedelta(days=100)).strftime("%d/%m/%Y %H:%M:%S")

        mock_worksheet.get_all_values.return_value = [
            ["tel", "nombre", "mail", "fecha", "origen", "estado", "fecha_baja", "", "ult"],
            [
                "5491111111111", "Test", "test@mail.com", fecha_captura,
                "Instagram", "Baja", fecha_baja, "", "",
            ],
        ]

        def cell_side_effect(row, col):
            c = MagicMock()
            c.value = "Baja Final"
            return c

        mock_worksheet.cell.side_effect = cell_side_effect

        with patch("flows.crm.crm_worker._get_worksheet", return_value=mock_worksheet):
            with patch("flows.crm.crm_worker.evolution_client.send_text") as mock_send:
                process_crm()

        assert mock_worksheet.update_cells.called

    def test_lead_sin_telefono_se_skip(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["tel", "nombre", "mail", "fecha", "origen", "estado", "fecha_baja", "", "ult"],
            self._make_row(telefono="", estado="Trial0"),
        ]
        with patch("flows.crm.crm_worker._get_worksheet", return_value=mock_worksheet):
            with patch("flows.crm.crm_worker.evolution_client.send_text") as mock_send:
                process_crm()

        mock_send.assert_not_called()
