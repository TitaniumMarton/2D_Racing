import json
import sys
from pathlib import Path
import pygame
import yaml

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

# Color definitions/used both in main.py and functions.py but kept separate to minimize possible import issues
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

# Path definitions for the root directory, localisation files, used in both main.py and functions.py but kept separate to minimize possible import issues
ROOT_DIR = Path(__file__).resolve().parent
LOCALISATION_DIR = ROOT_DIR / "localisation"
SETTINGS_FILE = ROOT_DIR / "settings.json"
DEFAULT_LANGUAGE = "english"
DEFAULT_DISPLAY_MODE = "windowed"
LOCALISATION_FILES = ("main_menu.yml", "settings.yml", "game.yml")


def render_pixel_text(font, text, color):
    rendered = font.render(text, False, color)
    pixel_size = (
        max(1, rendered.get_width() // 2),
        max(1, rendered.get_height() // 2),
    )
    reduced = pygame.transform.scale(rendered, pixel_size)
    return pygame.transform.scale(reduced, rendered.get_size())

def draw_button(surface, rect, text, font, mouse_position, selected=False):
    color = BUTTON_HOVER if rect.collidepoint(mouse_position) else BUTTON
    pygame.draw.rect(surface, color, rect, border_radius=10)
    border_color = ACCENT if selected else (63, 83, 108)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)
    label = render_pixel_text(font, text, WHITE)
    surface.blit(label, label.get_rect(center=rect.center))

def available_languages():
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


def load_localisation(language):
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

def load_preferences(languages):
    if not SETTINGS_FILE.exists():
        return 0, DEFAULT_LANGUAGE, DEFAULT_DISPLAY_MODE

    with SETTINGS_FILE.open(encoding="utf-8") as file:
        preferences = json.load(file)
    if not isinstance(preferences, dict):
        raise ValueError("The settings file must contain a JSON object")

    resolution = tuple(preferences.get("resolution", RESOLUTIONS[0]))
    language = preferences.get("language", DEFAULT_LANGUAGE)
    display_mode = preferences.get("display_mode", DEFAULT_DISPLAY_MODE)
    if resolution not in RESOLUTIONS:
        raise ValueError("The saved resolution is not supported")
    if language not in languages:
        raise ValueError("The saved language is not available")
    if display_mode not in DISPLAY_MODES:
        raise ValueError("The saved display mode is not available")
    return RESOLUTIONS.index(resolution), language, display_mode

def save_preferences(resolution_index, language, display_mode):
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "resolution": list(RESOLUTIONS[resolution_index]),
                "language": language,
                "display_mode": display_mode,
            },
            file,
            indent=2,
        )
        file.write("\n")

def fit_resolution_to_desktop(resolution):
    desktop_sizes = pygame.display.get_desktop_sizes()
    if not desktop_sizes:
        return resolution

    desktop_width, desktop_height = desktop_sizes[0]
    return (
        min(resolution[0], max(1, desktop_width - 32)),
        min(resolution[1], max(1, desktop_height - 64)),
    )

def get_display_mode_settings(display_mode, resolution):
    if display_mode == "fullscreen":
        return resolution, pygame.FULLSCREEN
    if display_mode == "borderless":
        desktop_sizes = pygame.display.get_desktop_sizes()
        if not desktop_sizes:
            raise RuntimeError("Could not determine the desktop size")
        return desktop_sizes[0], pygame.NOFRAME
    if display_mode == "windowed":
        return fit_resolution_to_desktop(resolution), 0
    raise ValueError("Unsupported display mode: {!r}".format(display_mode))