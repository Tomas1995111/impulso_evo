# Pendientes Impulso Evo

> Lista unificada de pendientes: bugs, seguridad, refactorización, negocio, testing e innovación.
> Dificultad: 1 (trivial) → 10 (rediseño completo).
> Última actualización: #15 (cache phone_exists) completado.

---

## FASE 1 — Bugs y Seguridad (urgente)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 1 | Rate-limit en webhook `/messages-upsert` | 2 | `flows/inbound/inbound.py` | Middleware FastAPI con contador Redis, ventana 1 min. Sin esto, spameo → quota Sheets agotada |
| 2 | USER non-root en Dockerfile | 3 | `Dockerfile` | Container corre como root. Crear `appuser`, `chown`, `USER appuser` |

---

## FASE 2 — Refactorización (calidad de código)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 3 | Unificar inicialización de Google Sheets | 3 | `flows/crm/crm_worker.py`, `core/sheets_client.py` | CRM usa `gspread.service_account()` directamente, sheets_client tiene su propio pool. Unificar en un solo punto |
| 4 | Mover mensajes del CRM a JSON externo | 2 | `flows/crm/crm_worker.py`, `contenido/` | Los 7 mensajes hardcodeados en `get_message()` → `contenido/crm_messages.json` para editar sin deploy |
| 5 | Mover `mensajes_fecha` a JSON externo | 3 | `flows/broadcast/broadcast.py`, `contenido/` | Feriados hardcodeados en Python → `contenido/mensajes_fecha.json` |
| 6 | Centralizar timezone | 1 | Nuevo `core/` o actualizar `config.py` | `ZoneInfo` como string en inbound, como `ZoneInfo` en otro lado, hardcodeada en broadcast/CRM. Crear `config.TIMEZONE_OBJ` |
| 7 | Renombrar `BACKUP` → `GRUPO_BACKUP` | 1 | `core/config.py`, callers | Inconsistencia de naming. Rename mecánico con grep |
| 8 | Reemplazar `print()` por `logging` | 1 | `core/evolution_client.py` | `send_text` y `send_text_to_destinations` usan `print()` en vez de `logging` |
| 9 | Mover listados de tickers a archivo separado | 2 | `core/alerts.py` → `core/tickers.py` | 200+ tickers hardcodeados en `alerts.py`. Mejor separar |
| 10 | Agregar type hints a funciones públicas | 2 | Todos los `core/` y `flows/` | Proyecto usa `from __future__ import annotations` en algunos archivos pero no en todos |
| 11 | Crear `core/exceptions.py` | 2 | `core/exceptions.py` | Excepciones custom (`AlertError`, `SheetError`, `EvolutionError`) en vez de `Exception` genérica |
| 12 | Healthchecks para servicios Python | 2 | `docker-compose.yml`, `flows/inbound/inbound.py` | `bot` y `bot_crm` no tienen healthcheck. Agregar test de Redis+Evolution en el endpoint `/health` |
| 13 | Pin de versión Evolution API | 1 | `docker-compose.yml` | `:latest` → tag fijo. Riesgo de breaking change silencioso |
| 14 | Deploy limits (memoria/CPU) | 2 | `docker-compose.yml` | Agregar `deploy: resources: limits` a cada servicio Python |
| 15 | Logging estructurado | 3 | Todos los servicios | `structlog` o JSON logging para debugging en producción |

---

## FASE 3 — Negocio / CX / CRM

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 16 | Validación de email en inbound | 1 | `flows/inbound/inbound.py` | Regex simple (`@` y `.`) antes de guardar en Sheets. Hoy acepta cualquier string |
| 17 | Subir TTL de Redis a 24h | 1 | `core/config.py` | El TTL de 6h para conversaciones es agresivo. Un usuario que se distrae pierde el estado |
| 18 | Check-in CRM día 1 | 2 | `flows/crm/crm_worker.py`, `contenido/` | Nuevo mensaje post-registro: "¿Te gustó el primer resumen? Mañana tenés otro." Actualmente el CRM inicia día 3 |
| 19 | Auto-detectar bajas por inactividad | 3 | `flows/crm/crm_worker.py` | Si el usuario no responde en 14 días → transición a Baja automática. Hoy es 100% manual |
| 20 | Encuesta automática de baja | 3 | `flows/crm/crm_worker.py` | Al dar de baja, enviar: "¿Por qué? 1) Precio 2) Tiempo 3) Contenido 4) Otro" y registrar motivo |
| 21 | Dashboard de métricas para admin | 4 | Nuevo endpoint o script | Endpoint `/dashboard` con: leads hoy, trials activos, conversiones Trial→Pago, bajas del mes |
| 22 | Alertas de churn al admin | 3 | `flows/crm/crm_worker.py` | Notificar al admin cuando un usuario lleva X días sin interacción en el grupo |
| 23 | Reducir frecuencia de mensajes | 2 | `flows/broadcast/broadcast.py` | 6-7 mensajes/día puede causar fatiga. Evaluar consolidar a 3-4 o ofrecer "modos" (conservador/agresivo) |
| 24 | Segmentación por perfil | 4 | Inbound + CRM + Broadcast | Preguntar en onboarding qué le interesa (Acciones/CEDEARs/Cripto/Renta fija) y filtrar contenido |

