import logging
import time
from datetime import datetime

import gspread

from core import config
from core import evolution_client

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
        1: f"¡Hola, {nombre}! Ya van 3 días de tu prueba gratis. 📈 ¿Cómo venís con la info del grupo? Ojalá te esté sirviendo para bajar a tierra el mercado. Acordate que este grupo es solo un adelanto general (el armado de carteras y los análisis a fondo los hacemos en el Premium). Si tenés alguna duda de lo que mandamos estos días, ¡escribime por acá! Un abrazo.",
        2: f"¡Hola, {nombre}! Tu prueba gratis está entrando en la recta final. ⏳ Si querés asegurar tu lugar para no perderte nada y pasar al Grupo Premium, podés activar tu membresía acá: 👉 [Link de Mercado Pago] Ahí adentro sumamos carteras sugeridas de CEDEARs/acciones, informes completos y mi acompañamiento en este privado para tus dudas al invertir. ¡Te espero!",
        3: f"¡Últimas 24 horas de prueba, {nombre}! ⚠️ Mañana el bot te va a remover automáticamente del grupo Free. Si te sirvió este vistazo para entender el mercado, mantené la constancia y sumate de forma definitiva al Premium acá: 👉 [Link de Mercado Pago] ¡Te espero del lado de adentro! 🚀",
        4: f"{nombre}, terminó tu prueba y el sistema te removió del grupo. ⏱️ Si querés seguir bien informado y subir de nivel al Grupo Premium (para ver carteras recomendadas, análisis y soporte privado), suscribite acá: 👉 [Link de Mercado Pago] Apenas pagues, mandame el comprobante por acá así te sumo de inmediato al Premium. ¡Gracias por compartir esta semana! 👍",
        5: f"¡Hola {nombre}! Se cumplen dos semanas desde que terminó tu prueba en Impulso Merval. 📈 Como sé que el mercado argentino no da respiro y estos días pasaron cosas clave (tasas, inflación, etc.), quiero darte un empujón para que vuelvas bien informado. Te armé un cupón especial del 30% de descuento para tu primer mes en el Grupo Premium. Activalo acá: 👉 [Link de Mercado Pago con Promo] ¡Te espero adentro para acomodar tus inversiones de este mes! 🚀",
        6: f"¡Hola {nombre}! Te escribo rápido porque el mercado y la economía acá nunca dan respiro. ⚠️ En el Grupo Premium actualizamos las estrategias todas las semanas para defender los ahorros de la comunidad y aprovechar las oportunidades en CEDEARs antes de que sea tarde. Si querés dejar de adivinar qué hacer con tu plata y ver nuestras carteras sugeridas, sumate de forma definitiva acá: 👉 [Link de Mercado Pago] ¡Buenas inversiones! 👍",
        7: f"¡Hola {nombre}! Hace un par de meses que dejaste el Grupo Premium de Impulso Merval y se te extraña en la comunidad. 📈 Te escribía porque seguimos sumando carteras sugeridas, nuevos análisis y puliendo el formato para darte la información cada vez más directa y filtrada. Como ya fuiste parte de la comunidad, si querés volver te mantengo el precio anterior congelado por 3 meses como beneficio exclusivo. Podés reactivar tu acceso definitivo acá: 👉 [Link de Mercado Pago] ¡Un abrazo y buenas inversiones! 🚀"
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
            cells_to_update = []
            for row_idx, col_idx, val in batch_updates:
                cell = worksheet.cell(row_idx, col_idx)
                cell.value = val
                cells_to_update.append(cell)
            worksheet.update_cells(cells_to_update)
            logger.info(f"✅ Batch update completado: {len(cells_to_update)} celdas actualizadas.")
        except Exception as e:
            logger.error(f"❌ Error en batch update de Google Sheets: {e}")

    logger.info("CRM Worker finalizó su ejecución.")


if __name__ == "__main__":
    process_crm()
