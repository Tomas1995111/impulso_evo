"""Variables de entorno y constantes compartidas por todos los flujos."""
import os

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Evolution API
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution_api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "Impulso")

# Grupos WhatsApp
GRUPO_DEFAULT = os.getenv("GRUPO_DEFAULT")
BACKUP = os.getenv("GRUPO_BACKUP")
REVISION = os.getenv("GRUPO_REVISION")
PREMIUM = os.getenv("GRUPO_PREMIUM")
FREE = os.getenv("GRUPO_FREE")

# URL de prueba para noticia_mercado en modo test
DEFAULT_TEST_PREMARKET_URL = os.getenv(
    "TEST_PREMARKET_URL",
    "https://www.cnbc.com/2026/05/15/stocks-making-the-biggest-moves-premarket-amat-intc-micc.html",
)

# Ruta absoluta a credenciales de Google
CREDENTIALS_FILE = str(BASE_DIR / "mensajes" / "credenciales.json")

# Timezone por defecto
TIMEZONE = "America/Argentina/Buenos_Aires"

# Google Sheet de alertas (core.alerts)
SHEET_ID = os.getenv("SHEET_ID", "1Z9gfXGPdhBktLMwAIj4KpJ5SI2hDKK5lXG2Z63DaMSI")

# Google Sheet de clientes / inbound (pestaña Maestro)
LEADS_SHEET_ID = os.getenv(
    "LEADS_SHEET_ID",
    "1ev-UYItiGQX7tSjNGV4-OHjVwT792KnHP3Vq9ghUlmQ",
)
LEADS_SHEET_TAB = os.getenv("LEADS_SHEET_TAB", "Maestro")
TRIAL_GROUP_JID = os.getenv("TRIAL_GROUP_JID", FREE or "")

# Alpha Vantage (calendario de balances)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "UA4MTIIYCGNESIPL")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
INBOUND_TTL_SECONDS = int(os.getenv("INBOUND_TTL_SECONDS", str(60 * 60 * 6)))  # 6h
ABANDONED_UMBRAL_MINUTOS = int(os.getenv("ABANDONED_UMBRAL_MINUTOS", "30"))
