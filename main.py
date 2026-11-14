#this version uses the idea i originaly wanted to ipmlelent but it doesnt solve the main function issue only hides it.

#this works the same way but the definiton is stored at functions.py

# 56 lines

from pathlib import Path
from functions import (Main)


RESOLUTIONS = (
    (1920, 1200),
    (1920, 1080),
    (3840, 2160),
    (2560, 1440),
    (1680, 1050),
    (1600, 900),
    (1440, 900),
    (1366, 768),
    (1360, 768),
    (1280, 1024),
    (1280, 800),
    (1280, 720),
    (1024, 768),
    (800, 600),
)
DISPLAY_MODES = ("fullscreen", "borderless", "windowed")
MENU_TRANSITION_DURATION_MS = 180

# Shared colors keep the screens and helper-drawn controls visually consistent.
BACKGROUND = (12, 18, 30)
PANEL = (22, 32, 49)
BUTTON = (35, 51, 73)
BUTTON_HOVER = (51, 75, 105)
MUTED = (155, 171, 190)
ACCENT = (86, 220, 166)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# Locate files relative to the source or PyInstaller bundle.
ROOT_DIR = Path(__file__).resolve().parent
LOCALISATION_DIR = ROOT_DIR / "localisation"
SETTINGS_FILE = ROOT_DIR / "settings.json"
DEFAULT_LANGUAGE = "english"
DEFAULT_DISPLAY_MODE = "windowed"
LOCALISATION_FILES = ("main_menu.yml", "settings.yml", "game.yml")


# Start the game only when this file is run as the program entry point.
if __name__ == "__main__":
    Main()
