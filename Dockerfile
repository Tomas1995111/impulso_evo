FROM python:3.11-slim
WORKDIR /app

# Agregá acá yfinance y cualquier otra librería que usen tus módulos de mensajes
RUN pip install --no-cache-dir apscheduler requests yfinance gspread oauth2client google-genai selenium ddgs chromium

COPY . .

CMD ["python", "-u", "automatizarMensajes.py"]