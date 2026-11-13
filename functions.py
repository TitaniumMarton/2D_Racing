import json
import math
import os
import sys
from pathlib import Path
import pygame
import yaml

# These are the screen sizes and display modes offered in the settings menu.
RESOLUTIONS = (
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

# Shared colors keep the helper-drawn controls consistent with the main screen.
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

# Resolve bundled assets separately from the writable user preferences file.
ROOT_DIR = Path(__file__).resolve().parent
LOCALISATION_DIR = ROOT_DIR / "localisation"
MUSIC_DIR = ROOT_DIR / "music"
MAIN_THEME_FILE = MUSIC_DIR / "main_theme.mp3"
# Keep settings outside PyInstaller's temporary bundle so user changes persist.
if getattr(sys, "frozen", False):
    settings_directory = Path(
        os.environ.get(
            "LOCALAPPDATA", Path.home() / "AppData" / "Local"
        )
    ) / "2D_Racing"
    SETTINGS_FILE = settings_directory / "settings.json"
else:
    SETTINGS_FILE = ROOT_DIR / "settings.json"
DEFAULT_LANGUAGE = "english"
DEFAULT_DISPLAY_MODE = "windowed"
# Start with quiet music; the settings slider can raise it up to full volume.
BASE_MUSIC_VOLUME = 0.2
DEFAULT_MUSIC_VOLUME = BASE_MUSIC_VOLUME
LOCALISATION_FILES = ("main_menu.yml", "settings.yml", "game.yml")


def Render_Pixel_Text(font, text, color):
    """Render readable text with a pixelated effect at its original dimensions."""
    rendered = font.render(text, False, color)
    pixel_size = (
        max(1, rendered.get_width() // 2),
        max(1, rendered.get_height() // 2),
    )
    reduced = pygame.transform.scale(rendered, pixel_size)
    return pygame.transform.scale(reduced, rendered.get_size())

def Draw_Button(surface, rect, text, font, mouse_position, selected=False):
    """Draw a button with hover feedback, a selection border, and centered text."""
    color = BUTTON_HOVER if rect.collidepoint(mouse_position) else BUTTON
    pygame.draw.rect(surface, color, rect, border_radius=10)
    border_color = ACCENT if selected else (63, 83, 108)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)
    label = Render_Pixel_Text(font, text, WHITE)
    surface.blit(label, label.get_rect(center=rect.center))

def Available_Languages():
    """List languages with every required translation file and require English."""
    languages = sorted(
        folder.name
        for folder in LOCALISATION_DIR.iterdir()
        if folder.is_dir()
        and all((folder / filename).is_file() for filename in LOCALISATION_FILES)
    )
    if DEFAULT_LANGUAGE not in languages:
        raise FileNotFoundError(
            "The English localisation file is missing from {!s}".format(
                LOCALISATION_DIR
            )
        )
    return languages


def Load_Localisation(language):
    """Load the selected language's YAML files and validate their translation values."""
    language_dir = LOCALISATION_DIR / language
    language_key = "l_{}".format(language)
    translations = {}
    for translation_file in sorted(language_dir.glob("*.yml")):
        with translation_file.open(encoding="utf-8") as file:
            data = yaml.safe_load(file)
        if not isinstance(data, dict) or not isinstance(data.get(language_key), dict):
            raise ValueError(
                "Invalid localisation file: {!s}".format(translation_file)
            )
        for key, value in data[language_key].items():
            if not isinstance(value, str):
                raise ValueError(
                    "Localisation value {!r} in {!s} must be a string".format(
                        key, translation_file
                    )
                )
            translations[key] = value
    return translations

def Validate_Music_Volume(volume):
    """Validate a 0-to-1 music level and return it as a float."""
    if (
        isinstance(volume, bool)
        or not isinstance(volume, (int, float))
        or not math.isfinite(volume)
        or not 0 <= volume <= 1
    ):
        raise ValueError("The saved music volume must be between 0 and 1")
    return float(volume)


def Load_Preferences(languages):
    """Load display, language, and volume preferences, using defaults when absent."""
    if not SETTINGS_FILE.exists():
        return 0, DEFAULT_LANGUAGE, DEFAULT_DISPLAY_MODE, DEFAULT_MUSIC_VOLUME

    with SETTINGS_FILE.open(encoding="utf-8") as file:
        preferences = json.load(file)
    if not isinstance(preferences, dict):
        raise ValueError("The settings file must contain a JSON object")

    resolution = tuple(preferences.get("resolution", RESOLUTIONS[0]))
    language = preferences.get("language", DEFAULT_LANGUAGE)
    display_mode = preferences.get("display_mode", DEFAULT_DISPLAY_MODE)
    music_volume = Validate_Music_Volume(
        preferences.get("music_volume", DEFAULT_MUSIC_VOLUME)
    )
    if resolution not in RESOLUTIONS:
        raise ValueError("The saved resolution is not supported")
    if language not in languages:
        raise ValueError("The saved language is not available")
    if display_mode not in DISPLAY_MODES:
        raise ValueError("The saved display mode is not available")
    return RESOLUTIONS.index(resolution), language, display_mode, music_volume

def Save_Preferences(
    resolution_index,
    language,
    display_mode,
    music_volume=DEFAULT_MUSIC_VOLUME,
):
    """Write the selected resolution, language, display mode, and volume to JSON."""
    music_volume = Validate_Music_Volume(music_volume)
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "resolution": list(RESOLUTIONS[resolution_index]),
                "language": language,
                "display_mode": display_mode,
                "music_volume": music_volume,
            },
            file,
            indent=2,
        )
        file.write("\n")


def Set_Music_Volume(volume):
    """Apply a validated 0-to-1 level to the currently loaded music track."""
    pygame.mixer.music.set_volume(Validate_Music_Volume(volume))


def Fit_Resolution_To_Desktop(resolution):
    """Shrink a requested window resolution to fit within the desktop margins."""
    desktop_sizes = pygame.display.get_desktop_sizes()
    if not desktop_sizes:
        return resolution

    desktop_width, desktop_height = desktop_sizes[0]
    return (
        min(resolution[0], max(1, desktop_width - 32)),
        min(resolution[1], max(1, desktop_height - 64)),
    )

def Get_Display_Mode_Settings(display_mode, resolution):
    """Choose the Pygame size and flags for fullscreen, borderless, or windowed mode."""
    if display_mode == "fullscreen":
        return resolution, pygame.FULLSCREEN
    if display_mode == "borderless":
        desktop_sizes = pygame.display.get_desktop_sizes()
        if not desktop_sizes:
            raise RuntimeError("Could not determine the desktop size")
        return desktop_sizes[0], pygame.NOFRAME
    if display_mode == "windowed":
        return Fit_Resolution_To_Desktop(resolution), 0
    raise ValueError("Unsupported display mode: {!r}".format(display_mode))