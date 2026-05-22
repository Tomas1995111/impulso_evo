# Impulso Evo

Bot automatizado para envío de mensajes en WhatsApp con alertas de mercado, cotizaciones y mensajes programados.

## 🚀 Instalación Rápida

### 1️⃣ Clonar el repositorio
```bash
git clone <tu-repo>
cd impulso_evo
```

### 2️⃣ Configurar credenciales

El proyecto requiere dos archivos de configuración con credenciales (NO se suben a git por seguridad):

#### **Archivo `.env`** (raíz del proyecto)
```bash
# Copia desde el template
cp .env.example .env

# Edita y completa con tus valores
# EVOLUTION_API_KEY, GEMINI_API_KEY, SHEET_ID, etc.
nano .env
```

**Dónde obtener cada valor:**
- **EVOLUTION_API_KEY**: Evolution API dashboard
- **GEMINI_API_KEY**: Google Cloud Console > API Keys
- **SHEET_ID**: URL de tu Google Sheet (ve la parte del ID)
- **Grupos**: Ejecuta `python grupos.py` (ver más abajo)

#### **Archivo `mensajes/credenciales.json`** (credencial de Google)
```bash
# Copia desde el template
cp mensajes/credenciales.example.json mensajes/credenciales.json

# Edita con tu JSON de service account de Google Cloud
nano mensajes/credenciales.json
```

**Dónde obtener:**
1. Google Cloud Console > Service Accounts
2. Crea una nueva service account o usa una existente
3. Descarga el JSON completo
4. Reemplaza el contenido en `mensajes/credenciales.json`

### 3️⃣ Ejecutar el proyecto
```bash
# Construir e iniciar contenedores
docker compose up -d --build

# Iniciar sin reconstruir
docker compose up -d

# Ver logs en tiempo real
docker logs -f impulso_bot_programador

# Detener contenedores
docker compose down
```

## 📋 Comandos útiles

### Ver IDs de grupos de WhatsApp
```bash
docker compose exec bot_programador python grupos.py
```

### Ver logs completos
```bash
docker logs -f impulso_bot_programador
```

## 🔐 Gestión de Secretos - Mejores Prácticas

### ❌ NO HAGAS:
- ❌ Nunca subes `.env` o `mensajes/credenciales.json` a git
- ❌ No compartas tus credenciales por email o Slack
- ❌ No dejes las keys visibles en capturas de pantalla

### ✅ SÍ HAZE:
- ✅ Mantén `.env` y credenciales solo en local
- ✅ Si comprometes una key, regenerala inmediatamente
- ✅ Usa archivos `.example` como templates
- ✅ Documenta en el `.example` qué va en cada campo

### 🔄 Si se te rompe la PC o cambias de máquina:

1. **Clona el proyecto:**
   ```bash
   git clone <tu-repo>
   cd impulso_evo
   ```

2. **Copia los archivos de configuración:**
   ```bash
   cp .env.example .env
   cp mensajes/credenciales.example.json mensajes/credenciales.json
   ```

3. **Completa con tus valores:**
   - Tienes los `.example` como referencia
   - Las keys están guardadas en:
     - 🔐 Gestor de contraseñas (1Password, Bitwarden, LastPass, etc.)
     - 💾 Backup seguro en la nube (Google Drive, OneDrive encriptado)
     - 📄 Archivo cifrado separado (no en este repo)

4. **Inicia el proyecto:**
   ```bash
   docker compose up -d --build
   ```

## 📦 Estructura de archivos importantes

```
impulso_evo/
├── .env                          ← NO SUBIR A GIT (tus credenciales)
├── .env.example                  ← ✅ Sube a git (template)
├── mensajes/
│   ├── credenciales.json         ← NO SUBIR A GIT (Google service account)
│   └── credenciales.example.json ← ✅ Sube a git (template)
├── docker-compose.yml
└── automatizarMensajes.py
```

El `.gitignore` ya está configurado para ignorar estos archivos automáticamente.


