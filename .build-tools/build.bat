@echo off
setlocal
cd /d "%~dp0.."

python -m PyInstaller --clean --noconfirm --onefile --windowed --name 2D_Racing --icon "%~dp0..\gfx\icon.png" --add-data "%~dp0..\localisation;localisation" --distpath . --workpath build --specpath build "%~dp0..\main.py"
if errorlevel 1 exit /b %errorlevel%

echo Built 2D_Racing.exe
