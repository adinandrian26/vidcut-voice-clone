@echo off
REM VidCut Desktop: nyalakan layanan + buka software (2 langkah jadi 1 klik).
cd /d "%~dp0.."
start "VidCut Backend" python -m uvicorn app.main:app --host 127.0.0.1 --port 8520
echo Menunggu layanan siap...
timeout /t 10 >nul
python -m desktop.vidcut_desktop
