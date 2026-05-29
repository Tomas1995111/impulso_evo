# Impulso Merval — Contexto del Negocio y Automatización

---

## 1. El Negocio

**Impulso Merval** es un proyecto argentino de divulgación y educación financiera diseñado para ayudar a trabajadores, profesionales y ahorristas comunes a entender el mercado financiero de forma sencilla.

**Filosofía "Cero Humo":** Traduce la complejidad de la economía y la bolsa local a un lenguaje coloquial y cercano, sin tecnicismos ni promesas de ganancias extraordinarias.

**Modelo de suscripción recurrente:** Membresía mensual que da acceso a una comunidad cerrada en WhatsApp.

**Estructura de grupos:**

| Grupo | Descripción |
|-------|-------------|
| **Free (Trial)** | Prueba gratuita de 7 días. Grupo silencioso (solo administradores). Resumen matutino diario con noticias, cotizaciones del dólar e ideas de inversión. |
| **Premium** | Espacio de pago con carteras sugeridas de CEDEARs/acciones, seguimiento de renta fija, informes especiales y soporte privado directo. |

**Estrategia de contenidos:** Videos cortos verticales en Instagram Reels y TikTok + Meta Ads. Formato híbrido (30% rostro, 70% pantalla compartida). CTA hacia WhatsApp activa la automatización de onboarding.

---

## 2. Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Lenguaje | Python 3.11+ |
| Contenedores | Docker + docker-compose |
| API WhatsApp | Evolution API (evoapicloud/evolution-api) |
| Base de datos principal | PostgreSQL 15 |
| Caché / estados | Redis |
| CRM / leads | Google Sheets (vía gspread) |
| Programación de tareas | APScheduler (BlockingScheduler) |
| Webhook server | FastAPI + Uvicorn |
| IA generativa | Google Gemini 2.5 Flash (resumen de noticias) |
| Datos financieros | yfinance, dolarapi.com |
| Orquestación | docker-compose (5 servicios) |

**Servicios en Docker:**

| Servicio | Container | Puerto | Comando |
|----------|-----------|--------|---------|
| `evolution_api` | impulso_bot_evoapi | 8080 | Evolution API server |
| `bot` | impulso_bot | — | Broadcast (APScheduler) |
| `bot_inbound` | impulso_bot_inbound | 8000 | FastAPI webhook |
| `bot_crm` | impulso_bot_crm | — | CRM diario (APScheduler) |
| `postgres` | postgres_evo | 5432 | Base de datos |
| `redis` | redis | 6379 | Caché / estados |

---

## 3. Flujo de Captura — Inbound Bot

El primer contacto con el lead está completamente automatizado mediante un webhook que recibe los mensajes entrantes de WhatsApp vía Evolution API.

### Detección de origen

El bot detecta de qué red social viene el lead analizando el texto del primer mensaje:

- **"prueba gratis"** → Instagram
- **"prueba gratuita"** → TikTok
- Esta métrica se registra automáticamente en Google Sheets.

### Diálogo guiado (máquina de estados en Redis)

```
idle → awaiting_name → awaiting_email → done
```

1. **Trigger:** El usuario envía "Quiero probar Impulso Merval" (o similar). El bot responde pidiendo el nombre.
2. **Nombre:** Valida que no esté vacío, lo guarda en Redis con TTL de 6 horas.
3. **Email:** Solicita el correo electrónico.
4. **Finalización:**
   - Agrega al usuario al grupo de WhatsApp Trial mediante Evolution API (`add_participant_to_group`).
   - Guarda la fila en Google Sheets (teléfono, nombre, email, fecha, origen, estado `Trial0`).
   - Responde con mensaje de bienvenida explicando cómo funciona la prueba.
   - Resetea el estado en Redis.

El sistema es tolerante a fallos: si falla Sheets, igual agrega al grupo; si falla el grupo, igual guarda el lead.

---

## 4. Flujo de Broadcast — Mensajes Programados

