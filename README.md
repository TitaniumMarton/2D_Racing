# 2D Racing

## Run from source

Install the game dependencies and start the game:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Build a Windows executable

Install the build dependencies and run the Windows build script:

```powershell
python -m pip install -r requirements-build.txt
.\.build-tools\build.bat
```

The windowed, single-file executable is created at `2D_Racing.exe`. It
includes the localisation and music files and does not open a command prompt.
The menu plays `music\main_theme.mp3`; gameplay is silent until a separate
gameplay track is added. Music volume defaults to 20% and can be changed in
Settings. The executable stores its preferences under `%LOCALAPPDATA%\2D_Racing`.
