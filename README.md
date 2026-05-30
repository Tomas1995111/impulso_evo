# Impulso Evo

Bot de WhatsApp para automatizar la comunicación con leads y clientes de **Impulso Merval**. Gestiona tres flujos independientes: mensajería programada a grupos (**Broadcast**), onboarding conversacional (**Inbound**), y ciclo de vida de trials con CRM (**CRM**).

---

## Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Configuración Inicial](#configuración-inicial)
- [Levantar el Proyecto](#levantar-el-proyecto)
- [Servicios](#servicios)
- [Logs](#logs)
- [Tests](#tests)
- [Variables de Entorno](#variables-de-entorno)
- [Archivos Ignorados por Git](#archivos-ignorados-por-git)
- [Flujo de Trabajo](#flujo-de-trabajo)
- [Mantenimiento](#mantenimiento)

---

## Arquitectura

```
impulso_evo/
├── core/                        # Módulos compartidos entre todos los flujos
│   ├── config.py                # Variables de entorno y constantes
│   ├── evolution_client.py      # Cliente HTTP para Evolution API (envío, gestión de grupos, retry)
│   ├── sheets_client.py         # Cliente Google Sheets (append de leads y alertas)
│   └── alerts.py                # Lógica de alertas bursátiles (fetch, build, save, tickers)
├── flows/
│   ├── broadcast/               # Flujo 1 — Mensajes programados a grupos WhatsApp
│   │   └── broadcast.py         #   APScheduler, mensajes semanales/fecha, contenido rotativo
│   ├── inbound/                 # Flujo 2 — Webhook de onboarding conversacional
│   │   ├── inbound.py           #   FastAPI, estados: idle → awaiting_name → awaiting_email → done
│   │   └── state.py             #   Persistencia en Redis con TTL de 6h
│   └── crm/                     # Flujo 3 — Ciclo de vida de leads (Trial → Retargeting)
│       └── crm_worker.py        #   Transiciones de estado, batch update en Sheets
├── mensajes/                    # Generadores de contenido bursátil
│   ├── mensajeCotizacionDolar.py#   Cotización del dólar
│   ├── mensajeIndices.py        #   Resumen de índices
│   ├── mensajeResumen.py        #   Resumen de noticias de mercado
│   └── credenciales.example.json#   Template de service account Google
├── contenido/                   # Contenido rotativo (JSON)
│   ├── miercoles.json           #   Rotación de los miércoles
│   ├── viernes.json             #   Rotación de los viernes
│   └── motivacionales.json      #   Rotación de mensajes motivacionales
├── scripts/
│   └── grupos.py                # Utilidad para listar grupos WhatsApp
├── tests/                       # Tests unitarios
│   ├── conftest.py              #   Fixtures compartidos (fakeredis, mocks de Evolution/Sheets)
│   ├── test_broadcast.py        #   17 tests
│   ├── test_crm.py              #   21 tests
│   └── test_inbound.py          #   25 tests
├── run_broadcast.py             # Entry point: Broadcast (BlockingScheduler)
├── run_inbound.py               # Entry point: Inbound (Uvicorn + FastAPI)
├── run_crm.py                   # Entry point: CRM (APScheduler, ejecuta a las 9 AM)
├── Dockerfile                   # Imagen Python 3.11-slim para los 3 servicios
├── docker-compose.yml           # Orquestación: 6 contenedores
├── requirements.txt             # Dependencias de producción
├── requirements-dev.txt         # Dependencias de desarrollo (tests)
├── pytest.ini                   # Configuración de pytest
├── .env.example                 # Template de variables de entorno
├── estado_mensajes.json         # Estado vivo de rotación de contenido (runtime)
└── arranque_impulso.bat         # Script de arranque rápido para Windows
```

### Diagrama de Flujo

```
                     ┌──────────────┐
                     │  Evolution   │
                     │  API (8080)  │
                     └──────┬───────┘
                            │
              ┌─────────────┼──────────────┐
              │             │              │
         ┌────▼────┐  ┌────▼────┐   ┌─────▼─────┐
         │  BOT    │  │ INBOUND │   │   CRM     │
         │Broadcast│  │ :8000   │   │ (9 AM)    │
         └─────────┘  └────┬────┘   └───────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │ (estado conversacional)
                    └─────────────┘
              ┌─────────────┐
              │Google Sheets│ (leads + alertas)
              └─────────────┘
```

---

## Requisitos

- **Docker** + **Docker Compose** (recomendado)
- O Python 3.11+ para ejecución local sin Docker
- Una cuenta de **Google Cloud** con Service Account y Sheets API habilitada
- Una instancia de **Evolution API** (se incluye en `docker-compose.yml`)
- Una instancia de **WhatsApp** conectada a Evolution API

---

## Configuración Inicial

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd impulso_evo
```

### 2. Crear archivos de configuración

```bash
cp .env.example .env
cp mensajes/credenciales.example.json mensajes/credenciales.json
```

### 3. Completar `.env`

Editar `.env` con tus valores reales. Las variables mínimas requeridas:

| Variable | Dónde obtenerla |
|----------|----------------|
| `EVOLUTION_API_KEY` | De la configuración de Evolution API |
| `EVOLUTION_INSTANCE_NAME` | Nombre de la instancia en Evolution (default: `Impulso`) |
| `LEADS_SHEET_ID` | ID de la Google Sheet de leads (de la URL: `/d/<ID>/edit`) |
| `SHEET_ID` | ID de la Google Sheet de alertas (opcional, tiene default) |
| `GEMINI_API_KEY` | Google AI Studio → API Key |
| `GRUPO_DEFAULT`, `PREMIUM`, etc. | Ejecutar `scripts/grupos.py` con el bot corriendo |

> **Importante:** `GRUPO_FREE` y `TRIAL_GROUP_JID` deben tener el mismo JID (grupo donde entran los trials).

### 4. Completar credenciales de Google

Pegar el JSON de tu **Service Account** de Google Cloud en `mensajes/credenciales.json`.

La Service Account debe tener permisos de editor en las Google Sheets que uses (`LEADS_SHEET_ID` y `SHEET_ID`). Para compartir una Sheet con la Service Account, usá el email que aparece en el JSON (`client_email`) como editor en la Sheet.

### 5. Verificar `.gitignore`

Los siguientes archivos están en `.gitignore` y **nunca deben commitearte**:

```
.env
mensajes/credenciales.json
*.key
*.pem
*.log
```

---

## Levantar el Proyecto

### Primera vez (construir imagen)

```bash
docker compose up -d --build
```

Esto construye la imagen Docker e inicia los 6 servicios. La primera vez puede tardar varios minutos (descarga imágenes base, instala dependencias, Evolution API configura la base de datos).

### Inicios subsecuentes

```bash
docker compose up -d
```

### Servicios que se levantan

| Servicio | Contenedor | Puerto | Descripción |
|----------|-----------|--------|-------------|
| `postgres` | `postgres_evo` | — | Base de datos de Evolution API |
| `redis` | `redis` | — | Almacén de estado conversacional |
| `evolution_api` | `impulso_bot_evoapi` | `8080` | API de WhatsApp |
| `bot` | `impulso_bot` | — | Broadcast (mensajes programados) |
| `bot_inbound` | `impulso_bot_inbound` | `8000` | Webhook de onboarding |
| `bot_crm` | `impulso_bot_crm` | — | CRM diario (9 AM ART) |

### Detener

```bash
docker compose down
```

Para detener y eliminar volúmenes (borra datos de Postgres, Redis e instancias de Evolution):

```bash
docker compose down -v
```

---

## Logs

```bash
# Todos los servicios
docker compose logs -f

# Servicio específico
docker compose logs -f bot          # Broadcast
docker compose logs -f bot_inbound  # Inbound (webhook)
docker compose logs -f bot_crm      # CRM
docker compose logs -f evolution_api # Evolution API
```

Los logs de los bots se muestran en stdout (sin archivos de log locales). Evolution API tiene su propio sistema de logging.

---

## Webhook (Evolution → Inbound)

Para que el onboarding funcione, hay que configurar Evolution API para que envíe los eventos `MESSAGES_UPSERT` al bot de inbound.

### Configuración en Evolution API

1. Abrir la UI de Evolution (http://localhost:8080)
2. Ir a la instancia → Webhook
3. Configurar URL: `http://bot_inbound:8000/messages-upsert`
4. Evento: `MESSAGES_UPSERT`

### Seguridad del Webhook (opcional)

Para proteger el endpoint contra accesos no autorizados:

1. En `.env`:
   ```env
   INBOUND_WEBHOOK_SECRET=tu_token_secreto
   ```
2. En la UI de Evolution, agregar el header personalizado:
   ```
   apikey: tu_token_secreto
   ```

Si `INBOUND_WEBHOOK_SECRET` está vacío, el webhook funciona sin autenticación.

---

## Tests

### Qué hacen los tests

Los tests unitarios validan los 3 flujos **sin conexión a APIs reales**. Evolution API, Google Sheets, Redis y Gemini se reemplazan por mocks usando `unittest.mock`, `fakeredis` y `httpx` (TestClient de FastAPI).

### Requisitos para tests

Los tests corren dentro del contenedor Docker o localmente. No necesitan:
- Instancia de Evolution API
- Redis real
- Google Sheets real
- Conexión a internet (excepto la primera instalación de dependencias)

### Paso a paso para ejecutar tests

#### Opción 1: Con Docker (recomendada)

```bash
# 1. Construir la imagen (incluye dependencias de producción y test)
docker compose build

# 2. Ejecutar TODOS los tests
docker compose run --rm bot python -m pytest tests/ -v
```

Salida esperada (final):
```
tests/test_broadcast.py::TestResolverMensaje::test_texto_literal_devuelve_mismo_texto PASSED
...
tests/test_crm.py::TestProcessCRM::test_lead_sin_telefono_se_skip PASSED
...
tests/test_inbound.py::TestOrigenDetection::test_origin_instagram_detectado PASSED

======================= 63 passed in XXs =======================
```

Todos los tests deben pasar con **63 passed** y **0 failed**.

#### Opción 2: Tests de un flujo específico

```bash
# Broadcast (17 tests)
docker compose run --rm bot python -m pytest tests/test_broadcast.py -v

# CRM (21 tests)
docker compose run --rm bot python -m pytest tests/test_crm.py -v

# Inbound (25 tests)
docker compose run --rm bot python -m pytest tests/test_inbound.py -v
```

#### Opción 3: Por marca (tags definidos en pytest.ini)

```bash
docker compose run --rm bot python -m pytest tests/ -m broadcast -v
docker compose run --rm bot python -m pytest tests/ -m inbound -v
docker compose run --rm bot python -m pytest tests/ -m crm -v
```

#### Opción 4: Sin Docker (local, requiere Python 3.11+)

```bash
# 1. Crear y activar entorno virtual (opcional)
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# 2. Instalar dependencias
pip install -r requirements.txt -r requirements-dev.txt

# 3. Ejecutar tests
python -m pytest tests/ -v
```

> **Nota:** Localmente podés necesitar Redis corriendo para algunos fixtures de `conftest.py`. Si no tenés Redis, usá `fakeredis` que es la versión simulada en memoria. El conftest ya lo configura automáticamente.

### Cobertura (opcional)

```bash
# Instalar pytest-cov primero
docker compose run --rm bot pip install pytest-cov

# Ejecutar con cobertura
docker compose run --rm bot python -m pytest tests/ --cov=flows --cov=core --cov-report=term-missing
```

### Estructura de tests

| Archivo | Cantidad | ¿Qué mockea? |
|---------|----------|-------------|
| `tests/test_broadcast.py` | 17 | `requests.post` (Evolution API), `yfinance`, `random.shuffle` |
| `tests/test_crm.py` | 21 | `gspread` completo, `evolution_client.send_text`, `evolution_client.remove_participant_from_group` |
| `tests/test_inbound.py` | 25 | `fakeredis` (Redis), `evolution_client` (envío y grupo), `sheets_client.append_lead_row` |

### Casos testeados

**Broadcast:**
- Resolución de mensajes: texto literal devuelve el mismo texto, claves especiales ejecutan su función
- Modo test: `noticia_mercado` recibe `test_url` en lugar de scrapear
- Rotación de contenido: avance de índice, mezcla cuando se agota, persistencia en JSON
- Estructura de mensajes: todos los mensajes programados tienen los campos esperados
- Envío: se llama a Evolution API con los parámetros correctos
- Tolerancia a errores: si falla un generador de contenido, no crashea el bot

**CRM:**
- `get_days_diff`: 5 formatos de fecha, valores vacíos/nulos, formato inválido
- `get_message`: 7 mensajes de texto con parámetros, ID inexistente devuelve vacío
- Transiciones de estado: Trial0→Trial3→Trial5→Trial6→Eliminado→Retargeting 15→Retargeting Final
- Baja→Baja Final (60+ días desde fecha de baja)
- Premium y estados finales se skippean (no se envían mensajes)
- Leads sin teléfono se skippean
- Batch update: se llama a `update_cells` con las celdas correctas

**Inbound:**
- Seguridad: rechazo sin token, token incorrecto (403), aceptación con token correcto, funcionamiento sin token configurado
- Flujo completo: idle→awaiting_name→awaiting_email→done (incluye inserción en Sheets)
- `extendedTextMessage` como alternativa a `conversation`
- Payloads anidados con `data.key` / `data.message`
- Filtros: `from_me` ignorado, mensajes de grupo ignorados, mensajes sin texto ignorados
- Tolerancia a fallos: si falla `add_participant_to_group` (500) el flujo continúa; si falla Sheets, el flujo continúa
- Origen detection: detecta "prueba gratis" → Instagram, "prueba gratuita" → TikTok, otros → idle

### Resultado esperado

```
======================= 63 passed in XXs =======================
```

Sin warnings de errores. Un warning de deprecación de Starlette TestClient es esperado y no afecta la funcionalidad.

---

## Variables de Entorno

Ver `.env.example` para el template completo.

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `EVOLUTION_API_URL` | Sí | `http://evolution_api:8080` | URL base de Evolution API |
| `EVOLUTION_API_KEY` | Sí | — | API Key de Evolution |
| `EVOLUTION_INSTANCE_NAME` | No | `Impulso` | Nombre de la instancia en Evolution |
| `GRUPO_DEFAULT` | Sí | — | JID del grupo principal |
| `GRUPO_BACKUP` | No | — | JID del grupo de backup |
| `GRUPO_REVISION` | Sí | — | JID del grupo de revisión |
| `GRUPO_PREMIUM` | Sí | — | JID del grupo premium |
| `GRUPO_FREE` | Sí | — | JID del grupo free/trial |
| `SHEET_ID` | No | (default interno) | ID de Google Sheet de alertas |
| `LEADS_SHEET_ID` | Sí | (default interno) | ID de Google Sheet de leads |
| `LEADS_SHEET_TAB` | No | `Maestro` | Nombre de la pestaña de leads |
| `GEMINI_API_KEY` | Sí | — | API Key de Google Gemini |
| `TRIAL_GROUP_JID` | Sí | Igual que `GRUPO_FREE` | Grupo donde se agregan los trials |
| `INBOUND_WEBHOOK_SECRET` | No | — | Token de autenticación del webhook |
| `TEST_PREMARKET_URL` | No | (default interno) | URL de prueba para `noticia_mercado` |

### Cómo obtener los JID de grupos

Con el proyecto levantado y Evolution API conectado a WhatsApp:

```bash
docker compose exec bot python scripts/grupos.py
```

Esto lista todos los grupos con su JID. Copiar los que correspondan a tus grupos en `.env`.

---

## Archivos Ignorados por Git

| Archivo | Contenido | Riesgo si se commitea |
|---------|-----------|----------------------|
| `.env` | API keys, contraseñas, tokens | Exposición de credenciales |
| `mensajes/credenciales.json` | Service Account de Google Cloud | Acceso a todas tus Sheets |
| `*.key` / `*.pem` | Llaves privadas | Compromiso criptográfico |
| `*.log` | Logs con números de teléfono, estados | Fuga de datos personales |
| `.vscode/` | Configuración local del editor | — |

---

## Flujo de Trabajo Detallado

### Broadcast (Bot Principal)

El broadcast corre permanentemente con `APScheduler`:

- **Mensajes semanales**: configurados con días y horas específicas (ej: lunes a viernes 9:30, 11:02, 15:30)
- **Mensajes por fecha**: feriados y eventos únicos, se ejecutan una sola vez
- **Contenido rotativo**: mensajes de miércoles, viernes y motivacionales se mezclan aleatoriamente y rotan sin repetir hasta agotar la lista
- **Resolución de contenido**: claves como `cotizacion_dolar`, `resumen_indices`, `noticia_mercado` se resuelven llamando a los generadores en `mensajes/`

El estado de rotación se persiste en `estado_mensajes.json` (montado como volumen en Docker).

### Inbound (Onboarding)

El inbound expone un endpoint FastAPI en `:8000` que recibe webhooks de Evolution:

1. Usuario escribe "quiero prueba gratis de Impulso Merval"
2. Webhook llega a `/messages-upsert`
3. Se valida el token de seguridad (si está configurado)
4. Se detecta el origen (Instagram, TikTok, etc.)
5. Estado pasa a `awaiting_name`, se pregunta el nombre
6. Usuario responde con nombre → estado `awaiting_email`, se pregunta email
7. Usuario responde con email → se agrega al grupo Trial, se guarda en Sheets, se envía mensaje de bienvenida
8. Estado se resetea a `idle`

Tiempo de expiración de sesión: 6 horas (TTL en Redis).

### CRM (Ciclo de Vida)

El CRM se ejecuta una vez al día a las 9 AM ART y procesa todos los leads de la Google Sheet:

| Estado | Días desde captura | Acción | Nuevo estado |
|--------|-------------------|--------|-------------|
| Trial0 | 3+ | Mensaje 1 | Trial3 |
| Trial3 | 5+ | Mensaje 2 | Trial5 |
| Trial5 | 6+ | Mensaje 3 | Trial6 |
| Trial6 | 7+ | Remover del grupo + Mensaje 4 | Eliminado |
| Eliminado | 22+ | Mensaje 5 | Retargeting 15 |
| Retargeting 15 | 47+ | Mensaje 6 | Retargeting Final |
| Baja | 60+ (desde baja) | Mensaje 7 | Baja Final |

Estados que se skippean (no se procesan): `Premium`, `Retargeting Final`, `Baja Final`, `Eliminado Definitivo`.

---

## Mantenimiento

### Actualizar contenido rotativo

Editar los archivos en `contenido/`:
- `miercoles.json` — mensajes para los miércoles
- `viernes.json` — mensajes para los viernes
- `motivacionales.json` — mensajes motivacionales

Cada archivo es un array de strings. Cuando se termina la lista, se mezcla aleatoriamente de nuevo.

### Agregar feriados o mensajes por fecha

Editar `mensajes_fecha` en `flows/broadcast/broadcast.py`. El formato de fecha es `"dd/mm/YYYY HH:MM"`.

### Agregar nuevos tipos de mensajes especiales

1. Crear el generador en `mensajes/` (o donde corresponda)
2. Agregarlo al diccionario `MENSAJES_ESPECIALES` en `flows/broadcast/broadcast.py`
3. Agregar un entry en `mensajes_semana` o `mensajes_fecha` que use la clave

### Modificar reglas de CRM

Editar `flows/crm/crm_worker.py`:
- Las constantes `COL_*` definen el índice de cada columna (1-based)
- Las reglas de transición están en el bloque `# --- BLOQUE TRIAL ---`, `# --- BLOQUE RETARGETING ---`
- Los mensajes están en el dict `messages` de `get_message()`

### Resetear estado de rotación

Eliminar `estado_mensajes.json` y reiniciar el contenedor. Los índices se recrearán automáticamente.

```bash
docker compose stop bot
del estado_mensajes.json
docker compose start bot
```

### Verificar estado de la instancia de WhatsApp

```bash
docker compose logs evolution_api | grep -i "open\|state\|connection"
```

---

## Troubleshooting

| Problema | Posible causa | Solución |
|----------|--------------|----------|
| Los mensajes no se envían | WhatsApp desconectado | Verificar con `docker compose logs evolution_api` |
| Error de Google Sheets | Credenciales inválidas | Verificar `mensajes/credenciales.json` y que la Service Account tenga acceso a la Sheet |
| El webhook responde 403 | Token incorrecto | Verificar `INBOUND_WEBHOOK_SECRET` en `.env` y en la configuración de Evolution |
| El onboarding no avanza de estado | Redis no disponible | Verificar `docker compose logs redis` |
| Tests fallan por conexión | Faltan fixtures de mock | Ejecutar tests dentro del contenedor Docker |

---

## Links Útiles

- [Evolution API](https://doc.evolution-api.com/) — Documentación de la API de WhatsApp
- [Google Cloud Console](https://console.cloud.google.com/) — Crear Service Account y habilitar Sheets API
- [Google AI Studio](https://aistudio.google.com/) — Obtener API Key de Gemini
- [gspread](https://docs.gspread.org/) — Librería Python para Google Sheets
