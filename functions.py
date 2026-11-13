import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
import pygame
import yaml

# These are the screen sizes and display modes offered in the settings menu.
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
    USER_DATA_DIR = Path(
        os.environ.get(
            "LOCALAPPDATA", Path.home() / "AppData" / "Local"
        )
    ) / "2D_Racing"
else:
    USER_DATA_DIR = ROOT_DIR
SETTINGS_FILE = USER_DATA_DIR / "settings.json"
SAVE_GAMES_DIR = USER_DATA_DIR / "savegames"
SAVE_GAMES_FILE = SAVE_GAMES_DIR / "savegames.json"
SAVE_SLOT_COUNT = 5
DEFAULT_LANGUAGE = "english"
DEFAULT_DISPLAY_MODE = "windowed"
# Start with quiet music; the settings slider can raise it up to full volume.
BASE_MUSIC_VOLUME = 0.2
DEFAULT_MUSIC_VOLUME = BASE_MUSIC_VOLUME
LOCALISATION_FILES = ("main_menu.yml", "settings.yml", "game.yml")
CHARACTER_DIR = ROOT_DIR / "gfx" / "characters"
DIFFICULTY_LEVELS = (
    "very_easy",
    "easy",
    "medium",
    "hard",
    "max_verstappen",
)


def Render_Pixel_Text(font, text, color):
    """Render readable text with a pixelated effect at its original dimensions."""
    rendered = font.render(text, False, color)
    pixel_size = (
        max(1, rendered.get_width() // 2),
        max(1, rendered.get_height() // 2),
    )
    reduced = pygame.transform.scale(rendered, pixel_size)
    return pygame.transform.scale(reduced, rendered.get_size())


def Load_Character_Images():
    """Load the available team characters and return their filename keys."""
    for character_directory in (CHARACTER_DIR, ROOT_DIR / "gfx"):
        if not character_directory.is_dir():
            continue
        character_files = sorted(
            (
                path
                for path in character_directory.glob("character_*.png")
                if path.stem != "character_outline"
            ),
            key=lambda path: path.name.lower(),
        )
        if character_files:
            return tuple(
                (
                    character_file.stem[len("character_"):],
                    pygame.image.load(str(character_file)).convert_alpha(),
                )
                for character_file in character_files
            )
    raise FileNotFoundError(
        "No character images were found in {!s} or {!s}".format(
            CHARACTER_DIR, ROOT_DIR / "gfx"
        )
    )


def Get_Localised_Team_Name(character_name, translations):
    """Return a team's localized label for its character filename key."""
    return translations["game_team_{}".format(character_name)]


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


def Get_Save_Slot_Path(slot_number):
    """Return the shared data-file path after validating a save slot number."""
    if (
        isinstance(slot_number, bool)
        or not isinstance(slot_number, int)
        or not 1 <= slot_number <= SAVE_SLOT_COUNT
    ):
        raise ValueError("The save slot number must be between 1 and 5")
    return SAVE_GAMES_FILE


def _Validate_Save_Slot(save_data, slot_number):
    if (
        not isinstance(save_data, dict)
        or isinstance(save_data.get("version"), bool)
        or not isinstance(save_data.get("version"), int)
        or save_data.get("version") != 1
        or not isinstance(save_data.get("slot"), int)
        or isinstance(save_data.get("slot"), bool)
        or save_data.get("slot") != slot_number
        or not isinstance(save_data.get("created_at"), str)
    ):
        raise ValueError("The data in save slot {} is invalid".format(slot_number))
    return save_data


def _Write_Save_Slots(save_slots):
    SAVE_GAMES_DIR.mkdir(parents=True, exist_ok=True)
    with SAVE_GAMES_FILE.open("w", encoding="utf-8") as file:
        json.dump({"version": 1, "slots": save_slots}, file, indent=2)
        file.write("\n")


def Load_Save_Slots():
    """Load all slots from one file, migrating older per-slot files if present."""
    SAVE_GAMES_DIR.mkdir(parents=True, exist_ok=True)
    if SAVE_GAMES_FILE.is_file():
        with SAVE_GAMES_FILE.open(encoding="utf-8") as file:
            save_data = json.load(file)
        if (
            not isinstance(save_data, dict)
            or isinstance(save_data.get("version"), bool)
            or not isinstance(save_data.get("version"), int)
            or save_data.get("version") != 1
            or not isinstance(save_data.get("slots"), list)
            or len(save_data["slots"]) != SAVE_SLOT_COUNT
        ):
            raise ValueError("The save games file is invalid")
        save_slots = [
            None
            if slot_data is None
            else _Validate_Save_Slot(slot_data, slot_number)
            for slot_number, slot_data in enumerate(save_data["slots"], start=1)
        ]
    else:
        save_slots = [None] * SAVE_SLOT_COUNT

    migrated_files = []
    for slot_number in range(1, SAVE_SLOT_COUNT + 1):
        legacy_path = SAVE_GAMES_DIR / "slot_{}.json".format(slot_number)
        if not legacy_path.is_file() or save_slots[slot_number - 1] is not None:
            continue
        with legacy_path.open(encoding="utf-8") as file:
            legacy_data = json.load(file)
        save_slots[slot_number - 1] = _Validate_Save_Slot(
            legacy_data, slot_number
        )
        migrated_files.append(legacy_path)

    if not SAVE_GAMES_FILE.is_file() or migrated_files:
        _Write_Save_Slots(save_slots)
        for legacy_path in migrated_files:
            legacy_path.unlink()
    return save_slots


def Load_Save_Slot(slot_number):
    """Load and validate one save slot, returning None when it is empty."""
    Get_Save_Slot_Path(slot_number)
    return Load_Save_Slots()[slot_number - 1]


def Create_Save_Slot(slot_number):
    """Create a new save-slot record without overwriting an existing slot."""
    Get_Save_Slot_Path(slot_number)
    save_slots = Load_Save_Slots()
    if save_slots[slot_number - 1] is not None:
        raise FileExistsError(
            "Save slot {} already exists".format(slot_number)
        )
    save_data = {
        "version": 1,
        "slot": slot_number,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    save_slots[slot_number - 1] = save_data
    _Write_Save_Slots(save_slots)
    return save_data


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