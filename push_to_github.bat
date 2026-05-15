@echo off
cd /d "c:\Users\User\OneDrive\Documents\Pothole Detection"

echo ============================================
echo   PotholeNet GitHub Push Script
echo ============================================
echo.
echo Step 1: Creating GitHub repo...
echo.

REM Try gh first
gh auth login --web -p https
gh repo create PotholeNet --public --source=. --push --description "Crowdsourced road hazard intelligence - ESP32-CAM + YOLOv8 + Roboflow + FastAPI + React"

if %errorlevel% neq 0 (
  echo.
  echo gh CLI didn't work. Using plain git instead.
  echo.
  echo IMPORTANT: Go to https://github.com/new and create a repo called "PotholeNet"
  echo Then come back here and press any key...
  pause
  git remote add origin https://github.com/Srinivaas-only/PotholeNet.git
  git branch -M main
  git push -u origin main
)

echo.
echo === DONE! Check your GitHub repo. ===
pause