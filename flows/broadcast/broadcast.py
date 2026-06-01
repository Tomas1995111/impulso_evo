"""
Mensajes programados a grupos: horarios, resolvers de contenido y envío vía Evolution API.
"""
import json
import logging
import random
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler

from core import config
from core import evolution_client
from core.links import SUSCRIPCION_PREMIUM_30D
from core.alerts import search_arg_alert, search_us_alert
from mensajes.mensajeCotizacionDolar import generar_cotizacion_dolar
from mensajes.mensajeIndices import generar_mensaje_indices
from mensajes.mensajeResumen import generar_mensaje_resumen

logger = logging.getLogger(__name__)

# ── Lógica de Mensajes Dinámicos (Rotativos persistentes) ───────────────────
def obtener_siguiente_mensaje_dinamico(tipo_mensaje):
    """
    Tipos válidos: 'miercoles', 'viernes', 'motivacionales'
    Lee el estado actual, envía el que corresponde y avanza el índice.
    Si se terminan, vuelve a mezclar automáticamente.
    """
    archivo_contenido = f"contenido/{tipo_mensaje}.json"
    archivo_estado = "estado_mensajes.json"

    # 1. Cargar el contenido base
    with open(archivo_contenido, "r", encoding="utf-8") as f:
        mensajes_base = json.load(f)

    # 2. Cargar o inicializar el estado
    try:
        with open(archivo_estado, "r", encoding="utf-8") as f:
            estado = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        estado = {}

    # 3. Si no existe el estado para este tipo o se terminaron los mensajes, inicializar/mezclar
    if tipo_mensaje not in estado or estado[tipo_mensaje]["proximo_indice"] >= len(
        estado[tipo_mensaje]["lista_mezclada"]
    ):
        indices_mezclados = list(range(len(mensajes_base)))
        random.shuffle(indices_mezclados)

        estado[tipo_mensaje] = {
            "lista_mezclada": indices_mezclados,
            "proximo_indice": 0,
        }
        logger.info("Lista de '%s' mezclada de nuevo de forma aleatoria.", tipo_mensaje)

    # 4. Obtener el mensaje actual usando el índice guardado
    info_tipo = estado[tipo_mensaje]
    lista_ordenada_actual = info_tipo["lista_mezclada"]
    idx_actual_en_base = lista_ordenada_actual[info_tipo["proximo_indice"]]

    mensaje_a_enviar = mensajes_base[idx_actual_en_base]

    # 5. Actualizar el estado para el PRÓXIMO envío
    info_tipo["proximo_indice"] += 1

    with open(archivo_estado, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4, ensure_ascii=False)

    return mensaje_a_enviar


def generar_mensaje_vencimiento():
    hoy = datetime.now()
    manana = hoy + timedelta(days=1)

    str_hoy = hoy.strftime("%d/%m")
    str_manana = manana.strftime("%d/%m")

    return (
        "📢 *Vencimiento de Opciones*\n"
        f"📅 Mañana, viernes {str_manana}, se produce el vencimiento mensual de opciones.\n"
        f"⚠️ Recuerde que pueden negociarse hasta hoy (jueves {str_hoy}) a las 15:30 hs y ejercerse en cualquier momento."
    )


# ── Pool de saludos diarios rotativos ────────────────────────────────────────
SALUDOS_DIARIOS = [
    "📊 *Buenos días, Impulso.*\nEn un minuto te llegan los índices y la noticia del día.",
    "🌅 *Arrancó el día, Impulso.*\nPrepará el café que en un toque tenés el panorama completo.",
    "☀️ *Arrancamos con todo.*\nEn unos minutos compartimos el resumen del día para que no te pierdas nada.",
    "📈 *Vamos por un nuevo día.*\nEn breve compartimos los números y la noticia para arrancar informado.",
]


# ── Resolver de mensajes especiales ──────────────────────────────────────────
MENSAJES_ESPECIALES = {
    "saludo_diario": lambda: random.choice(SALUDOS_DIARIOS),
    "cotizacion_dolar": generar_cotizacion_dolar,
    "resumen_indices": generar_mensaje_indices,
    "noticia_mercado": generar_mensaje_resumen,
    "alerta_bursatil": search_us_alert,
    "alerta_bursatil_arg": search_arg_alert,
    "dinamico_miercoles": lambda: obtener_siguiente_mensaje_dinamico("miercoles"),
    "dinamico_viernes": lambda: obtener_siguiente_mensaje_dinamico("viernes"),
    "dinamico_motivacional": lambda: obtener_siguiente_mensaje_dinamico("motivacionales"),
    "vencimiento_opciones": generar_mensaje_vencimiento,
}


