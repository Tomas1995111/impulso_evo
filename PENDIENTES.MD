# Pendientes Impulso Evo

> Lista priorizada de cambios identificados durante la revisión del proyecto.
> Dificultad: 1 (trivial) → 10 (rediseño).
> Última actualización: #19 (logging) y #13 (thread-safety) completados.

---

## Pendientes (ordenados del más al menos importante)

| # | Item | Dificultad | Archivos | Por qué importa |
|---|------|:----------:|----------|-----------------|
| 15 | **Rate-limit en webhook `/messages-upsert`** | 2/10 | `flows/inbound/inbound.py` | Sin rate-limit, un usuario (o bot malicioso) enviando 100 mensajes en 1 segundo golpea Google Sheets 100 veces y puede causar 429s. Mitigación: contador Redis con ventana de 1 minuto. |
| 14 | **Cache de `phone_exists()` en Redis** | 4/10 | `core/sheets_client.py` | Cada trigger de inbound hace 1 llamada a `phone_exists()` → 1 hit a Google Sheets. Con cache Redis (TTL 5 min) yace el 90% de las llamadas, baja la latencia y protege el quota de la API. |
| 11 | **`USER` no-root en Dockerfile** | 3/10 | `Dockerfile` | Hoy el container corre como root. Si alguien explota una vulnerabilidad de `requests` o `uvicorn`, obtiene root en el host. Mitigación: crear `appuser`, `chown`, `USER appuser`. |
| 12 | **Healthchecks para servicios Python** | 2/10 | `docker-compose.yml`, `flows/inbound/inbound.py` | Sin healthcheck, `docker ps` muestra "Up" aunque el proceso esté en deadlock. Solución: endpoint `/health` en FastAPI que retorna 200 si Redis+Evolution responden, y `test: ["CMD", "curl", ...]` en compose. |
| 16 | **Mover `mensajes_fecha` a JSON externo** | 3/10 | `flows/broadcast/broadcast.py`, `contenido/` | Hoy los mensajes por fecha están hardcodeados en un dict Python (línea ~86 `MENSAJES_ESPECIALES` o un dict similar). Moverlos a `contenido/mensajes_fecha.json` permite editarlos sin deploy. |
| 10 | **Pin de versión Evolution API** (`:latest` → tag fijo) | 1/10 | `docker-compose.yml` | Con `:latest`, un día Evolution API publica un breaking change y los 3 bots rompen a la vez. Decisión previa: dejar `:latest` por ahora. Riesgo aceptado. |
| 17 | **Renombrar `BACKUP` → `GRUPO_BACKUP`** en config | 1/10 | `core/config.py`, callers | Inconsistencia de naming. Hoy `BACKUP = os.getenv("GRUPO_BACKUP")` en `core/config.py:15`. Cambio mecánico: rename + update de los call sites (buscar con `grep -rn "config.BACKUP"`). |

### Detalle de los top-2 (los más críticos)

- **#15 — Rate-limit en `/messages-upsert`**
  Un usuario puede mandar N mensajes en poco tiempo (legítimo o no). Cada uno triggerea `phone_exists()` → 1 hit a Google Sheets. Si la frecuencia es alta, se pasa el quota y la API responde 429, lo que el `try/except` actual en `inbound.py:174-175` se traga silenciosamente (ahora loggea con #19, pero el usuario no recibe respuesta). Mitigación:
  1. Middleware FastAPI que cuente hits por `remote_jid` en Redis con `INCR` + `EXPIRE 60`.
  2. Si supera N mensajes por minuto → return 429 inmediato sin tocar Sheets.
  3. Aplicar antes de parsear el payload (ahorra CPU en validación).

- **#14 — Cache de `phone_exists()`**
  `phone_exists()` (línea 140) hace `get_all_values()` sobre toda la hoja Maestro, que puede tener cientos de filas. Cada trigger inbound = 1 llamada completa. Si tenés 100 triggers/hora son 100 fetches completos. Cache Redis con TTL 5 min reduce el 90% a costo de 1 GET por key. La invalidación es trivial: cuando `append_lead_row()` escribe, hace `redis.delete(f"phone_exists:{phone}")` para ese teléfono.

---

## Completados (histórico)

| # | Item | Dificultad | Archivos |
|---|------|:----------:|----------|
| 1 | `.dockerignore` (nuevo) | 1/10 | `.dockerignore` |
| 2 | Volumen `credenciales.json` en servicio `bot` | 1/10 | `docker-compose.yml` |
| 3 | Mover `POSTGRES_PASSWORD` a `.env` | 2/10 | `docker-compose.yml`, `.env.example`, `.env` |
| 4 | `logging.basicConfig()` en `run_broadcast.py` y `run_inbound.py` | 1/10 | `run_broadcast.py`, `run_inbound.py` |
| 5 | Sacar volumen huérfano `./flows/crm` de `bot_inbound` | 1/10 | `docker-compose.yml` |
| 6 | Rutas absolutas en `broadcast.py` y `mensajeCotizacionDolar.py` | 3/10 | `flows/broadcast/broadcast.py`, `mensajes/mensajeCotizacionDolar.py` |
| 7 | Actualizar fixtures de `tests/test_broadcast.py` | 4/10 | `tests/test_broadcast.py` |
| 8 | Limpiar `SHEET_ID` duplicado en `core/alerts.py:16` | 1/10 | `core/alerts.py` |
| 9 | `arranque_impulso.bat` con `%~dp0` | 1/10 | `arranque_impulso.bat` |
| 18 | Diagnosticar inbound "no dispara" (Fase 1) | 3/10 | (sin cambios) — el código funcionaba bien, el usuario ya estaba en `LEADS_SHEET_ID` y `phone_exists()` retornaba `True` como debe. |
| 19 | Mejorar logging del inbound (5 silent-exit points) | 2/10 | `flows/inbound/inbound.py` |
| 13 | Thread-safety en `_client_cache` (Lock + DCL) | 4/10 | `core/sheets_client.py` |

---

## Resumen ejecutivo

- **Pendientes activos**: 7 (#15, #14, #11, #12, #16, #10, #17)
- **Items completados**: 12 (1-9 del plan original + #18, #19, #13 del backlog)
- **Dificultad promedio pendientes**: 2.3/10
- **Próximo sugerido**: #15 (rate-limit) — bajo costo, evita incidentes de quota en Sheets
