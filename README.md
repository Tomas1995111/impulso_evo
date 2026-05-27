# Impulso Evo

Bot de WhatsApp para envío de mensajes programados (mercado, cotizaciones, alertas).

## Clonar e instalar

```bash
git clone <tu-repo>
cd impulso_evo
```

### Archivos que tenés que tener (no vienen en git)

| Archivo | Cómo obtenerlo |
|---------|----------------|
| `.env` | `cp .env.example .env` y completar con tus valores |
| `mensajes/credenciales.json` | `cp mensajes/credenciales.example.json mensajes/credenciales.json` y pegar el JSON de tu service account de Google Cloud |

Guardá tus keys en un gestor de contraseñas o backup seguro. No subas `.env` ni `credenciales.json` a git.

### Levantar el proyecto

```bash
docker compose up -d --build
```

Para iniciar sin reconstruir:

```bash
docker compose up -d
```

Para detener:

```bash
docker compose down
```

## Ver logs

```bash
docker logs -f impulso_bot
```

## Webhook (Evolution → Inbound)

Levanta el inbound con el compose y configurá en la UI de Evolution el webhook para `MESSAGES_UPSERT` con esta URL:

- `http://bot_inbound:8000/messages-upsert`

Si tu UI te pide una URL base “global” (sin path), también sirve:

- `http://bot_inbound:8000`

porque el servicio expone `/messages-upsert` y `/webhook/messages-upsert`.

## Ver grupos de WhatsApp

Con el proyecto levantado:

```bash
docker compose exec bot python grupos.py
```

Copiá los IDs `@g.us` en tu `.env` (`GRUPO_DEFAULT`, `GRUPO_PREMIUM`, etc.).
