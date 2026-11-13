import json
import math
import sys
from pathlib import Path
import pygame
import yaml

from functions import (
    MAIN_THEME_FILE,
    Available_Languages,
    Create_Save_Slot,
    Draw_Button,
    Get_Display_Mode_Settings,
    Load_Localisation,
    Load_Preferences,
    Load_Save_Slot,
    Load_Save_Slots,
    Render_Pixel_Text,
    SAVE_SLOT_COUNT,
    Save_Preferences,
    Set_Music_Volume,
)

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
                title_font, translations["game_mode_chooser_title"], WHITE
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
            # Show non-interactive mode cards until their gameplay is implemented.
            card_gap = max(16, int(28 * scale))
            card_width = min(
                int(width * 0.38),
                max(180, int(480 * scale)),
            )
            card_height = max(120, int(220 * scale))
            card_left = center_x - (card_width * 2 + card_gap) // 2
            card_top = int(height * 0.34)
            card_rectangles = (
                pygame.Rect(card_left, card_top, card_width, card_height),
                pygame.Rect(
                    card_left + card_width + card_gap,
                    card_top,
                    card_width,
                    card_height,
                ),
            )
            card_font = pygame.font.Font(
                None, max(14, min(40, card_width // 9))
            )
            for card_rect, label_key in zip(
                card_rectangles,
                ("game_mode_carrier", "game_mode_sandbox"),
            ):
                pygame.draw.rect(screen, PANEL, card_rect, border_radius=14)
                pygame.draw.rect(
                    screen,
                    (63, 83, 108),
                    card_rect,
                    width=2,
                    border_radius=14,
                )
                card_label = Render_Pixel_Text(
                    card_font, translations[label_key], WHITE
                )
                screen.blit(
                    card_label,
                    card_label.get_rect(center=card_rect.center),
                )
            development_label = Render_Pixel_Text(
                small_font, translations["game_under_development"], MUTED
            )
            screen.blit(
                development_label,
                development_label.get_rect(
                    center=(
                        center_x,
                        card_rectangles[0].bottom + max(32, int(64 * scale)),
                    )
                ),
            )
            hint = Render_Pixel_Text(
                small_font, translations["game_modes_back_hint"], WHITE
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


# Start the game only when this file is run as the program entry point.
if __name__ == "__main__":
    Main()
