# mensajes/mensajeCotizacionesDolar.py
import requests

URL = "https://dolarapi.com/v1/dolares"
HEADERS = {"User-Agent": "Mozilla/5.0"}

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

def generar_cotizacion_dolar():
    try:
        r = requests.get(URL, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return f"[!] No se pudo consultar la API ({r.status_code})."
        data = r.json()
        if not isinstance(data, list) or not data:
            return "[!] Respuesta inesperada de la API (lista vacía)."

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
            return "[!] La API no devolvió cotizaciones utilizables."

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
            venta  = _fmt_ar(item["venta"])

            lineas.append(f"{emoji} *{nombre}*")
            lineas.append(f"Compra: {compra} | Venta: {venta}")
            lineas.append("")

        return "\n".join(lineas).strip()

    except requests.Timeout:
        return "[!] Tiempo de espera excedido consultando dolarapi.com."
    except requests.RequestException as e:
        return f"[!] Error de red consultando dolarapi.com: {e}"
    except Exception as e:
        return f"[!] Error inesperado generando cotizaciones: {e}"

if __name__ == "__main__":
    print("\n" + generar_cotizacion_dolar() + "\n")
