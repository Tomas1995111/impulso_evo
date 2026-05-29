# Impulso Evo — AGENTS.md

## Project structure

```
run_broadcast.py   → flows/broadcast/broadcast.py   (APScheduler, mensajes programados)
run_inbound.py     → flows/inbound/inbound.py        (FastAPI, webhook onboarding)
run_crm.py         → flows/crm/crm_worker.py         (APScheduler, CRM diario 9 AM)
core/config.py     — env vars y constantes compartidas (importado por todo el proyecto)
core/evolution_client.py — HTTP client hacia Evolution API
core/sheets_client.py    — Google Sheets append para leads
```

Una sola imagen Docker (`Dockerfile`), tres servicios en `docker-compose.yml` con distintos `command:`.

## Setup

```bash
cp .env.example .env                          # llenar con valores reales
cp mensajes/credenciales.example.json mensajes/credenciales.json  # service account de Google
docker compose up -d --build                  # levanta todo
```

Servicios: `postgres`, `redis`, `evolution_api`, `bot`, `bot_inbound`, `bot_crm`.

## Comandos frecuentes

```bash
docker compose logs -f impulso_bot            # broadcast
docker compose logs -f impulso_bot_inbound    # inbound
docker compose logs -f impulso_bot_crm        # CRM
docker compose exec bot python scripts/grupos.py   # listar grupos WhatsApp
docker compose run --rm bot python -c "..."        # ejecutar código ad-hoc
```

## Arquitectura clave

- **Broadcast**: `BlockingScheduler` con jobs cron/date. Los mensajes especiales (`noticia_mercado`, `resumen_indices`, etc.) se resuelven via `MENSAJES_ESPECIALES` dict en `broadcast.py:88`. Contenido rotativo (miercoles/viernes/motivacionales) se persiste en `estado_mensajes.json` con mezcla aleatoria.
- **Inbound**: FastAPI escucha en `:8000/messages-upsert`. Conversación guiada por estados en Redis (`idle → awaiting_name → awaiting_email`). TTL 6h. Tolerante a fallos de Sheets o grupo.
- **CRM**: `process_crm()` lee Google Sheets, aplica reglas de negocio (Trial0→Trial3→...→Eliminado→Retargeting), actualiza estados. Corre 1 vez al día vía APScheduler.
- **Evolution API**: El servicio `evolution_api` en docker-compose es `evoapicloud/evolution-api:latest`. Los bots se conectan por `http://evolution_api:8080`. La instancia se llama `Impulso` por defecto (`EVOLUTION_INSTANCE_NAME`).

## Convenciones y quirks

- Sin linter, typecheck, tests, pre-commit, ni CI.
- `core/__init__.py` es docstring-only, no hay imports de paquete.
- Los `__init__.py` de cada paquete son solo docstring (namespace packages).
- No hay `requirements-dev.txt` ni `pyproject.toml`. Todo en `requirements.txt`.
- Las credenciales de Google viven en `mensajes/credenciales.json` (gitignorado). Ruta absoluta resuelta en `core.config.CREDENTIALS_FILE`.
- `estado_mensajes.json` es runtime state — se monta como volumen en Docker.
- `ZoneInfo("America/Argentina/Buenos_Aires")` usado en inbound; timezone hardcoded como string en broadcast y run_crm.
- Las alertas bursátiles (`mensajeAlertaCompra*`) tienen su propio cliente gspread inline, no usan `core/sheets_client.py`.
- Las funciones `send_text` y `send_text_to_destinations` en evolution_client usan `print()` para logging (no `logging`).
- No hay `.env` loading automático en `run_broadcast.py` ni `run_inbound.py` — las variables se inyectan via `env_file: .env` en docker-compose. El CRM worker sí usaba `load_dotenv()` pero fue eliminado en refactor.

## Archivos que no deben modificarse sin cuidado

- `estado_mensajes.json`: estado vivo de rotación de mensajes. Si se pierde, los índices se recrean mezclando desde cero (comportamiento seguro pero pierde progreso).
- `flows/crm/crm_worker.py`: tiene columnas hardcodeadas (1-based: COL_TELEFONO=1, COL_NOMBRE=2, COL_FECHA_CAPTURA=4, etc.). Cambiar la estructura del Sheet requiere actualizar estas constantes.
