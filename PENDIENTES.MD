# Pendientes Impulso Evo

> Lista unificada de pendientes, ordenados por prioridad de impacto.
> Dificultad: 1 (trivial) → 10 (rediseño completo).
> Última actualización: reordenado por prioridad.

---

## 🔴 P0 — Crítico (producción rota o riesgo de seguridad)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 1 | Rate-limit en webhook `/messages-upsert` | 2 | `flows/inbound/inbound.py` | Sin esto, spameo → quota Google Sheets agotada. Servicio caído |
| 2 | USER non-root en Dockerfile | 3 | `Dockerfile` | Container corre como root. Riesgo de seguridad en producción |
| 3 | Pin de versión Evolution API | 1 | `docker-compose.yml` | `:latest` → tag fijo. Riesgo de breaking change silencioso |
| 4 | Validación de email en inbound | 1 | `flows/inbound/inbound.py` | Regex simple (`@` y `.`) antes de guardar en Sheets. Hoy acepta cualquier string |
| 5 | Subir TTL de Redis a 24h | 1 | `core/config.py` | TTL de 6h es agresivo. Un usuario que se distrae pierde el estado de conversación |

---

## 🟡 P1 — Alto (experiencia de usuario o impacto de negocio directo)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 6 | Check-in CRM día 1 | 2 | `flows/crm/crm_worker.py`, `contenido/` | Nuevo mensaje post-registro: "¿Te gustó el primer resumen?" Actualmente el CRM inicia en día 3 — los primeros 2 días hay silencio total |
| 7 | Auto-detectar bajas por inactividad | 3 | `flows/crm/crm_worker.py` | Si el usuario no responde en 14 días → transición a Baja automática. Hoy es 100% manual |
| 8 | Reducir frecuencia de mensajes | 2 | `flows/broadcast/broadcast.py` | 6-7 mensajes/día puede causar fatiga y bajas. Evaluar consolidar a 3-4 o ofrecer "modos" |
| 9 | Healthchecks para servicios Python | 2 | `docker-compose.yml`, `flows/inbound/inbound.py` | `bot` y `bot_crm` no tienen healthcheck. Docker no reinicia si el servicio queda colgado |
| 10 | Encuesta automática de baja | 3 | `flows/crm/crm_worker.py` | Al dar de baja, preguntar motivo y registrarlo. Sin esto no hay data para mejorar |
| 11 | Alertas de churn al admin | 3 | `flows/crm/crm_worker.py` | Notificar al admin cuando un usuario lleva X días sin interacción |

---

## 🟢 P2 — Medio (calidad de código y mantenibilidad)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 12 | Unificar inicialización de Google Sheets | 3 | `flows/crm/crm_worker.py`, `core/sheets_client.py` | CRM usa `gspread.service_account()` directamente, sheets_client tiene su propio pool. Duplicación |
| 13 | Reemplazar `print()` por `logging` | 1 | `core/evolution_client.py` | `send_text` y `send_text_to_destinations` usan `print()` en vez de `logging` |
| 14 | Centralizar timezone | 1 | `config.py` | `ZoneInfo` como string en inbound, `ZoneInfo` en otro lado, hardcodeada en broadcast/CRM |
| 15 | Renombrar `BACKUP` → `GRUPO_BACKUP` | 1 | `core/config.py`, callers | Inconsistencia de naming. Rename mecánico con grep |
| 16 | Mover mensajes del CRM a JSON externo | 2 | `flows/crm/crm_worker.py`, `contenido/` | Los 7 mensajes hardcodeados en `get_message()` → `contenido/crm_messages.json` |
| 17 | Mover `mensajes_fecha` a JSON externo | 3 | `flows/broadcast/broadcast.py`, `contenido/` | Feriados hardcodeados en Python → `contenido/mensajes_fecha.json` |
| 18 | Mover listados de tickers a archivo separado | 2 | `core/alerts.py` → `core/tickers.py` | 200+ tickers hardcodeados en `alerts.py` |
| 19 | Deploy limits (memoria/CPU) | 2 | `docker-compose.yml` | Agregar `deploy: resources: limits` a cada servicio Python |
| 20 | Crear `core/exceptions.py` | 2 | `core/exceptions.py` | Excepciones custom en vez de `Exception` genérica |

---

## 🔵 P3 — Bajo (mejoras incrementales, sin urgencia)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 21 | Agregar type hints a funciones públicas | 2 | Todos los `core/` y `flows/` | Proyecto inconsistente con `from __future__ import annotations` |
| 22 | Logging estructurado | 3 | Todos los servicios | `structlog` o JSON logging para debugging en producción |
| 23 | Exportar leads a CSV | 2 | `core/sheets_client.py` | Función `exportar_csv()` para reporting manual sin abrir Sheets |
| 24 | Cobertura de código | 2 | `pytest.ini`, CI | Agregar `pytest-cov` al pipeline, meta 70%+ |

---

## ⚪ P4 — Futuro (proyectos grandes, valor pero no urgente)

| # | Item | Dif | Archivos | Descripción |
|---|------|:---:|----------|-------------|
| 25 | Dashboard de métricas para admin | 4 | Nuevo endpoint o script | Leads hoy, trials activos, conversiones Trial→Pago, bajas del mes |
| 26 | Segmentación por perfil | 4 | Inbound + CRM + Broadcast | Preguntar en onboarding qué le interesa y filtrar contenido |
| 27 | Tests de integración | 4 | `tests/` | Pipeline completo mockeado (inbound → Sheets → Redis → Evolution) |
| 28 | CI/CD con GitHub Actions | 4 | `.github/workflows/` | Pipeline: lint → test → build. Deploy manual |
| 29 | Bot de consultas inteligente | 6 | `commands.py`, Gemini | Comando `/opinar TICKER` con análisis de Gemini + yfinance |
| 30 | Alertas push personalizadas (watchlist) | 6 | Nuevo Sheet + cron job | `/seguir AAPL GGAL` → alerta privada si movimiento >2% |
| 31 | Simulador de cartera | 7 | Nuevo Sheet + cron job | `/cartera AAPL:30%,GGAL:20%` → análisis semanal de rentabilidad |

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

- **Total pendientes:** 31
- **Por prioridad:** P0 Crítico 5 | P1 Alto 6 | P2 Medio 9 | P3 Bajo 4 | P4 Futuro 7
- **Dificultad promedio:** 2.5/10
- **Impacto inmediato:** P0 (#1-5) → producción estable y segura
- **Mayor ROI de negocio:** P1 (#6-11) → retención y monitoreo de usuarios
