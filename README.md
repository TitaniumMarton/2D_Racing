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
The main menu, settings, save slots, and mode chooser play
`music\main_theme.mp3`; gameplay is silent until a separate gameplay track is
added. Music volume defaults to 20% and can be changed in Settings. The
executable stores its preferences and five save-slot files under
`%LOCALAPPDATA%\2D_Racing`. Source runs use `settings.json` and `savegames\` in
the project folder. Save slots currently store creation metadata; gameplay
progress is not implemented yet.
