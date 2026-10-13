@echo off
setlocal
cd /d "%~dp0"
echo =====================================
echo           TRIPGENIE STARTER
echo =====================================
if not exist app.py (
  echo ERROR: app.py not found. Open the inner TripGenie_Project folder.
  pause
  exit /b 1
)
echo Installing required Python packages...
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check the error above.
  pause
  exit /b 1
)
echo Preparing recommendation model...
py train_model.py
if errorlevel 1 echo WARNING: Model training failed; the app may rebuild it at startup.
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"
echo Starting Flask. Keep this window open while using TripGenie.
py app.py
pause
