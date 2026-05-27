FROM python:3.11-slim
WORKDIR /app

# Agregá acá yfinance y cualquier otra librería que usen tus módulos de mensajes
RUN pip install --no-cache-dir apscheduler requests yfinance gspread oauth2client google-genai python-dotenv selenium ddgs chromium fastapi uvicorn redis

COPY . .

CMD ["python", "-u", "run_broadcast.py"]