El bot de broadcast ejecuta mensajes automáticos a los grupos WhatsApp según un cron semanal y fechas específicas. Usa **APScheduler** con `BlockingScheduler`.

### Mensajes semanales

| Días | Horario | Contenido | Grupo |
|------|---------|-----------|-------|
| Lun–Vie | 09:30 | Saludo matutino + resumen de índices globales (S&P 500, Nasdaq, Dow Jones, VIX, petróleo, oro, soja, bonos USA, Bitcoin, Ethereum) vía **yfinance** + noticia del mercado traducida y resumida por **Gemini 2.5 Flash** desde CNBC | Premium |
| Lun–Vie | 11:02 | Alertas bursátiles EE.UU. (x2) + Argentina (x2) — acciones con recomendación de compra a ≥20% de su máximo histórico, con stop loss y desarmes calculados automáticamente | Revisión |
| Lun–Vie | 15:30 | Cotización del dólar (oficial, tarjeta, mayorista, MEP, CCL, blue, cripto) vía **dolarapi.com** | Premium |
| Vie | 13:30 | Recordatorio de caucionar líquido antes del finde | Premium |
| Mar | 16:00 | Programa de referidos (30 días gratis por invitación) | Premium |
| Mar | 17:30 | Contenido motivacional rotativo (mezcla aleatoria persistente) | Premium |
| Mié | 17:30 | Contenido educativo rotativo (`contenido/miercoles.json`) | Premium |
| Vie | 17:30 | Contenido educativo rotativo (`contenido/viernes.json`) | Premium |
| Jue (semana 3) | 11:00 | Vencimiento mensual de opciones | Premium |

### Mensajes por fecha fija

Avisos de feriados programados para todo el año (ambas bolsas — BYMA y NYSE — con cierres y horarios reducidos). Se disparan una única vez en la fecha indicada.

### Contenido rotativo

Los mensajes de miércoles, viernes y motivacionales se almacenan en archivos JSON (`contenido/miercoles.json`, `contenido/viernes.json`, `contenido/motivacionales.json`). El orden de envío es aleatorio con persistencia de estado en `estado_mensajes.json`. Cuando se agota la lista, se re-mezcla automáticamente.

---

## 5. Flujo CRM — Ciclo de Vida del Cliente

El CRM se ejecuta automáticamente **todos los días a las 9:00 AM ART** mediante APScheduler. Lee el Google Sheets de leads, calcula días transcurridos desde la captura o baja, y aplica transiciones de estado.

### Estados y transiciones

```
Trial0 ──[día 3]──→ Trial3 ──[día 5]──→ Trial5 ──[día 6]──→ Trial6 ──[día 7]──→ Eliminado
                                                                                      │
                                                                                      │[día 22]
                                                                                      ↓
                                                                               Retargeting 15
                                                                                      │
                                                                                      │[día 47]
                                                                                      ↓
                                                                               Retargeting Final

Premium (escudo — no se procesa)

Baja ──[60 días]──→ Baja Final
```

### Reglas de negocio detalladas

| Estado actual | Condición | Acción | Nuevo estado | Mensaje |
|---------------|-----------|--------|-------------|---------|
| Trial0 / Trial 0 | días_captura ≥ 3 | Enviar mensaje privado de check | Trial3 | "¿Cómo venís con la info del grupo?" |
| Trial3 / Trial 3 | días_captura ≥ 5 | Enviar beneficios Premium + link MP | Trial5 | "Tu prueba está en la recta final" |
| Trial5 / Trial 5 | días_captura ≥ 6 | Enviar urgencia últimas 24h | Trial6 | "Últimas 24 horas de prueba" |
| Trial6 / Trial 6 | días_captura ≥ 7 | **Remover del grupo Free** + enviar msg post-expulsión | Eliminado | "El sistema te removió del grupo" |
| Eliminado | días_captura ≥ 22 | Enviar cupón 30% desc. primer mes | Retargeting 15 | Cupón especial de descuento |
| Retargeting 15 | días_captura ≥ 47 | Enviar msg macroeconómico evergreen | Retargeting Final | "El mercado no da respiro" |
| Baja | días_baja ≥ 60 | Enviar propuesta recuperación (precio congelado 3 meses) | Baja Final | "Se te extraña en la comunidad" |
| Premium | *cualquiera* | **Escudo:** no se procesa ni modifica | — | — |
| Baja Final / Retargeting Final / Eliminado Definitivo | *cualquiera* | Terminal, no se vuelve a procesar | — | — |

