import time
import requests
import os
import json
import random
from datetime import datetime, timedelta
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
    if tipo_mensaje not in estado or estado[tipo_mensaje]["proximo_indice"] >= len(estado[tipo_mensaje]["lista_mezclada"]):
        indices_mezclados = list(range(len(mensajes_base)))
        random.shuffle(indices_mezclados)
        
        estado[tipo_mensaje] = {
            "lista_mezclada": indices_mezclados,
            "proximo_indice": 0
        }
        print(f"[INFO] Lista de '{tipo_mensaje}' mezclada de nuevo de forma aleatoria.")

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
    
    str_hoy = hoy.strftime('%d/%m')
    str_manana = manana.strftime('%d/%m')
    
    return (
        "📢 *Vencimiento de Opciones*\n"
        f"📅 Mañana, viernes {str_manana}, se produce el vencimiento mensual de opciones.\n"
        f"⚠️ Recuerde que pueden negociarse hasta hoy (jueves {str_hoy}) a las 15:30 hs y ejercerse en cualquier momento."
    )


# ── Resolver de mensajes especiales ──────────────────────────────────────────
MENSAJES_ESPECIALES = {
    "cotizacion_dolar": generar_cotizacion_dolar,
    "resumen_indices": generar_mensaje_indices,
    "noticia_mercado": generar_mensaje_resumen,
    "alerta_bursatil": generar_alerta_aleatoria,
    "alerta_bursatil_arg": generar_alerta_aleatoria_arg,
    # "reporte_google_sheet":generar_reporte_google_sheet,
    "dinamico_miercoles": lambda: obtener_siguiente_mensaje_dinamico("miercoles"),
    "dinamico_viernes": lambda: obtener_siguiente_mensaje_dinamico("viernes"),
    "dinamico_motivacional": lambda: obtener_siguiente_mensaje_dinamico("motivacionales"),
    "vencimiento_opciones": generar_mensaje_vencimiento,
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
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:00", "mensaje": "💪 *Muy buenos días, Impulsores.*\nHoy es una nueva oportunidad para seguir creciendo juntos.", "grupo": [PREMIUM]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:00", "mensaje": "resumen_indices", "grupo": [PREMIUM]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "09:00", "mensaje": "noticia_mercado", "grupo": [PREMIUM]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil", "grupo": [REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil", "grupo": [REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil_arg", "grupo": [REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "11:00", "mensaje": "alerta_bursatil_arg", "grupo": [REVISION]},
    {"dias": ["mon", "tue", "wed", "thu", "fri"], "hora": "15:30", "mensaje": "cotizacion_dolar", "grupo": [PREMIUM]},
    {"dias": ["tue"], "hora": "15:30", "mensaje": "dinamico_motivacional", "grupo": [PREMIUM]},
    {"dias": ["wed"], "hora": "15:30", "mensaje": "dinamico_miercoles", "grupo": [PREMIUM]},
    {"dias": ["fri"], "hora": "15:30", "mensaje": "dinamico_viernes", "grupo": [PREMIUM]},
    {"dias": ["fri"], "hora": "13:30", "mensaje": "💰 *¡No te olvides de caucionar lo líquido este finde semana!*", "grupo": [PREMIUM]},
    {"dias": ["tue"], "hora": "16:00", "mensaje": "🎁 *¡Invitá a un amigo y ganan los dos!*\n\nSi alguien se suscribe con este link 👇\nhttps://www.mercadopago.com.ar/subscriptions/checkout?preapproval_plan_id=2c9380847596cf970175ae9482893205\n*y nos dice que vos lo invitaste*, te bonificamos *tu próximo pago* 💸\n\n👥 *¿Cómo funciona?*\n1️⃣ Compartí el link con quien creas que le puede servir\n2️⃣ Cuando se sume, que nos escriba: *\"Me invitó Juan\"*\n3️⃣ ¡Ambos reciben *30 días gratis*!\n\n📩 *Ante cualquier duda, escribime por privado.*", "grupo": [PREMIUM]},
]

mensajes_fecha = [
    {"fecha": "22/05/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 25/05 ambas bolsas estarán cerradas. La Bolsa de Buenos Aires por el Día de la Revolución de Mayo y la Bolsa de Nueva York por el Día de los Caídos.", "grupo": [PREMIUM]},
    {"fecha": "12/06/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 15/06 la Bolsa de Buenos Aires estará cerrada por el feriado en conmemoración del Gral. Güemes.", "grupo": [PREMIUM]},
    {"fecha": "18/06/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl viernes 19/06 la Bolsa de Nueva York estará cerrada por el feriado de Juneteenth.", "grupo": [PREMIUM]},
    {"fecha": "02/07/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl viernes 03/07 la Bolsa de Nueva York estará cerrada por el Primer Grito de Independencia.", "grupo": [PREMIUM]},
    {"fecha": "08/07/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 09/07 y viernes 10/07 la Bolsa de Buenos Aires estará cerrada (Día de la Independencia y Fines Turísticos).", "grupo": [PREMIUM]},
    {"fecha": "14/08/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 17/08 la Bolsa de Buenos Aires estará cerrada (Paso a la Inmortalidad del Gral. San Martín).", "grupo": [PREMIUM]},
    {"fecha": "04/09/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 07/09 la Bolsa de Nueva York estará cerrada por el Día del Trabajo.", "grupo": [PREMIUM]},
    {"fecha": "09/10/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 12/10 la Bolsa de Buenos Aires estará cerrada por el Día del Respeto a la Diversidad Cultural.", "grupo": [PREMIUM]},
    {"fecha": "05/11/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl viernes 06/11 la Bolsa de Buenos Aires estará cerrada por el Día del Bancario.", "grupo": [PREMIUM]},
    {"fecha": "20/11/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 23/11 la Bolsa de Buenos Aires estará cerrada por el Día de la Soberanía Nacional.", "grupo": [PREMIUM]},
    {"fecha": "25/11/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 26/11 la Bolsa de Nueva York estará cerrada (Día de Acción de Gracias). El viernes 27/11 operará con horario reducido, cerrando temprano a las 13:00.", "grupo": [PREMIUM]},
    {"fecha": "04/12/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl lunes 07/12 y martes 08/12 la Bolsa de Buenos Aires estará cerrada (Fines Turísticos e Inmaculada Concepción de María).", "grupo": [PREMIUM]},
    {"fecha": "23/12/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 24/12 la Bolsa de Buenos Aires estará cerrada (Nochebuena) y Nueva York operará con cierre temprano a las 13:00. El viernes 25/12 ambas bolsas estarán cerradas por Navidad.", "grupo": [PREMIUM]},
    {"fecha": "30/12/2026 12:20", "mensaje": "📢 *Aviso Feriado:*\nEl jueves 31/12 la Bolsa de Buenos Aires estará cerrada.", "grupo": [PREMIUM]}
]

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
    
    # 3. Test de vencimiento de opciones
    print("📢 Probando vencimiento de opciones...")
    enviar_mensaje(GRUPO_DEFAULT, "vencimiento_opciones", test_mode=EJECUTAR_TEST_AL_INICIO)
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

# Regla del vencimiento de opciones
scheduler.add_job(
    enviar_mensaje,
    "cron",
    day="14-20",         
    day_of_week="thu",   
    hour=11,              
    minute=0,            
    args=[PREMIUM, "vencimiento_opciones"] 
)

print("⏰ Planificador iniciado. Esperando horarios...")
scheduler.start()