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

MENU_TRANSITION_DURATION_MS = 180

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



def Main():
    """Initialize Pygame and run the menu, settings, and game loop."""
    # Initialize Pygame and load saved display, language, and music settings.
    pygame.init()

    languages = Available_Languages()
    resolution_index, language, display_mode, music_volume = Load_Preferences(languages)

    # Prepare frame timing, fonts, current screen state, and pending settings.
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 100)
    button_font = pygame.font.Font(None, 42)
    small_font = pygame.font.Font(None, 28)
    mode_font = pygame.font.Font(None, 24)
    state = "menu"
    running = True
    selected_save_slot = None
    selected_mode = None
    selected_difficulty = None
    selected_team_index = 0
    team_confirmed = False
    save_slots = []
    save_slots_error = None
    transition_started_at = None
    pending_resolution_index = resolution_index
    pending_language = language
    pending_display_mode = display_mode
    pending_music_volume = music_volume
    volume_slider_dragging = False
    confirm_previous_resolution_index = resolution_index
    confirm_previous_display_mode = display_mode
    resolution_confirm_deadline = 0
    localisations = {locale: Load_Localisation(locale) for locale in languages}

    if any("language_name" not in data for data in localisations.values()):
        raise ValueError("Each localisation must define a language_name")
    
    # Build language labels before creating the first display surface.
    language_names = {
        locale: data["language_name"]
        for locale, data in localisations.items()
    }
    translations = localisations[language]
    try:
        save_slots = Load_Save_Slots()
    except (OSError, ValueError) as error:
        print("Could not load save slots: {}".format(error), file=sys.stderr)
        save_slots = [None] * SAVE_SLOT_COUNT
        save_slots_error = translations["game_save_slot_error"]
    screen_size, screen_flags = Get_Display_Mode_Settings(
        display_mode, RESOLUTIONS[resolution_index]
    )
    screen = pygame.display.set_mode(screen_size, screen_flags)
    pygame.display.set_caption("2D Racing")
    team_characters = Load_Character_Images()
    team_image_cache = {}
    chooser_title_fonts = {}
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()
    pygame.mixer.music.load(str(MAIN_THEME_FILE))
    Set_Music_Volume(music_volume)
    # Keep the theme looping through the main menu, settings, and mode selection.
    pygame.mixer.music.play(-1)

    # Prepare the translated labels and dropdown state used by the settings screen.
    display_mode_labels = {
        mode: translations["display_mode_{}".format(mode)]
        for mode in DISPLAY_MODES
    }
    dropdown_open = None
    dropdown_scroll = 0
    settings_message = None

    while running:
        previous_state = state
        # Accept the pending resolution when its confirmation timer expires.
        if (
            state == "confirm_resolution"
            and pygame.time.get_ticks() >= resolution_confirm_deadline
        ):
            try:
                Save_Preferences(
                    pending_resolution_index,
                    language,
                    pending_display_mode,
                    pending_music_volume,
                )
            except OSError as error:
                print("Could not save settings: {}".format(error), file=sys.stderr)
                screen_size, screen_flags = Get_Display_Mode_Settings(
                    confirm_previous_display_mode,
                    RESOLUTIONS[confirm_previous_resolution_index],
                )
                screen = pygame.display.set_mode(screen_size, screen_flags)
                resolution_index = confirm_previous_resolution_index
                display_mode = confirm_previous_display_mode
                pending_resolution_index = resolution_index
                pending_display_mode = display_mode
                pending_music_volume = music_volume
                Set_Music_Volume(music_volume)
                settings_message = translations["settings_save_failed"]
            else:
                resolution_index = pending_resolution_index
                display_mode = pending_display_mode
                music_volume = pending_music_volume
                settings_message = translations["settings_applied"]
            state = "settings"

        # Recalculate control positions so the interface scales with the window.
        width, height = screen.get_size()
        center_x = width // 2
        scale = min(width / 1920, height / 1200)
        chooser_title_size = max(36, min(100, int(width * 0.055)))
        if chooser_title_size not in chooser_title_fonts:
            chooser_title_fonts[chooser_title_size] = pygame.font.Font(
                None, chooser_title_size
            )
        chooser_title_font = chooser_title_fonts[chooser_title_size]
        button_width = min(int(width * 0.42), 520)
        button_height = max(52, int(72 * scale))
        selector_width = min(int(width * 0.48), 520)
        selector_height = max(40, int(62 * scale))
        selector_x = center_x - selector_width // 2
        
        resolution_selector = pygame.Rect(
            selector_x, int(height * 0.29), selector_width, selector_height)
        
        language_selector = pygame.Rect(
            selector_x, int(height * 0.60), selector_width, selector_height
        )
        music_volume_slider_rect = pygame.Rect(
            selector_x,
            int(height * 0.73),
            selector_width,
            max(32, int(48 * scale)),
        )
        music_volume_track = pygame.Rect(
            music_volume_slider_rect.x + 12,
            music_volume_slider_rect.centery - 4,
            music_volume_slider_rect.width - 24,
            8,
        )
        mode_group_width = min(int(width * 0.78), 900)
        mode_gap = max(6, int(12 * scale))
        mode_button_width = (mode_group_width - 2 * mode_gap) // len(DISPLAY_MODES)
        mode_button_height = max(36, int(52 * scale))
        mode_button_x = center_x - mode_group_width // 2
        mode_buttons = {
            mode: pygame.Rect(
                mode_button_x + index * (mode_button_width + mode_gap),
                int(height * 0.44),
                mode_button_width,
                mode_button_height,
            )
            for index, mode in enumerate(DISPLAY_MODES)
        }
        card_gap = max(16, int(28 * scale))
        card_width = min(
            int(width * 0.38),
            max(180, int(480 * scale)),
        )
        card_height = max(120, int(220 * scale))
        card_left = center_x - (card_width * 2 + card_gap) // 2
        card_top = int(height * 0.34)
        mode_cards = {
            "carrier": pygame.Rect(card_left, card_top, card_width, card_height),
            "sandbox": pygame.Rect(
                card_left + card_width + card_gap,
                card_top,
                card_width,
                card_height,
            ),
        }
        difficulty_button_width = min(int(width * 0.68), 700)
        difficulty_button_height = max(48, int(64 * scale))
        difficulty_button_gap = max(8, int(12 * scale))
        difficulty_buttons = {
            difficulty: pygame.Rect(
                center_x - difficulty_button_width // 2,
                int(height * 0.30)
                + index * (difficulty_button_height + difficulty_button_gap),
                difficulty_button_width,
                difficulty_button_height,
            )
            for index, difficulty in enumerate(DIFFICULTY_LEVELS)
        }
        team_arrow_size = max(56, int(72 * scale))
        team_arrow_gap = max(16, int(28 * scale))
        team_image_max_width = max(1, int(width * 0.30))
        team_image_max_height = max(1, int(height * 0.38))
        team_arrow_y = int(height * 0.50)
        team_arrow_left = pygame.Rect(
            center_x - team_image_max_width // 2 - team_arrow_gap - team_arrow_size,
            team_arrow_y - team_arrow_size // 2,
            team_arrow_size,
            team_arrow_size,
        )
        team_arrow_right = pygame.Rect(
            center_x + team_image_max_width // 2 + team_arrow_gap,
            team_arrow_y - team_arrow_size // 2,
            team_arrow_size,
            team_arrow_size,
        )
        row_height = max(32, int(40 * scale))
        footer_height = max(48, int(60 * scale))
        footer_margin = max(24, int(min(width, height) * 0.06))
        footer_y = height - footer_height - footer_margin
        footer_width = min(
            260,
            max(180, int(width * 0.32)),
            (width - 3 * footer_margin) // 2,
        )
        back_button = pygame.Rect(
            footer_margin, footer_y, footer_width, footer_height
        )
        apply_button = pygame.Rect(
            width - footer_margin - footer_width,
            footer_y,
            footer_width,
            footer_height,
        )
        save_slot_button_width = min(int(width * 0.68), 900)
        save_slot_button_height = max(44, int(64 * scale))
        save_slot_button_gap = max(8, int(12 * scale))
        save_slot_buttons = tuple(
            pygame.Rect(
                center_x - save_slot_button_width // 2,
                int(height * 0.24)
                + slot_index * (save_slot_button_height + save_slot_button_gap),
                save_slot_button_width,
                save_slot_button_height,
            )
            for slot_index in range(SAVE_SLOT_COUNT)
        )

        start_button = pygame.Rect(
            0, int(height * 0.56), button_width, button_height
        )
        start_button.centerx = center_x
        settings_button = start_button.copy()
        settings_button.y = int(height * 0.56) + button_height + max(16, int(20 * scale))
        quit_button = settings_button.copy()
        quit_button.y = settings_button.bottom + max(16, int(20 * scale))

        dropdown_selector = (
            resolution_selector if dropdown_open == "resolution" else
            language_selector if dropdown_open == "language" else None
        )
        if dropdown_open == "resolution":
            dropdown_options = [
                "{} x {}".format(*resolution) for resolution in RESOLUTIONS
            ]
        elif dropdown_open == "language":
            dropdown_options = [language_names[item] for item in languages]
        else:
            dropdown_options = []
        dropdown_max_rows = (
            max(1, min(6, (footer_y - dropdown_selector.bottom) // row_height))
            if dropdown_selector is not None
            else 0
        )
        dropdown_scroll = min(
            dropdown_scroll, max(0, len(dropdown_options) - dropdown_max_rows)
        )
        dropdown_rect = (
            pygame.Rect(
                dropdown_selector.x,
                dropdown_selector.bottom,
                dropdown_selector.width,
                min(len(dropdown_options), dropdown_max_rows) * row_height,
            )
            if dropdown_selector is not None
            else None
        )

        # Handle navigation, dropdowns, display settings, and volume adjustments.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state == "confirm_resolution" and event.key == pygame.K_RETURN:
                    screen_size, screen_flags = Get_Display_Mode_Settings(
                        confirm_previous_display_mode,
                        RESOLUTIONS[confirm_previous_resolution_index],
                    )
                    screen = pygame.display.set_mode(screen_size, screen_flags)
                    resolution_index = confirm_previous_resolution_index
                    display_mode = confirm_previous_display_mode
                    pending_resolution_index = resolution_index
                    pending_display_mode = display_mode
                    state = "settings"
                    settings_message = translations["settings_resolution_reverted"]
                elif event.key == pygame.K_ESCAPE and state == "mode_chooser":
                    state = "save_slots"
                elif event.key == pygame.K_ESCAPE and state == "difficulty_chooser":
                    state = "mode_chooser"
                elif event.key == pygame.K_ESCAPE and state == "team_chooser":
                    state = "difficulty_chooser"
                elif event.key == pygame.K_ESCAPE and state == "save_slots":
                    state = "menu"
                elif state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    state = "save_slots"
            elif event.type == pygame.MOUSEWHEEL and dropdown_rect is not None:
                if dropdown_rect.collidepoint(pygame.mouse.get_pos()):
                    dropdown_scroll = max(
                        0,
                        min(
                            dropdown_scroll - event.y,
                            len(dropdown_options) - dropdown_max_rows,
                        ),
                    )
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                volume_slider_dragging = False
            elif (
                event.type == pygame.MOUSEMOTION
                and volume_slider_dragging
                and state == "settings"
            ):
                pending_music_volume = max(
                    0.0,
                    min(
                        1.0,
                        (event.pos[0] - music_volume_track.left)
                        / music_volume_track.width,
                    ),
                )
                Set_Music_Volume(pending_music_volume)
                settings_message = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "menu":
                    if start_button.collidepoint(event.pos):
                        state = "save_slots"
                    elif settings_button.collidepoint(event.pos):
                        state = "settings"
                        pending_resolution_index = resolution_index
                        pending_language = language
                        pending_display_mode = display_mode
                        pending_music_volume = music_volume
                        volume_slider_dragging = False
                        settings_message = None
                    elif quit_button.collidepoint(event.pos):
                        running = False
                elif state == "settings":
                    if music_volume_slider_rect.collidepoint(event.pos):
                        volume_slider_dragging = True
                        dropdown_open = None
                        pending_music_volume = max(
                            0.0,
                            min(
                                1.0,
                                (event.pos[0] - music_volume_track.left)
                                / music_volume_track.width,
                            ),
                        )
                        Set_Music_Volume(pending_music_volume)
                        settings_message = None
                    elif dropdown_rect is not None and dropdown_rect.collidepoint(event.pos):
                        option_index = dropdown_scroll + (
                            event.pos[1] - dropdown_rect.y
                        ) // row_height
                        if dropdown_open == "resolution":
                            pending_resolution_index = option_index
                        else:
                            pending_language = languages[option_index]
                        dropdown_open = None
                        settings_message = None
                    elif dropdown_open is not None and not (
                        resolution_selector.collidepoint(event.pos)
                        or language_selector.collidepoint(event.pos)
                    ):
                        dropdown_open = None
                    if resolution_selector.collidepoint(event.pos):
                        dropdown_open = (
                            None if dropdown_open == "resolution" else "resolution"
                        )
                        dropdown_scroll = 0
                    elif language_selector.collidepoint(event.pos):
                        dropdown_open = (
                            None if dropdown_open == "language" else "language"
                        )
                        dropdown_scroll = 0
                    elif any(
                        button.collidepoint(event.pos)
                        for button in mode_buttons.values()
                    ):
                        pending_display_mode = next(
                            mode
                            for mode, button in mode_buttons.items()
                            if button.collidepoint(event.pos)
                        )
                        settings_message = None
                    elif apply_button.collidepoint(event.pos):
                        resolution_changed = (
                            pending_resolution_index != resolution_index
                        )
                        mode_changed = pending_display_mode != display_mode
                        if resolution_changed or mode_changed:
                            try:
                                Save_Preferences(
                                    resolution_index,
                                    pending_language,
                                    display_mode,
                                    music_volume,
                                )
                            except OSError as error:
                                print(
                                    "Could not save settings: {}".format(error),
                                    file=sys.stderr,
                                )
                                settings_message = translations["settings_save_failed"]
                            else:
                                language = pending_language
                                translations = localisations[language]
                                display_mode_labels = {
                                    mode: translations[
                                        "display_mode_{}".format(mode)
                                    ]
                                    for mode in DISPLAY_MODES
                                }
                                pending_language = language
                                screen_size, screen_flags = (
                                    Get_Display_Mode_Settings(
                                        pending_display_mode,
                                        RESOLUTIONS[pending_resolution_index],
                                    )
                                )
                                try:
                                    screen = pygame.display.set_mode(
                                        screen_size, screen_flags
                                    )
                                except pygame.error as error:
                                    print(
                                        "Could not change display settings: {}".format(
                                            error
                                        ),
                                        file=sys.stderr,
                                    )
                                    pending_resolution_index = resolution_index
                                    pending_display_mode = display_mode
                                    settings_message = translations[
                                        "settings_display_failed"
                                    ]
                                else:
                                    if resolution_changed:
                                        confirm_previous_resolution_index = (
                                            resolution_index
                                        )
                                        confirm_previous_display_mode = display_mode
                                        resolution_confirm_deadline = (
                                            pygame.time.get_ticks() + 10000
                                        )
                                        state = "confirm_resolution"
                                        settings_message = None
                                    else:
                                        try:
                                            Save_Preferences(
                                                resolution_index,
                                                language,
                                                pending_display_mode,
                                                pending_music_volume,
                                            )
                                        except OSError as error:
                                            print(
                                                "Could not save settings: {}".format(
                                                    error
                                                ),
                                                file=sys.stderr,
                                            )
                                            old_size, old_flags = (
                                                Get_Display_Mode_Settings(
                                                    display_mode,
                                                    RESOLUTIONS[resolution_index],
                                                )
                                            )
                                            screen = pygame.display.set_mode(
                                                old_size, old_flags
                                            )
                                            pending_display_mode = display_mode
                                            settings_message = translations[
                                                "settings_save_failed"
                                            ]
                                        else:
                                            display_mode = pending_display_mode
                                            music_volume = pending_music_volume
                                            settings_message = translations[
                                                "settings_applied"
                                            ]
                        else:
                            try:
                                Save_Preferences(
                                    resolution_index,
                                    pending_language,
                                    display_mode,
                                    pending_music_volume,
                                )
                            except OSError as error:
                                print(
                                    "Could not save settings: {}".format(error),
                                    file=sys.stderr,
                                )
                                settings_message = translations["settings_save_failed"]
                            else:
                                music_volume = pending_music_volume
                                language = pending_language
                                translations = localisations[language]
                                display_mode_labels = {
                                    mode: translations[
                                        "display_mode_{}".format(mode)
                                    ]
                                    for mode in DISPLAY_MODES
                                }
                                pending_language = language
                                settings_message = translations["settings_applied"]
                    elif back_button.collidepoint(event.pos):
                        state = "menu"
                        pending_music_volume = music_volume
                        Set_Music_Volume(music_volume)
                        volume_slider_dragging = False
                elif state == "save_slots":
                    for slot_index, slot_button in enumerate(save_slot_buttons):
                        if slot_button.collidepoint(event.pos):
                            slot_number = slot_index + 1
                            try:
                                save_slot = Load_Save_Slot(slot_number)
                                if save_slot is None:
                                    save_slot = Create_Save_Slot(slot_number)
                            except (OSError, ValueError) as error:
                                print(
                                    "Could not load save slot {}: {}".format(
                                        slot_number, error
                                    ),
                                    file=sys.stderr,
                                )
                                save_slots_error = translations[
                                    "game_save_slot_error"
                                ]
                            else:
                                save_slots[slot_index] = save_slot
                                selected_save_slot = slot_number
                                save_slots_error = None
                                state = "mode_chooser"
                            break
                elif state == "mode_chooser":
                    for mode, card_rect in mode_cards.items():
                        if card_rect.collidepoint(event.pos):
                            selected_mode = mode
                            selected_difficulty = None
                            team_confirmed = False
                            state = "difficulty_chooser"
                            break
                elif state == "difficulty_chooser":
                    for difficulty, difficulty_rect in difficulty_buttons.items():
                        if difficulty_rect.collidepoint(event.pos):
                            selected_difficulty = difficulty
                            selected_team_index = 0
                            team_confirmed = False
                            state = "team_chooser"
                            break
                    if back_button.collidepoint(event.pos):
                        state = "mode_chooser"
                elif state == "team_chooser":
                    if team_arrow_left.collidepoint(event.pos):
                        selected_team_index = (
                            selected_team_index - 1
                        ) % len(team_characters)
                        team_confirmed = False
                    elif team_arrow_right.collidepoint(event.pos):
                        selected_team_index = (
                            selected_team_index + 1
                        ) % len(team_characters)
                        team_confirmed = False
                    elif back_button.collidepoint(event.pos):
                        state = "difficulty_chooser"
                    elif apply_button.collidepoint(event.pos):
                        team_confirmed = True

        if state != previous_state:
            transition_started_at = pygame.time.get_ticks()

        # Redraw the active screen from its current state.
        mouse_position = pygame.mouse.get_pos()
        screen.fill(BACKGROUND)

        if state == "menu":
            # Show the animated title and the three main navigation buttons.
            title = Render_Pixel_Text(
                title_font, translations["main_menu_title"], WHITE
            )
            title_y = int(height * 0.30 + math.sin(pygame.time.get_ticks() / 1500) * 8)
            screen.blit(title, title.get_rect(center=(center_x, title_y)))
            subtitle = Render_Pixel_Text(
                small_font, translations["main_menu_subtitle"], MUTED
            )
            screen.blit(subtitle, subtitle.get_rect(center=(center_x, int(height * 0.39))))
            Draw_Button(
                screen,
                start_button,
                translations["main_menu_start"],
                button_font,
                mouse_position,
            )
            Draw_Button(
                screen,
                settings_button,
                translations["main_menu_settings"],
                button_font,
                mouse_position,
            )
            Draw_Button(
                screen,
                quit_button,
                translations["main_menu_quit"],
                button_font,
                mouse_position,
            )

        elif state == "confirm_resolution":
            # Show the countdown and instructions for reverting a display change.
            title = Render_Pixel_Text(
                title_font, translations["settings_confirm_resolution"], WHITE
            )
            seconds_left = max(
                0,
                (resolution_confirm_deadline - pygame.time.get_ticks() + 999) // 1000,
            )
            prompt = Render_Pixel_Text(
                small_font,
                translations["settings_press_enter_revert"].format(
                    seconds=seconds_left
                ),
                ACCENT,
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.43))))
            screen.blit(prompt, prompt.get_rect(center=(center_x, int(height * 0.53))))

        elif state == "settings":
            # Draw translated display controls, the music slider, and feedback.
            title = Render_Pixel_Text(
                title_font, translations["settings_title"], WHITE
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.14))))
            resolution_label = Render_Pixel_Text(
                small_font, translations["settings_resolution"], MUTED
            )
            screen.blit(
                resolution_label,
                resolution_label.get_rect(center=(center_x, int(height * 0.25))),
            )
            mode_label = Render_Pixel_Text(
                small_font, translations["settings_display_mode"], MUTED
            )
            screen.blit(
                mode_label,
                mode_label.get_rect(center=(center_x, int(height * 0.41))),
            )
            language_label = Render_Pixel_Text(
                small_font, translations["settings_language"], MUTED
            )
            screen.blit(
                language_label,
                language_label.get_rect(center=(center_x, int(height * 0.56))),
            )
            music_volume_label = Render_Pixel_Text(
                small_font,
                translations["settings_music_volume"].format(
                    percent=int(round(pending_music_volume * 100))
                ),
                MUTED,
            )
            screen.blit(
                music_volume_label,
                music_volume_label.get_rect(center=(center_x, int(height * 0.68))),
            )
            Draw_Button(
                screen,
                resolution_selector,
                "{} x {}    v".format(*RESOLUTIONS[pending_resolution_index]),
                button_font,
                mouse_position,
            )
            Draw_Button(
                screen,
                language_selector,
                "{}    v".format(language_names[pending_language]),
                button_font,
                mouse_position,
            )
            for mode, button in mode_buttons.items():
                Draw_Button(
                    screen,
                    button,
                    display_mode_labels[mode],
                    mode_font,
                    mouse_position,
                    selected=mode == pending_display_mode,
                )
            pygame.draw.rect(
                screen, BUTTON, music_volume_slider_rect, border_radius=10
            )
            pygame.draw.rect(
                screen,
                (63, 83, 108),
                music_volume_slider_rect,
                width=2,
                border_radius=10,
            )
            pygame.draw.rect(
                screen, (63, 83, 108), music_volume_track, border_radius=4
            )
            music_volume_fill = pygame.Rect(
                music_volume_track.x,
                music_volume_track.y,
                int(music_volume_track.width * pending_music_volume),
                music_volume_track.height,
            )
            if music_volume_fill.width > 0:
                pygame.draw.rect(
                    screen, ACCENT, music_volume_fill, border_radius=4
                )
            pygame.draw.circle(
                screen,
                ACCENT,
                (
                    music_volume_track.x
                    + int(music_volume_track.width * pending_music_volume),
                    music_volume_track.centery,
                ),
                max(8, int(12 * scale)),
            )
            Draw_Button(
                screen,
                back_button,
                translations["settings_back"],
                small_font,
                mouse_position,
            )
            Draw_Button(
                screen,
                apply_button,
                translations["settings_apply"],
                small_font,
                mouse_position,
            )
            if settings_message is not None:
                message = Render_Pixel_Text(
                    small_font,
                    settings_message,
                    RED
                    if settings_message
                    in (
                        translations["settings_save_failed"],
                        translations["settings_display_failed"],
                    )
                    else ACCENT,
                )
                screen.blit(
                    message,
                    message.get_rect(center=(center_x, footer_y - row_height)),
                )
            if dropdown_rect is not None and dropdown_open is not None:
                pygame.draw.rect(screen, PANEL, dropdown_rect)
                pygame.draw.rect(screen, (63, 83, 108), dropdown_rect, width=2)
                for row in range(dropdown_rect.height // row_height):
                    option_index = dropdown_scroll + row
                    option_rect = pygame.Rect(
                        dropdown_rect.x,
                        dropdown_rect.y + row * row_height,
                        dropdown_rect.width,
                        row_height,
                    )
                    if option_rect.collidepoint(mouse_position):
                        pygame.draw.rect(screen, BUTTON_HOVER, option_rect)
                    if dropdown_open == "resolution":
                        option_label = dropdown_options[option_index]
                    else:
                        option_label = dropdown_options[option_index]
                    option_text = Render_Pixel_Text(
                        small_font, option_label, WHITE
                    )
                    screen.blit(
                        option_text,
                        option_text.get_rect(
                            midleft=(option_rect.x + 16, option_rect.centery)
                        ),
                    )

        elif state == "save_slots":
            title = Render_Pixel_Text(
                title_font, translations["game_save_slots_title"], WHITE
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.14))))
            for slot_index, slot_button in enumerate(save_slot_buttons):
                slot_number = slot_index + 1
                save_slot = save_slots[slot_index]
                if save_slot is None:
                    slot_label = translations["game_slot_empty"].format(
                        slot=slot_number
                    )
                else:
                    saved_date = save_slot["created_at"].replace("T", " ")[:16]
                    slot_label = translations["game_slot_saved"].format(
                        slot=slot_number,
                        date=saved_date,
                    )
                Draw_Button(
                    screen,
                    slot_button,
                    slot_label,
                    small_font,
                    mouse_position,
                )
            if save_slots_error is not None:
                error_label = Render_Pixel_Text(
                    small_font, save_slots_error, RED
                )
                screen.blit(
                    error_label,
                    error_label.get_rect(center=(center_x, int(height * 0.88))),
                )
            back_hint = Render_Pixel_Text(
                small_font, translations["game_slots_back_hint"], WHITE
            )
            screen.blit(back_hint, (24, 20))

        elif state == "mode_chooser":
            title = Render_Pixel_Text(
                chooser_title_font,
                translations["game_mode_chooser_title"],
                WHITE,
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.14))))
            selected_slot_label = Render_Pixel_Text(
                small_font,
                translations["game_mode_chooser_slot"].format(
                    slot=selected_save_slot
                ),
                MUTED,
            )
            screen.blit(
                selected_slot_label,
                selected_slot_label.get_rect(
                    center=(center_x, int(height * 0.23))
                ),
            )
            card_font = pygame.font.Font(
                None, max(14, min(40, card_width // 9))
            )
            for mode, label_key in (
                ("carrier", "game_mode_carrier"),
                ("sandbox", "game_mode_sandbox"),
            ):
                Draw_Button(
                    screen,
                    mode_cards[mode],
                    translations[label_key],
                    card_font,
                    mouse_position,
                )
            hint = Render_Pixel_Text(
                small_font, translations["game_modes_back_hint"], WHITE
            )
            screen.blit(hint, (24, 20))

        elif state == "difficulty_chooser":
            title = Render_Pixel_Text(
                chooser_title_font, translations["game_difficulty_title"], WHITE
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.13))))
            mode_label = Render_Pixel_Text(
                small_font,
                translations["game_selected_mode"].format(
                    mode=translations["game_mode_{}".format(selected_mode)]
                ),
                MUTED,
            )
            screen.blit(
                mode_label,
                mode_label.get_rect(center=(center_x, int(height * 0.22))),
            )
            difficulty_font = pygame.font.Font(
                None, max(16, min(30, int(34 * scale)))
            )
            for difficulty, button in difficulty_buttons.items():
                Draw_Button(
                    screen,
                    button,
                    translations["game_difficulty_{}".format(difficulty)],
                    difficulty_font,
                    mouse_position,
                    selected=difficulty == selected_difficulty,
                )
            Draw_Button(
                screen,
                back_button,
                translations["game_back"],
                small_font,
                mouse_position,
            )
            hint = Render_Pixel_Text(
                small_font, translations["game_difficulty_back_hint"], WHITE
            )
            screen.blit(hint, (24, 20))

        elif state == "team_chooser":
            title = Render_Pixel_Text(
                chooser_title_font, translations["game_team_chooser_title"], WHITE
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.13))))
            mode_label = Render_Pixel_Text(
                small_font,
                translations["game_selected_mode"].format(
                    mode=translations["game_mode_{}".format(selected_mode)]
                ),
                MUTED,
            )
            difficulty_label = Render_Pixel_Text(
                small_font,
                translations["game_selected_difficulty"].format(
                    difficulty=translations[
                        "game_difficulty_{}".format(selected_difficulty)
                    ]
                ),
                MUTED,
            )
            screen.blit(
                mode_label,
                mode_label.get_rect(center=(center_x, int(height * 0.21))),
            )
            screen.blit(
                difficulty_label,
                difficulty_label.get_rect(center=(center_x, int(height * 0.26))),
            )
            team_key, team_image = team_characters[selected_team_index]
            image_cache_key = (
                team_key,
                team_image_max_width,
                team_image_max_height,
            )
            scaled_team_image = team_image_cache.get(image_cache_key)
            if scaled_team_image is None:
                image_width, image_height = team_image.get_size()
                image_scale = min(
                    team_image_max_width / image_width,
                    team_image_max_height / image_height,
                )
                scaled_size = (
                    max(1, int(image_width * image_scale)),
                    max(1, int(image_height * image_scale)),
                )
                scaled_team_image = pygame.transform.smoothscale(
                    team_image, scaled_size
                )
                team_image_cache[image_cache_key] = scaled_team_image
            screen.blit(
                scaled_team_image,
                scaled_team_image.get_rect(
                    center=(center_x, team_arrow_y)
                ),
            )
            Draw_Button(
                screen,
                team_arrow_left,
                "",
                button_font,
                mouse_position,
            )
            Draw_Button(
                screen,
                team_arrow_right,
                "",
                button_font,
                mouse_position,
            )
            arrow_center_y = team_arrow_left.centery
            pygame.draw.polygon(
                screen,
                WHITE,
                (
                    (team_arrow_left.centerx - 14, arrow_center_y),
                    (team_arrow_left.centerx + 4, arrow_center_y - 14),
                    (team_arrow_left.centerx + 4, arrow_center_y - 5),
                    (team_arrow_left.centerx + 15, arrow_center_y - 5),
                    (team_arrow_left.centerx + 15, arrow_center_y + 5),
                    (team_arrow_left.centerx + 4, arrow_center_y + 5),
                    (team_arrow_left.centerx + 4, arrow_center_y + 14),
                ),
            )
            pygame.draw.polygon(
                screen,
                WHITE,
                (
                    (team_arrow_right.centerx + 14, arrow_center_y),
                    (team_arrow_right.centerx - 4, arrow_center_y - 14),
                    (team_arrow_right.centerx - 4, arrow_center_y - 5),
                    (team_arrow_right.centerx - 15, arrow_center_y - 5),
                    (team_arrow_right.centerx - 15, arrow_center_y + 5),
                    (team_arrow_right.centerx - 4, arrow_center_y + 5),
                    (team_arrow_right.centerx - 4, arrow_center_y + 14),
                ),
            )
            team_label = Render_Pixel_Text(
                button_font, Get_Localised_Team_Name(team_key, translations), WHITE
            )
            screen.blit(
                team_label,
                team_label.get_rect(center=(center_x, int(height * 0.76))),
            )
            Draw_Button(
                screen,
                back_button,
                translations["game_back"],
                small_font,
                mouse_position,
            )
            Draw_Button(
                screen,
                apply_button,
                translations[
                    "game_team_confirmed" if team_confirmed else "game_team_confirm"
                ],
                small_font,
                mouse_position,
                selected=team_confirmed,
            )
            if team_confirmed:
                confirmation = Render_Pixel_Text(
                    small_font, translations["game_team_selected"], ACCENT
                )
                screen.blit(
                    confirmation,
                    confirmation.get_rect(
                        center=(center_x, int(height * 0.82))
                    ),
                )

            hint = Render_Pixel_Text(
                small_font, translations["game_team_back_hint"], WHITE
            )
            screen.blit(hint, (24, 20))

        if transition_started_at is not None:
            elapsed = pygame.time.get_ticks() - transition_started_at
            progress = min(1.0, elapsed / MENU_TRANSITION_DURATION_MS)
            sweep_x = int(width * progress)
            covered_width = width - sweep_x
            if covered_width > 0:
                pygame.draw.rect(
                    screen,
                    BLACK,
                    pygame.Rect(sweep_x, 0, covered_width, height),
                )
                pygame.draw.rect(
                    screen,
                    BLACK,
                    pygame.Rect(sweep_x, 0, min(4, covered_width), height),
                )
            if progress >= 1.0:
                transition_started_at = None

        pygame.display.flip()

        # Limit the loop to 60 frames per second.
        clock.tick(60)

    # Release Pygame resources after the window closes.
    pygame.quit()
    sys.exit()