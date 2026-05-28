@echo off
echo ====================================================
echo [AUTOBOT] Esperando a que Docker Desktop se inicie...
echo ====================================================

:check_docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 5 /nobreak >nul
    goto check_docker
)

echo [AUTOBOT] Docker esta activo. Iniciando proyecto...
cd /d "C:\Users\tarriola\Desktop\Proyectos\impulso_evo"
docker compose up -d --build

echo [AUTOBOT] Proyecto impulso_evo levantado con exito.
timeout /t 10
exit