---

## FASE 4 — Testing y DevOps

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 25 | Tests de integración | 4 | `tests/` | Al menos 5 tests que mockeen el pipeline completo (inbound → Sheets → Redis → Evolution) |
| 26 | CI/CD con GitHub Actions | 4 | `.github/workflows/` | Pipeline: lint → test → build. Deploy manual |
| 27 | Cobertura de código | 2 | `pytest.ini`, CI | Agregar `pytest-cov` al pipeline, meta 70%+ |
| 28 | Exportar leads a CSV | 2 | `core/sheets_client.py` | Función `exportar_csv()` para reporting manual sin abrir Sheets |

---

## FASE 5 — Innovación

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 29 | Bot de consultas inteligente | 6 | `flows/inbound/commands.py`, Gemini | Comando `/opinar TICKER` que consulte Gemini con datos de yfinance para dar análisis en tiempo real |
| 30 | Alertas push personalizadas (watchlist) | 6 | Nuevo Sheet + cron job | El usuario configura tickers de interés (`/seguir AAPL GGAL`), recibe alerta privada si movimiento >2% |
| 31 | Simulador de cartera | 7 | Nuevo Sheet + cron job | `/cartera AAPL:30%,GGAL:20%` → análisis semanal de rentabilidad ficticia con yfinance |

---

## Completados (histórico — no modificar)

| # | Item | Dificultad | Archivos |
|---|------|:----------:|----------|
| 1 | `.dockerignore` (nuevo) | 1 | `.dockerignore` |
| 2 | Volumen `credenciales.json` en servicio `bot` | 1 | `docker-compose.yml` |
| 3 | Mover `POSTGRES_PASSWORD` a `.env` | 2 | `docker-compose.yml`, `.env.example`, `.env` |
| 4 | `logging.basicConfig()` en `run_broadcast.py` y `run_inbound.py` | 1 | `run_broadcast.py`, `run_inbound.py` |
| 5 | Sacar volumen huérfano `./flows/crm` de `bot_inbound` | 1 | `docker-compose.yml` |
| 6 | Rutas absolutas en `broadcast.py` y `mensajeCotizacionDolar.py` | 3 | `flows/broadcast/broadcast.py`, `mensajes/mensajeCotizacionDolar.py` |
| 7 | Actualizar fixtures de `tests/test_broadcast.py` | 4 | `tests/test_broadcast.py` |
| 8 | Limpiar `SHEET_ID` duplicado en `core/alerts.py:16` | 1 | `core/alerts.py` |
| 9 | `arranque_impulso.bat` con `%~dp0` | 1 | `arranque_impulso.bat` |
| 10 | Fix `TICKERS_ARG` duplicado (`TECO2.BA`) | 1 | `core/alerts.py` |
| 11 | Sacar `ALPHA_VANTAGE_API_KEY` hardcodeada | 1 | `core/config.py:44` |
| 12 | Renombrar `SHEET_ID` → `ALERTAS_SHEET_ID` + quitar defaults hardcodeados | 2 | `core/config.py`, `core/alerts.py`, `core/sheets_client.py`, `tests/conftest.py`, `.env`, `.env.example`, `README.md` |
| 13 | Fix formatos fecha en `get_days_diff()` (sacar `%G:%M` y `%k:%M`) | 1 | `flows/crm/crm_worker.py` |
| 14 | Actualizar docstring `add_participant_to_group` (acepta dígitos y JID) | 1 | `core/evolution_client.py` |
| 15 | Cache de `phone_exists()` en Redis (TTL 5min) | 2 | `core/sheets_client.py` |
| 16 | Thread-safety en `_client_cache` (Lock + DCL) | 4 | `core/sheets_client.py` |
| 17 | Diagnosticar inbound "no dispara" (Fase 1) | 3 | (sin cambios) |
| 18 | Mejorar logging del inbound (5 silent-exit points) | 2 | `flows/inbound/inbound.py` |

---

## Resumen ejecutivo

- **Total pendientes activos:** 31
- **Por fase:** Seguridad 2 | Refactor 13 | Negocio 9 | Testing 4 | Innovación 3
- **Dificultad promedio:** 2.5/10
- **Items más urgentes:** #1-2 (bugs + seguridad)
- **Mayor impacto de negocio:** #18 (check-in día 1), #19 (auto-bajas), #23 (frecuencia mensajes)