def resolver_mensaje(texto, test_mode: bool = False, test_url: str = None):
    """Resuelve un mensaje especial.

    - Si `test_mode` es True y el mensaje es `noticia_mercado`, se pasa `test_url`
      a `generar_mensaje_resumen`.
    - Para el resto de mensajes se llama la función sin argumentos.
    """
    if texto in MENSAJES_ESPECIALES:
        try:
            if texto == "noticia_mercado" and test_mode:
                use_url = test_url or config.DEFAULT_TEST_PREMARKET_URL
                return MENSAJES_ESPECIALES[texto](test_url=use_url)
            return MENSAJES_ESPECIALES[texto]()
        except Exception as e:
            logger.error("No se pudo generar '%s': %s", texto, e)
            return None
    return texto


# ── Mensajes programados
mensajes_semana = [
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:30", "mensaje": "saludo_diario", "grupo": [config.PREMIUM]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:30", "mensaje": "resumen_indices", "grupo": [config.PREMIUM]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:30", "mensaje": "noticia_mercado", "grupo": [config.PREMIUM]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil", "grupo": [config.REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil", "grupo": [config.REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil_arg", "grupo": [config.REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil_arg", "grupo": [config.REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "15:30", "mensaje": "cotizacion_dolar", "grupo": [config.PREMIUM]},
    {"dias": ["fri"], "hora": "13:30", "mensaje": "💰 *¡No te olvides de caucionar lo líquido este finde semana!*", "grupo": [config.PREMIUM]},
    {"dias": ["tue"], "hora": "15:00", "mensaje": "🔑 *Sumate como inversor asesorado.*\n\nDesignanos como asesores en tu broker (PPI, IOL, Balanz, etc.). No te cuesta nada y nosotros te hacemos el seguimiento de tu cartera.\n\nEscribime al privado y te paso los datos para la designación en 2 minutos.", "grupo": [config.PREMIUM]},
    {"dias": ["thu"], "hora": "16:00", "mensaje": f"🎁 *Invitá a un amigo y ganan los DOS.*\n\nCuando alguien se suscribe con tu link y dice que vos lo invitaste, los dos reciben **30 días gratis**.\n\n👉 {SUSCRIPCION_PREMIUM_30D}", "grupo": [config.PREMIUM]},
    {"dias": ["tue"], "hora": "17:30", "mensaje": "dinamico_motivacional", "grupo": [config.PREMIUM]},
    {"dias": ["wed"], "hora": "17:30", "mensaje": "dinamico_miercoles", "grupo": [config.PREMIUM]},
    {"dias": ["fri"], "hora": "17:30", "mensaje": "dinamico_viernes", "grupo": [config.PREMIUM]},
]

mensajes_fecha = [
    {"fecha": "22/05/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 25/05 ambas bolsas estarán cerradas. La Bolsa de Buenos Aires por el Día de la Revolución de Mayo y la Bolsa de Nueva York por el Día de los Caídos.", "grupo": [config.PREMIUM]},
    {"fecha": "12/06/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 15/06 la Bolsa de Buenos Aires estará cerrada por el feriado en conmemoración del Gral. Güemes.", "grupo": [config.PREMIUM]},
    {"fecha": "18/06/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl viernes 19/06 la Bolsa de Nueva York estará cerrada por el feriado de Juneteenth.", "grupo": [config.PREMIUM]},
    {"fecha": "02/07/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl viernes 03/07 la Bolsa de Nueva York estará cerrada por el Primer Grito de Independencia.", "grupo": [config.PREMIUM]},
    {"fecha": "08/07/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 09/07 y viernes 10/07 la Bolsa de Buenos Aires estará cerrada (Día de la Independencia y Fines Turísticos).", "grupo": [config.PREMIUM]},
    {"fecha": "14/08/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 17/08 la Bolsa de Buenos Aires estará cerrada (Paso a la Inmortalidad del Gral. San Martín).", "grupo": [config.PREMIUM]},
    {"fecha": "04/09/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 07/09 la Bolsa de Nueva York estará cerrada por el Día del Trabajo.", "grupo": [config.PREMIUM]},
    {"fecha": "09/10/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 12/10 la Bolsa de Buenos Aires estará cerrada por el Día del Respeto a la Diversidad Cultural.", "grupo": [config.PREMIUM]},
    {"fecha": "05/11/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl viernes 06/11 la Bolsa de Buenos Aires estará cerrada por el Día del Bancario.", "grupo": [config.PREMIUM]},
    {"fecha": "20/11/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 23/11 la Bolsa de Buenos Aires estará cerrada por el Día de la Soberanía Nacional.", "grupo": [config.PREMIUM]},
    {"fecha": "25/11/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 26/11 la Bolsa de Nueva York estará cerrada (Día de Acción de Gracias). El viernes 27/11 operará con horario reducido, cerrando temprano a las 13:00.", "grupo": [config.PREMIUM]},
    {"fecha": "04/12/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 07/12 y martes 08/12 la Bolsa de Buenos Aires estará cerrada (Fines Turísticos e Inmaculada Concepción de María).", "grupo": [config.PREMIUM]},
    {"fecha": "23/12/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 24/12 la Bolsa de Buenos Aires estará cerrada (Nochebuena) y Nueva York operará con cierre temprano a las 13:00. El viernes 25/12 ambas bolsas estarán cerradas por Navidad.", "grupo": [config.PREMIUM]},
    {"fecha": "30/12/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 31/12 la Bolsa de Buenos Aires estará cerrada.", "grupo": [config.PREMIUM]},
]


def enviar_mensaje(grupo, clave_o_texto, test_mode: bool = False, test_url: str = None):
    texto = resolver_mensaje(clave_o_texto, test_mode=test_mode, test_url=test_url)
    if not texto:
        logger.warning("Mensaje vacío o con error, se omite el envío.")
        return

    evolution_client.send_text_to_destinations(grupo, texto)


def _run_startup_test(test_mode: bool = False):
    if not test_mode:
        return

    logger.info("MODO TEST: Verificando que WhatsApp esté 100% online...")
    evolution_client.wait_whatsapp_open()

    logger.info("MODO TEST: Enviando ráfaga inicial de prueba forzada al DEFAULT...")

    logger.info("Probando mensajes semanales...")
    for msg in mensajes_semana:
        if msg.get("mensaje") == "noticia_mercado":
            enviar_mensaje(
                config.GRUPO_DEFAULT,
                msg["mensaje"],
                test_mode=test_mode,
                test_url=config.DEFAULT_TEST_PREMARKET_URL,
            )
        else:
            enviar_mensaje(config.GRUPO_DEFAULT, msg["mensaje"], test_mode=test_mode)
        time.sleep(2)

    logger.info("Probando mensajes por fecha específica...")
    for msg in mensajes_fecha:
        if msg.get("mensaje") == "noticia_mercado":
            enviar_mensaje(
                config.GRUPO_DEFAULT,
                msg["mensaje"],
                test_mode=test_mode,
                test_url=config.DEFAULT_TEST_PREMARKET_URL,
            )
        else:
            enviar_mensaje(config.GRUPO_DEFAULT, msg["mensaje"], test_mode=test_mode)
        time.sleep(2)

    logger.info("Probando vencimiento de opciones...")
    enviar_mensaje(config.GRUPO_DEFAULT, "vencimiento_opciones", test_mode=test_mode)
    time.sleep(2)

    logger.info("Fin del test inicial.")


def main(test_mode: bool = False):
    _run_startup_test(test_mode)

    scheduler = BlockingScheduler(timezone=config.TIMEZONE)

    for msg in mensajes_semana:
        grupo = msg.get("grupo", config.GRUPO_DEFAULT)
        dias_cron = ",".join(msg["dias"])
        hora, minuto = msg["hora"].split(":")
        scheduler.add_job(
            enviar_mensaje,
            "cron",
            day_of_week=dias_cron,
            hour=int(hora),
            minute=int(minuto),
            misfire_grace_time=300,
            args=[grupo, msg["mensaje"]],
        )

    for msg in mensajes_fecha:
        grupo = msg.get("grupo", config.GRUPO_DEFAULT)
        fecha_dt = datetime.strptime(msg["fecha"], "%d/%m/%Y %H:%M")
        if fecha_dt < datetime.now():
            continue
        scheduler.add_job(
            enviar_mensaje,
            "date",
            run_date=fecha_dt,
            misfire_grace_time=300,
            args=[grupo, msg["mensaje"]],
        )

    scheduler.add_job(
        enviar_mensaje,
        "cron",
        day="14-20",
        day_of_week="thu",
        hour=11,
        minute=0,
        misfire_grace_time=300,
        args=[config.PREMIUM, "vencimiento_opciones"],
    )

    logger.info("Planificador iniciado. Esperando horarios...")
    scheduler.start()


if __name__ == "__main__":
    main()
