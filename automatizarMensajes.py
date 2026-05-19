import time
import requests
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from mensajes.mensajeIndices import generar_mensaje_indices
from mensajes.mensajeAlertaCompra import generar_alerta_aleatoria
from mensajes.mensajeAlertaCompraArg import generar_alerta_aleatoria_arg
from mensajes.mensajeCotizacionDolar import generar_cotizacion_dolar
from mensajes.mensajeResumen import generar_mensaje_resumen

# ── CONFIGURACIÓN MODO TEST ─────────────────────────────────────────────────
# Ponelo en True para enviar todo al iniciar. En False solo espera sus horarios.
EJECUTAR_TEST_AL_INICIO = False  

# ── Configuración API ────────────────────────────────────────────────────────
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution_api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "Impulso")
URL_API = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
HEADERS = {"apikey": EVOLUTION_API_KEY}

GRUPO_DEFAULT = os.getenv("GRUPO_DEFAULT")
BACKUP = os.getenv("GRUPO_BACKUP")
REVISION = os.getenv("GRUPO_REVISION")
PREMIUM = os.getenv("GRUPO_PREMIUM")
FREE = os.getenv("GRUPO_FREE")

# ── Resolver de mensajes especiales ──────────────────────────────────────────
MENSAJES_ESPECIALES = {
    "cotizacion_dolar": generar_cotizacion_dolar,
    "resumen_indices": generar_mensaje_indices,
    "noticia_mercado": generar_mensaje_resumen,
    "alerta_bursatil": generar_alerta_aleatoria,
    "alerta_bursatil_arg": generar_alerta_aleatoria_arg,
    # "reporte_google_sheet":generar_reporte_google_sheet,
}

# URL de prueba para el modo test (se puede sobreescribir con TEST_PREMARKET_URL en .env)
DEFAULT_TEST_PREMARKET_URL = os.getenv(
    "TEST_PREMARKET_URL",
    "https://www.cnbc.com/2026/05/15/stocks-making-the-biggest-moves-premarket-amat-intc-micc.html",
)

def resolver_mensaje(texto, test_mode: bool = False, test_url: str = None):
    """Resuelve un mensaje especial.

    - Si `test_mode` es True y el mensaje es `noticia_mercado`, se pasa `test_url`
      a `generar_mensaje_resumen`.
    - Para el resto de mensajes se llama la función sin argumentos.
    """
    if texto in MENSAJES_ESPECIALES:
        try:
            if texto == "noticia_mercado" and test_mode:
                use_url = test_url or DEFAULT_TEST_PREMARKET_URL
                return MENSAJES_ESPECIALES[texto](test_url=use_url)
            return MENSAJES_ESPECIALES[texto]()
        except Exception as e:
            print(f"[ERROR] No se pudo generar '{texto}': {e}")
            return None
    return texto


# ── Mensajes programados
mensajes_semana = [
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "08:55", "mensaje": "💪 *Muy buenos días, Impulsores.*\nHoy es una nueva oportunidad para seguir creciendo juntos.", "grupo": [BACKUP]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:03", "mensaje": "resumen_indices", "grupo": [BACKUP]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:11", "mensaje": "noticia_mercado", "grupo": [BACKUP]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil", "grupo": [BACKUP]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:05", "mensaje": "alerta_bursatil", "grupo": [BACKUP]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:10", "mensaje": "alerta_bursatil_arg", "grupo": [BACKUP]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:15", "mensaje": "alerta_bursatil_arg", "grupo": [BACKUP]},
    {"dias": ["mon"], "hora": "13:30", "mensaje": "💰 *¡No te olvides de caucionar lo líquido este finde semana!*", "grupo": [BACKUP]},
    {"dias": ["mon"], "hora": "16:00", "mensaje": "🎁 *¡Invitá a un amigo y ganan los dos!*\n\nSi alguien se suscribe con este link 👇\nhttps://www.mercadopago.com.ar/subscriptions/checkout?preapproval_plan_id=2c9380847596cf970175ae9482893205\n*y nos dice que vos lo invitaste*, te bonificamos *tu próximo pago* 💸\n\n👥 *¿Cómo funciona?*\n1️⃣ Compartí el link con quien creas que le puede servir\n2️⃣ Cuando se sume, que nos escriba: *\"Me invitó Juan\"*\n3️⃣ ¡Ambos reciben *30 días gratis*!\n\n📩 *Ante cualquier duda, escribime por privado.*", "grupo": [BACKUP]},
    {"dias": ["mon"], "hora": "00:11", "mensaje": "cotizacion_dolar", "grupo": [BACKUP]},
]

mensajes_fecha = [
    {"fecha": "18/05/2026 12:00", "mensaje": "📢 *Aviso Feriado:* La Bolsa estará cerrada.", "grupo": [BACKUP]}
]

