import logging
import time
from datetime import datetime

import gspread

from core import config
from core import evolution_client
from core.links import SUSCRIPCION_PREMIUM, SUSCRIPCION_PREMIUM_30D

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger("CRM_Worker")

# Índices de columnas (1-based para gspread)
COL_TELEFONO = 1
COL_NOMBRE = 2
COL_FECHA_CAPTURA = 4
COL_ESTADO = 6
COL_FECHA_BAJA = 7
COL_ULTIMA_ACT = 9


def get_days_diff(date_str: str) -> int:
    """Calcula la diferencia de días entre hoy y la fecha provista."""
    if not date_str:
        return -1
    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %k:%M",
        "%d/%m/%Y %G:%M",
        "%d/%m/%Y",
    ]
    clean_date = date_str.strip()
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_date, fmt)
            diff = datetime.now() - dt
            return diff.days
        except ValueError:
            continue
    logger.error(f"Formato de fecha inválido: '{date_str}'")
    return -1


def get_message(msg_id: int, nombre: str) -> str:
    messages = {
        1: (
            f"¡Hola {nombre}! Ya llevás 3 días con nosotros — ¿qué tal vienes? 📊\n\n"
            "Esto que ves en el grupo es una muestra de lo que armamos todos los días. "
            "Adentro del Premium no solo tenés el resumen, directamente tenés carteras "
            "sugeridas y análisis que te ahorran horas de leer solo.\n\n"
            "Si algo no se entiende o querés profundizar en algún tema, "
            "contestame por acá sin vueltas.\n\n"
            "—Tomás"
        ),
        2: (
            f"¡Hola {nombre}! Esto ya se empieza a poner bueno. ⏳\n\n"
            "Te quedan un par de días de prueba. Pasarte al Premium es "
            "simplemente dejar de recibir información suelta y empezar a tener "
            "un plan concreto para tu plata: carteras de CEDEARs, informes "
            "que te ahorran horas, y soporte directo cuando tengas dudas.\n\n"
            f"{SUSCRIPCION_PREMIUM}\n\n"
            "Cualquier duda, respondeme. —Tomás"
        ),
        3: (
            f"{nombre}, mañana se termina tu prueba ⚠️\n\n"
            "Si te gustó tener el mercado resumido todos los días sin tener "
            "que perseguir las noticias, esto es solo el aperitivo. Adentro "
            "del Premium ves dónde poner la plata, no solo lo que pasó.\n\n"
            f"{SUSCRIPCION_PREMIUM}\n\n"
            "Mañana temprano mando el resumen diario, no te lo pierdas.\n"
            "—Tomás"
        ),
        4: (
            f"Hola {nombre}, se terminó la semana de prueba. 🙌\n\n"
            "Ojalá te haya servido para ver el mercado más claro. "
            "La puerta del Premium sigue abierta cuando quieras:\n\n"
            f"{SUSCRIPCION_PREMIUM}\n\n"
            "Apenas te suscribís, mandame el comprobante y te agrego al toque. "
            "Sin vueltas.\n\n"
            "—Tomás"
        ),
        5: (
            f"{nombre}, te tengo una oferta exprés: "
            f"**30% OFF en tu primer mes** del Grupo Premium. 🎁\n\n"
            "Por menos de lo que gastás en un café por día te sumás y ves "
            "todo lo que hacemos adentro: carteras sugeridas, alertas, "
            "análisis, y soporte directo cuando lo necesites.\n\n"
            f"{SUSCRIPCION_PREMIUM_30D}\n\n"
            "Si te interesa, no le des muchas vueltas.\n"
            "—Tomás"
        ),
        6: (
            f"¡Hola {nombre}! El mercado no para y cada semana ajustamos "
            f"carteras y estrategias en el Premium. 📈\n\n"
            "La gente adentro ya no tiene que estar pendiente de 20 fuentes "
            "distintas. Le llega todo filtrado, con sugerencia de qué hacer.\n\n"
            "Si te interesa invertir con menos ruido y más claridad:\n\n"
            f"{SUSCRIPCION_PREMIUM}\n\n"
            "Cuando quieras, estoy acá.\n"
            "—Tomás"
        ),
        7: (
            f"Hola {nombre}, te llegó un beneficio exclusivo por haber sido "
            f"parte del Premium: **tu precio anterior congelado por 3 meses** "
            f"si volvés ahora. 🚀\n\n"
            "No sé si viste, pero venimos sumando carteras nuevas y el grupo "
            "está cada vez más activo. Si en su momento te servía, "
            "hoy está mejor.\n\n"
            f"{SUSCRIPCION_PREMIUM}\n\n"
            "Apenas te suscribís, avisame y te pongo al día con todo.\n"
            "—Tomás"
        ),
    }
    return messages.get(msg_id, "")


