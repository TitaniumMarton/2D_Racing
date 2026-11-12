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

# Colors (RGB)
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


def main():
    pygame.init()

    languages = available_languages()
    resolution_index, language, display_mode = load_preferences(languages)
    localisations = {
        locale: load_localisation(locale) for locale in languages
    }
    if any("language_name" not in data for data in localisations.values()):
        raise ValueError("Each localisation must define a language_name")
    language_names = {
        locale: data["language_name"]
        for locale, data in localisations.items()
    }
    translations = localisations[language]
    screen_size, screen_flags = get_display_mode_settings(
        display_mode, RESOLUTIONS[resolution_index]
    )
    screen = pygame.display.set_mode(screen_size, screen_flags)
    pygame.display.set_caption("2D Racing")

    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 100)
    button_font = pygame.font.Font(None, 42)
    small_font = pygame.font.Font(None, 28)
    mode_font = pygame.font.Font(None, 24)
    state = "menu"
    running = True
    pending_resolution_index = resolution_index
    pending_language = language
    pending_display_mode = display_mode
    confirm_previous_resolution_index = resolution_index
    confirm_previous_display_mode = display_mode
    resolution_confirm_deadline = 0
    display_mode_labels = {
        mode: translations["display_mode_{}".format(mode)]
        for mode in DISPLAY_MODES
    }
    dropdown_open = None
    dropdown_scroll = 0
    settings_message = None

    while running:
        if (
            state == "confirm_resolution"
            and pygame.time.get_ticks() >= resolution_confirm_deadline
        ):
            try:
                save_preferences(
                    pending_resolution_index, language, pending_display_mode
                )
            except OSError as error:
                print("Could not save settings: {}".format(error), file=sys.stderr)
                screen_size, screen_flags = get_display_mode_settings(
                    confirm_previous_display_mode,
                    RESOLUTIONS[confirm_previous_resolution_index],
                )
                screen = pygame.display.set_mode(screen_size, screen_flags)
                resolution_index = confirm_previous_resolution_index
                display_mode = confirm_previous_display_mode
                pending_resolution_index = resolution_index
                pending_display_mode = display_mode
                settings_message = translations["settings_save_failed"]
            else:
                resolution_index = pending_resolution_index
                display_mode = pending_display_mode
                settings_message = translations["settings_applied"]
            state = "settings"

        width, height = screen.get_size()
        center_x = width // 2
        scale = min(width / 1920, height / 1080)
        button_width = min(int(width * 0.42), 520)
        button_height = max(52, int(72 * scale))
        selector_width = min(int(width * 0.48), 520)
        selector_height = max(40, int(62 * scale))
        selector_x = center_x - selector_width // 2
        resolution_selector = pygame.Rect(
            selector_x, int(height * 0.29), selector_width, selector_height
        )
        language_selector = pygame.Rect(
            selector_x, int(height * 0.60), selector_width, selector_height
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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state == "confirm_resolution" and event.key == pygame.K_RETURN:
                    screen_size, screen_flags = get_display_mode_settings(
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
                elif event.key == pygame.K_ESCAPE and state == "game":
                    state = "menu"
                elif state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    state = "game"
            elif event.type == pygame.MOUSEWHEEL and dropdown_rect is not None:
                if dropdown_rect.collidepoint(pygame.mouse.get_pos()):
                    dropdown_scroll = max(
                        0,
                        min(
                            dropdown_scroll - event.y,
                            len(dropdown_options) - dropdown_max_rows,
                        ),
                    )
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "menu":
                    if start_button.collidepoint(event.pos):
                        state = "game"
                    elif settings_button.collidepoint(event.pos):
                        state = "settings"
                        pending_resolution_index = resolution_index
                        pending_language = language
                        pending_display_mode = display_mode
                        settings_message = None
                    elif quit_button.collidepoint(event.pos):
                        running = False
                elif state == "settings":
                    if dropdown_rect is not None and dropdown_rect.collidepoint(event.pos):
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
                                save_preferences(
                                    resolution_index,
                                    pending_language,
                                    display_mode,
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
                                    get_display_mode_settings(
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
                                            save_preferences(
                                                resolution_index,
                                                language,
                                                pending_display_mode,
                                            )
                                        except OSError as error:
                                            print(
                                                "Could not save settings: {}".format(
                                                    error
                                                ),
                                                file=sys.stderr,
                                            )
                                            old_size, old_flags = (
                                                get_display_mode_settings(
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
                                            settings_message = translations[
                                                "settings_applied"
                                            ]
                        else:
                            try:
                                save_preferences(
                                    resolution_index, pending_language, display_mode
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
                                settings_message = translations["settings_applied"]
                    elif back_button.collidepoint(event.pos):
                        state = "menu"

        mouse_position = pygame.mouse.get_pos()
        screen.fill(BACKGROUND)

        if state == "menu":
            title = render_pixel_text(
                title_font, translations["main_menu_title"], WHITE
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.30))))
            subtitle = render_pixel_text(
                small_font, translations["main_menu_subtitle"], MUTED
            )
            screen.blit(subtitle, subtitle.get_rect(center=(center_x, int(height * 0.39))))
            draw_button(
                screen,
                start_button,
                translations["main_menu_start"],
                button_font,
                mouse_position,
            )
            draw_button(
                screen,
                settings_button,
                translations["main_menu_settings"],
                button_font,
                mouse_position,
            )
            draw_button(
                screen,
                quit_button,
                translations["main_menu_quit"],
                button_font,
                mouse_position,
            )

        elif state == "confirm_resolution":
            title = render_pixel_text(
                title_font, translations["settings_confirm_resolution"], WHITE
            )
            seconds_left = max(
                0,
                (resolution_confirm_deadline - pygame.time.get_ticks() + 999) // 1000,
            )
            prompt = render_pixel_text(
                small_font,
                translations["settings_press_enter_revert"].format(
                    seconds=seconds_left
                ),
                ACCENT,
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.43))))
            screen.blit(prompt, prompt.get_rect(center=(center_x, int(height * 0.53))))

        elif state == "settings":
            title = render_pixel_text(
                title_font, translations["settings_title"], WHITE
            )
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.14))))
            resolution_label = render_pixel_text(
                small_font, translations["settings_resolution"], MUTED
            )
            screen.blit(
                resolution_label,
                resolution_label.get_rect(center=(center_x, int(height * 0.25))),
            )
            mode_label = render_pixel_text(
                small_font, translations["settings_display_mode"], MUTED
            )
            screen.blit(
                mode_label,
                mode_label.get_rect(center=(center_x, int(height * 0.41))),
            )
            language_label = render_pixel_text(
                small_font, translations["settings_language"], MUTED
            )
            screen.blit(
                language_label,
                language_label.get_rect(center=(center_x, int(height * 0.56))),
            )
            draw_button(
                screen,
                resolution_selector,
                "{} x {}    v".format(*RESOLUTIONS[pending_resolution_index]),
                button_font,
                mouse_position,
            )
            draw_button(
                screen,
                language_selector,
                "{}    v".format(language_names[pending_language]),
                button_font,
                mouse_position,
            )
            for mode, button in mode_buttons.items():
                draw_button(
                    screen,
                    button,
                    display_mode_labels[mode],
                    mode_font,
                    mouse_position,
                    selected=mode == pending_display_mode,
                )
            draw_button(
                screen,
                back_button,
                translations["settings_back"],
                small_font,
                mouse_position,
            )
            draw_button(
                screen,
                apply_button,
                translations["settings_apply"],
                small_font,
                mouse_position,
            )
            if settings_message is not None:
                message = render_pixel_text(
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
                    option_text = render_pixel_text(
                        small_font, option_label, WHITE
                    )
                    screen.blit(
                        option_text,
                        option_text.get_rect(
                            midleft=(option_rect.x + 16, option_rect.centery)
                        ),
                    )

        else:
            square_size = max(24, int(100 * scale))
            squares = (
                (int(width * 350 / 1920), int(height * 250 / 1080), (0, 255, 0)),
                (int(width * 500 / 1920), int(height * 350 / 1080), (255, 255, 0)),
                (int(width * 650 / 1920), int(height * 450 / 1080), (255, 0, 0)),
            )
            for x, y, color in squares:
                pygame.draw.rect(screen, color, (x, y, square_size, square_size))
            hint = render_pixel_text(
                small_font, translations["game_back_hint"], WHITE
            )
            screen.blit(hint, (24, 20))

        pygame.display.flip()

        # --- Frame Rate Control ---
        clock.tick(60)

    # Quit Pygame and exit system
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
