import re

def buscar_url_resumen():
    url_sitemap = "https://www.cnbc.com/sitemap_news.xml"
    print("🔍 [Sitemap] Consultando el mapa de sitio oficial de CNBC...", flush=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url_sitemap, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"❌ [Sitemap] Error al acceder: {res.status_code}", flush=True)
            return None
            
        # Buscamos la URL con el patrón exacto de premarket del día
        patron = r"https://www.cnbc.com/\d{4}/\d{2}/\d{2}/stocks-making-the-biggest-moves-premarket-[\w-]+.html"
        urls_encontradas = re.findall(patron, res.text)
        
        if urls_encontradas:
            url_final = urls_encontradas[0]
            print(f"🎯 [Sitemap] ¡URL encontrada sin buscadores!: {url_final}", flush=True)
            return url_final
            
        print("⚠️ [Sitemap] La nota de Premarket aún no figura en el sitemap.", flush=True)
        return None
        
    except Exception as e:
        print(f"❌ [Sitemap] Error de red: {e}", flush=True)
        return None