### Columnas del Google Sheets (Maestro)

| # | Columna | Uso |
|---|---------|-----|
| 1 | Teléfono | Identificador único |
| 2 | Nombre | Del lead |
| 3 | Mail | Capturado en onboarding |
| 4 | Fecha de Captura | Se calculan días transcurridos |
| 5 | Origen | Instagram / TikTok |
| 6 | Estado | Máquina de estados del CRM |
| 7 | Fecha de Baja | Se calculan días desde baja |
| 8 | Motivo Baja | Registro manual del admin |
| 9 | Última Actualización | Timestamp del último cambio |

### Notas importantes

- **Premium** funciona como escudo absoluto: el bot ignora la fila por completo.
- **Bajas:** Al cambiar a Baja, el bot envía un mensaje solicitando feedback (precio, tiempo, etc.) que el admin registra manualmente. 60 días después envía propuesta de recuperación.
- **Expulsión:** Ocurre 30 minutos antes del mensaje de las 9:30, maximizando el impacto psicológico de escasez.
- **Batch update:** Todas las celdas modificadas se actualizan en una sola llamada a `update_cells()` al finalizar el procesamiento.

---

## 6. Mensajes que envía el sistema (resumen)

| Tipo | ¿Qué contiene? | Fuente de datos | ¿A quién? | ¿Cuándo? |
|------|---------------|-----------------|-----------|----------|
| Resumen de índices | S&P 500, Nasdaq, Dow, VIX, petróleo, oro, soja, bonos, Bitcoin, Ethereum con análisis de pulso | yfinance | Premium | Lun–Vie 09:30 |
| Noticia de mercado | Artículo de CNBC traducido y resumido | Gemini + CNBC sitemap | Premium | Lun–Vie 09:30 |
| Cotización del dólar | 7 tipos de dólar (oficial, blue, MEP, CCL, etc.) | dolarapi.com | Premium | Lun–Vie 15:30 |
| Alerta bursátil USA | Acción con stop loss y desarmes | yfinance | Revisión | Lun–Vie 11:02 (x2) |
| Alerta bursátil Argentina | Acción argentina con stop loss y desarmes | yfinance | Revisión | Lun–Vie 11:02 (x2) |
| Contenido rotativo | Educativo / motivacional desde JSON rotativo | contenido/*.json | Premium | Mar/Mié/Vie 17:30 |
| Vencimiento de opciones | Recordatorio mensual | Cálculo de fecha | Premium | Jue semana 3, 11:00 |
| Feriados | Aviso de cierre de bolsas | Fechas fijas | Premium | Fecha específica |
| CRM Trial3 | Check personalizado día 3 | — | Lead (privado) | Automático |
| CRM Trial5 | Beneficios Premium + link MP | — | Lead (privado) | Automático |
| CRM Trial6 | Urgencia últimas 24h | — | Lead (privado) | Automático |
| CRM Eliminado | Post-expulsión + oferta Premium | — | Lead (privado) | Automático |
| CRM Retargeting 15 | Cupón 30% descuento | — | Lead (privado) | Automático |
| CRM Retargeting Final | Mensaje macroeconómico | — | Lead (privado) | Automático |
| CRM Baja Final | Propuesta recuperación precio congelado | — | Lead (privado) | Automático |
| Onboarding | Solicitud nombre → email → bienvenida | — | Lead (privado) | En tiempo real |
