FROM python:3.10-slim
WORKDIR /app

# Agregá acá yfinance y cualquier otra librería que usen tus módulos de mensajes
RUN pip install --no-cache-dir apscheduler requests yfinance gspread oauth2client

COPY . .

CMD ["python", "-u", "automatizarMensajes.py"]