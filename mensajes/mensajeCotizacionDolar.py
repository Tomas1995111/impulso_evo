# mensajes/mensajeCotizacionesDolar.py
import json
import logging
from datetime import datetime

import requests

from core import config

logger = logging.getLogger(__name__)

URL = "https://dolarapi.com/v1/dolares"
HEADERS = {"User-Agent": "Mozilla/5.0"}
ESTADO_DOLAR_FILE = str(config.BASE_DIR / "estado_dolar.json")

ORDEN_CASAS = [
    "oficial",
    "tarjeta",
    "mayorista",
    "bolsa",
    "contadoconliqui",
    "blue",
    "cripto",
]

EMOJIS = {
    "oficial": "🇦🇷",
    "tarjeta": "✈️",
    "mayorista": "🏦",
    "bolsa": "📈",
    "contadoconliqui": "🌐",
    "blue": "💸",
    "cripto": "🪙",
}

def _fmt_ar(valor):
    try:
        if valor is None:
            return "—"
        v = float(valor)
        s = f"{v:,.2f}" if not v.is_integer() else f"{int(v):,}"
        return "$" + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

def _fmt_pct(cambio):
    if cambio is None:
        return ""
    s = f"+{cambio:.2f}%" if cambio >= 0 else f"{cambio:.2f}%"
    return s.replace(".", ",")


def _load_estado_dolar():
    try:
        with open(ESTADO_DOLAR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_estado_dolar(valores_por_casa):
    try:
        hoy = datetime.now().strftime("%d/%m/%Y")
        with open(ESTADO_DOLAR_FILE, "w", encoding="utf-8") as f:
            json.dump({"fecha": hoy, "valores": valores_por_casa}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("No se pudo guardar %s: %s", ESTADO_DOLAR_FILE, e)


def generar_cotizacion_dolar():
    try:
        r = requests.get(URL, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            logger.error("No se pudo consultar la API (%s).", r.status_code)
            raise RuntimeError(f"No se pudo consultar la API ({r.status_code}).")
        data = r.json()
        if not isinstance(data, list) or not data:
            logger.error("Respuesta inesperada de la API (lista vacía).")
            raise RuntimeError("Respuesta inesperada de la API (lista vacía).")

        por_casa = {}
        for it in data:
            if not isinstance(it, dict):
                continue
            casa = (it.get("casa") or "").strip().lower().replace(" ", "")
            nombre = it.get("nombre") or it.get("casa") or ""
            compra = it.get("compra")
            venta  = it.get("venta")
            if not nombre:
                continue
            clave = casa or nombre.strip().lower().replace(" ", "")
            por_casa[clave] = {
                "casa": casa or clave,
                "nombre": nombre.strip(),
                "compra": compra,
                "venta": venta,
            }

        if not por_casa:
            logger.error("La API no devolvió cotizaciones utilizables.")
            raise RuntimeError("La API no devolvió cotizaciones utilizables.")

        # Cargar estado anterior para comparativa día contra día
        estado_anterior = _load_estado_dolar()
        hoy = datetime.now().strftime("%d/%m/%Y")
        usar_comparativa = (
            estado_anterior is not None
            and estado_anterior.get("fecha") != hoy
        )
        valores_previos = estado_anterior.get("valores", {}) if usar_comparativa else {}

        valores_a_guardar = {}

        # Armado del mensaje
        lineas = ["💵 *Cotizaciones del Dólar* 💵", ""]

        def pick(key):
            if key in por_casa:
                return por_casa[key]
            for v in por_casa.values():
                if v["casa"] == key:
                    return v
            for k, v in por_casa.items():
                if k.replace("-", "") == key:
                    return v
            return None

        for key in ORDEN_CASAS:
            item = pick(key)
            if not item:
                continue

            nombre = item["nombre"]
            if nombre.lower().startswith("contado con"):
                nombre = "CCL"

            emoji = EMOJIS.get(key, "💵")
            compra = _fmt_ar(item["compra"])
            venta_fmt = _fmt_ar(item["venta"])

            # Valor numérico de venta para comparar y guardar
            venta_num = None
            try:
                venta_num = float(item["venta"]) if item.get("venta") is not None else None
            except (ValueError, TypeError):
                pass

            if venta_num is not None:
                valores_a_guardar[key] = venta_num

            # Comparativa vs día anterior
            cambio_pct = None
            flecha = ""
            if key in valores_previos:
                prev = valores_previos[key]
                if prev is not None and venta_num is not None and prev != 0:
                    diff = venta_num - prev
                    cambio_pct = (diff / prev) * 100
                    flecha = " 📈" if cambio_pct > 0 else (" 📉" if cambio_pct < 0 else " ➡️")

            venta_line = venta_fmt
            if cambio_pct is not None:
                venta_line += f" ({_fmt_pct(cambio_pct)}{flecha})"

            lineas.append(f"{emoji} *{nombre}*")
            lineas.append(f"Compra: {compra} | Venta: {venta_line}")
            lineas.append("")

        _save_estado_dolar(valores_a_guardar)

        return "\n".join(lineas).strip()

    except requests.Timeout:
        logger.error("Tiempo de espera excedido consultando dolarapi.com.")
        raise
    except requests.RequestException:
        logger.exception("Error de red consultando dolarapi.com")
        raise
    except Exception:
        logger.exception("Error inesperado generando cotizaciones")
        raise

if __name__ == "__main__":
    print("\n" + generar_cotizacion_dolar() + "\n")