# mensajes_semana = [
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "08:55", "mensaje": "💪 *Muy buenos días, Impulsores.*\nHoy es una nueva oportunidad para seguir creciendo juntos.", "grupo": [PREMIUM, FREE, BACKUP]},
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:03", "mensaje": "resumen_indices", "grupo": [PREMIUM, FREE, BACKUP]},
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:11", "mensaje": "noticia_mercado", "grupo": [PREMIUM, FREE, BACKUP]},
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil", "grupo": [REVISION, BACKUP]},
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:05", "mensaje": "alerta_bursatil", "grupo": [REVISION, BACKUP]},
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:10", "mensaje": "alerta_bursatil_arg", "grupo": [REVISION, BACKUP]},
#     {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:15", "mensaje": "alerta_bursatil_arg", "grupo": [REVISION, BACKUP]},
#     {"dias": ["fri"], "hora": "13:30", "mensaje": "💰 *¡No te olvides de caucionar lo líquido este finde semana!*", "grupo": [PREMIUM, FREE, BACKUP]},
#     {"dias": ["tue"], "hora": "19:00", "mensaje": "🎁 *¡Invitá a un amigo y ganan los dos!*\n\nSi alguien se suscribe con este link 👇\nhttps://www.mercadopago.com.ar/subscriptions/checkout?preapproval_plan_id=2c9380847596cf970175ae9482893205\n*y nos dice que vos lo invitaste*, te bonificamos *tu próximo pago* 💸\n\n👥 *¿Cómo funciona?*\n1️⃣ Compartí el link con quien creas que le puede servir\n2️⃣ Cuando se sume, que nos escriba: *\"Me invitó Juan\"*\n3️⃣ ¡Ambos reciben *30 días gratis*!\n\n📩 *Ante cualquier duda, escribime por privado.*", "grupo": [PREMIUM, FREE, BACKUP]},
#     {"dias": ["fri"], "hora": "00:11", "mensaje": "cotizacion_dolar", "grupo": [PREMIUM, FREE, BACKUP]},
# ]

# mensajes_fecha = [
#     {"fecha": "27/05/2026 12:00", "mensaje": "📢 *Aviso Feriado:* La Bolsa estará cerrada.", "grupo": [PREMIUM, FREE, BACKUP]}
# ]

# ── Envío ────────────────────────────────────────────────────────────────────
def enviar_mensaje(grupo, clave_o_texto, test_mode: bool = False, test_url: str = None):
    texto = resolver_mensaje(clave_o_texto, test_mode=test_mode, test_url=test_url)
    if not texto:
        print(f"[{datetime.now()}] Mensaje vacío o con error, se omite el envío.")
        return

    destinatarios = [grupo] if isinstance(grupo, str) else grupo

    for dest in destinatarios:
        numero = dest if "@" in dest else f"{dest}@g.us"
        payload = {"number": numero, "text": texto}
        try:
            res = requests.post(URL_API, json=payload, headers=HEADERS)
            print(f"[{datetime.now()}] Enviado a {numero}. Estado: {res.status_code}")
        except Exception as e:
            print(f"[ERROR] No se pudo enviar a {numero}: {e}")

# ── Ejecución de Test Inicial ───────────────────────────────────────────────
if EJECUTAR_TEST_AL_INICIO:
    print("⏳ MODO TEST: Verificando que WhatsApp esté 100% online...")
    url_estado = f"{EVOLUTION_API_URL}/instance/connectionState/{EVOLUTION_INSTANCE_NAME}"
    
    while True:
        try:
            res = requests.get(url_estado, headers=HEADERS, timeout=5)
            estado = res.json().get("instance", {}).get("state", "").lower()
            if estado == "open":
                print("✅ ¡WhatsApp conectado y listo para enviar!")
                break
            print(f"⏳ WhatsApp está en estado '{estado}'. Esperando 5 segundos...")
        except Exception:
            print("⏳ Evolution API está cargando... Esperando 5 segundos...")
        time.sleep(5)
    
    print("🚀 MODO TEST: Enviando ráfaga inicial de prueba forzada al DEFAULT...")
    
    # 1. Test de mensajes semanales
    print("📅 Probando mensajes semanales...")
    for msg in mensajes_semana:
        if msg.get("mensaje") == "noticia_mercado":
            enviar_mensaje(
                GRUPO_DEFAULT,
                msg["mensaje"],
                test_mode=EJECUTAR_TEST_AL_INICIO,
                test_url=DEFAULT_TEST_PREMARKET_URL,
            )
        else:
            enviar_mensaje(GRUPO_DEFAULT, msg["mensaje"], test_mode=EJECUTAR_TEST_AL_INICIO)
        time.sleep(2)
        
    # 2. Test de mensajes por fecha
    print("📌 Probando mensajes por fecha específica...")
    for msg in mensajes_fecha:
        if msg.get("mensaje") == "noticia_mercado":
            enviar_mensaje(
                GRUPO_DEFAULT,
                msg["mensaje"],
                test_mode=EJECUTAR_TEST_AL_INICIO,
                test_url=DEFAULT_TEST_PREMARKET_URL,
            )
        else:
            enviar_mensaje(GRUPO_DEFAULT, msg["mensaje"], test_mode=EJECUTAR_TEST_AL_INICIO)
        time.sleep(2)
        
    print("✅ Fin del test inicial.")

# ── Scheduler ────────────────────────────────────────────────────────────────
scheduler = BlockingScheduler(timezone="America/Argentina/Buenos_Aires")

for msg in mensajes_semana:
    grupo = msg.get("grupo", GRUPO_DEFAULT)
    dias_cron = ",".join(msg["dias"])  # Usa los días cortos directamente
    hora, minuto = msg["hora"].split(":")
    scheduler.add_job(
        enviar_mensaje,
        "cron",
        day_of_week=dias_cron,
        hour=int(hora),
        minute=int(minuto),
        args=[grupo, msg["mensaje"]]
    )

for msg in mensajes_fecha:
    grupo = msg.get("grupo", GRUPO_DEFAULT)
    fecha_dt = datetime.strptime(msg["fecha"], "%d/%m/%Y %H:%M")
    if fecha_dt > datetime.now():
        scheduler.add_job(
            enviar_mensaje,
            "date",
            run_date=fecha_dt,
            args=[grupo, msg["mensaje"]]
        )

print("⏰ Planificador iniciado. Esperando horarios...")
scheduler.start()