def _get_worksheet():
    gc = gspread.service_account(filename=config.CREDENTIALS_FILE)
    sh = gc.open_by_key(config.LEADS_SHEET_ID)
    return sh.worksheet(config.LEADS_SHEET_TAB)


def process_crm():
    logger.info("Iniciando CRM Worker...")

    try:
        worksheet = _get_worksheet()
        records = worksheet.get_all_values()
    except Exception as e:
        logger.error(f"Error conectando a Google Sheets: {e}")
        return

    if not records or len(records) <= 1:
        logger.info("No hay registros para procesar.")
        return

    hoy_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    batch_updates = []

    for idx, row in enumerate(records[1:], start=2):
        row = row + [""] * (10 - len(row))

        telefono = row[COL_TELEFONO - 1].strip()
        nombre = row[COL_NOMBRE - 1].strip()
        fecha_captura = row[COL_FECHA_CAPTURA - 1].strip()
        estado = row[COL_ESTADO - 1].strip()
        fecha_baja = row[COL_FECHA_BAJA - 1].strip()
        logger.info(f"Procesando {nombre}: Estado='{estado}', DiasBaja={get_days_diff(fecha_baja)}")
        if not telefono or not estado:
            continue

        if estado in ["Premium", "Retargeting Final", "Baja Final", "Eliminado Definitivo"]:
            continue

        dias_captura = get_days_diff(fecha_captura)
        dias_baja = get_days_diff(fecha_baja)

        nuevo_estado = None
        mensaje_id = None
        remover_grupo = False

        # --- BLOQUE TRIAL ---
        if estado in ["Trial 0", "Trial0"] and dias_captura >= 3:
            mensaje_id = 1
            nuevo_estado = "Trial3"
        elif estado in ["Trial 3", "Trial3"] and dias_captura >= 5:
            mensaje_id = 2
            nuevo_estado = "Trial5"
        elif estado in ["Trial 5", "Trial5"] and dias_captura >= 6:
            mensaje_id = 3
            nuevo_estado = "Trial6"
        elif estado in ["Trial 6", "Trial6"] and dias_captura >= 7:
            remover_grupo = True
            mensaje_id = 4
            nuevo_estado = "Eliminado"

        # --- BLOQUE RETARGETING ---
        elif estado == "Eliminado" and dias_captura >= 22:
            mensaje_id = 5
            nuevo_estado = "Retargeting 15"
        elif estado == "Retargeting 15" and dias_captura >= 47:
            mensaje_id = 6
            nuevo_estado = "Retargeting Final"

        # --- BLOQUE BAJA PREMIUM ---
        elif estado == "Baja" and dias_baja >= 60:
            mensaje_id = 7
            nuevo_estado = "Baja Final"

        # --- EJECUCIÓN DE ACCIONES ---
        if nuevo_estado:
            logger.info(f"Procesando a {nombre} ({telefono}) - Transición: {estado} -> {nuevo_estado}")

            exito = True

            if remover_grupo:
                logger.info(f"Removiendo a {telefono} del grupo free...")
                exito = evolution_client.remove_participant_from_group(config.FREE, telefono)
                time.sleep(2)

            if mensaje_id and exito:
                texto = get_message(mensaje_id, nombre)
                remote_jid = telefono if "@" in telefono else f"{telefono}@s.whatsapp.net"
                evolution_client.send_text(remote_jid, texto)
                exito = True

            if exito:
                batch_updates.append((idx, COL_ESTADO, nuevo_estado))
                batch_updates.append((idx, COL_ULTIMA_ACT, hoy_str))
                logger.info(f"✅ Sheet registrado para batch update: {nombre}")
            else:
                logger.warning(f"⚠️ Se omitió actualización de Sheet para {nombre} por error en API.")

            time.sleep(4)

    if batch_updates:
        try:
            from gspread import Cell
            cells_to_update = [Cell(row=r, col=c, value=v) for r, c, v in batch_updates]
            worksheet.update_cells(cells_to_update)
            logger.info(f"✅ Batch update completado: {len(cells_to_update)} celdas actualizadas.")
        except Exception as e:
            logger.error(f"❌ Error en batch update de Google Sheets: {e}")

    logger.info("CRM Worker finalizó su ejecución.")


if __name__ == "__main__":
    process_crm()
