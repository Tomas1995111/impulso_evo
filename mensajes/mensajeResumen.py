# mensajeResumen.py
import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

# =========================
# Funciones auxiliares
# =========================

def buscar_url_en_sitemap():
    """
    Descarga el sitemap de noticias de CNBC y busca la URL de premarket
    que coincida con la fecha indicada.
    """
    # ── CONFIGURACIÓN DE FECHA ───────────────────────────────────────────────
    
    # MAÑANA LUNES: Descomentá esta línea de abajo para que sea automático:
    fecha_filtro = time.strftime("%Y/%m/%d")
    # ─────────────────────────────────────────────────────────────────────────

    url_sitemap = "https://www.cnbc.com/sitemap_news.xml"
    print(f"🔍 [Sitemap] Consultando el mapa de sitio oficial de CNBC...", flush=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url_sitemap, headers=headers, timeout=12)
        if res.status_code != 200:
            print(f"❌ [Sitemap] Error de servidor al acceder al XML: {res.status_code}", flush=True)
            return None
            
        print(f"📄 [Sitemap] XML descargado ({len(res.text)} caracteres). Buscando patrones para la fecha {fecha_filtro}...", flush=True)
        
        # El patrón busca la estructura exacta de la URL usando la fecha elegida
        patron = rf"https://www.cnbc.com/{fecha_filtro}/stocks-making-the-biggest-moves-premarket-[\w-]+.html"
        urls_encontradas = re.findall(patron, res.text)
        
        if urls_encontradas:
            url_final = urls_encontradas[0]
            print(f"🎯 [Sitemap] ¡URL localizada con éxito!: {url_final}", flush=True)
            return url_final
            
        print(f"⚠️ [Sitemap] No se encontró ninguna nota de premarket para la fecha: {fecha_filtro}", flush=True)
        return None
        
    except Exception as e:
        print(f"❌ [Sitemap] Error de red consultando el archivo XML: {e}", flush=True)
        return None

def esperar_y_buscar_url(max_espera_min=70, intervalo_min=5):
    inicio = time.time()
    intento = 0
    print(f"⏱️ [Planificador] Iniciando rutina de espera del sitemap. Límite: {max_espera_min} minutos.", flush=True)
    
    while (time.time() - inicio) < max_espera_min * 60:
        intento += 1
        print(f"\n🔄 [Planificador] Intento #{intento}...", flush=True)
        url = buscar_url_en_sitemap()
        
        if url:
            return url
            
        print(f"😴 [Planificador] Nota ausente en el XML. Durmiendo por {intervalo_min} minutos antes del reintento...", flush=True)
        time.sleep(intervalo_min * 60)
        
    print("🚨 [Planificador] Se agotó el tiempo de espera en el sitemap sin novedades.", flush=True)
    return None

def extraer_html_crudo(url):
    """Descarga el contenido HTML completo de la nota usando requests."""
    print(f"🚀 [Requests] Descargando HTML de la noticia...", flush=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            print(f"✅ [Requests] HTML descargado correctamente. Tamaño: {len(res.text)} caracteres.", flush=True)
            return res.text
        print(f"❌ [Requests] Error de servidor al bajar la nota. Estado: {res.status_code}", flush=True)
        return None
    except Exception as e:
        logger.error(f"Error de red al descargar el artículo: {e}")
        return None

def _get_gemini_client():
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY no está configurada.", flush=True)
        return None
    return genai.Client(api_key=api_key)


def procesar_con_gemini(html_crudo):
    """Le pasa el HTML crudo a Gemini para que limpie el código basura y devuelva el resumen formateado."""
    if not html_crudo:
        print("⚠️ [Gemini] Cancelado: El HTML de entrada está vacío.", flush=True)
        return None

    client = _get_gemini_client()
    if not client:
        return None

    print(f"🧠 [Gemini] Enviando HTML crudo a Gemini 2.5 Flash...", flush=True)
    prompt = (
        "Te voy a pasar el código HTML completo y crudo de un artículo de CNBC. "
        "Tu tarea como analista financiero experto es ignorar todo el código de programación, "
        "etiquetas HTML, menús de navegación y anuncios publicitarios.\n\n"
        "Buscá únicamente la sección principal del artículo donde se detallan los movimientos de las "
        "acciones antes de la apertura del mercado (Pmarket).\n\n"
        "Traducí esa información al español de forma clara, fluida y profesional, y armá el "
        "mensaje respetando estrictamente este formato Markdown para cada acción:\n\n"
        "🔹 [Nombre de la Empresa]:\n[Breve resumen de por qué sube o baja con su impacto porcentual]\n\n"
        "Comenzá el mensaje directamente con el título: 📊 *Mayores movimientos de acciones* 📊\n\n"
        "No agregues introducciones ni textos extra al inicio ni al final."
    )
    
    try:
        print("📡 [Gemini] Ejecutando llamada a la API de Google GenAI...", flush=True)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, html_crudo]
        )
        print("✨ [Gemini] Procesamiento de IA completado exitosamente.", flush=True)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error crítico invocando la API: {e}")
        return None

# =========================
# Función principal (La que llama tu bot)
# =========================
def generar_mensaje_resumen(test_url: str = None):
    """Genera el resumen de mercado.

    Si se provee `test_url`, se usará esa URL directamente (modo test). Si no, se
    intentará localizar la nota en el sitemap de CNBC como antes.
    """
    print("\n🏁 [Inicio] Ejecutando generar_mensaje_resumen()...", flush=True)
    try:
        # Si estamos en modo test y recibimos una URL de prueba, la usamos
        if test_url:
            url = test_url
            print(f"🧪 [Test] Usando URL de prueba: {url}", flush=True)
        else:
            # Busca el link directo en el mapa de sitio
            url = esperar_y_buscar_url()
            if not url:
                logger.warning("No se envió nada porque no se encontró la nota en el sitemap de CNBC.")
                return None

        # 1. Bajamos el código de la página directo
        html_crudo = extraer_html_crudo(url)
        
        # 2. La IA extrae los datos, los traduce y les da formato desde el HTML
        mensaje_final = procesar_con_gemini(html_crudo)

        if not mensaje_final:
            print("🛑 [Fin] La IA no logró retornar un bloque de texto válido.", flush=True)
            return "[!] No se pudo generar el resumen con la IA."

        print("🎉 [Fin] Resumen de mercado generado con éxito.", flush=True)
        return mensaje_final

    except Exception as e:
        msg = f"[!] Error inesperado generando mensajeResumen: {e}"
        logger.error(msg)
        return msg