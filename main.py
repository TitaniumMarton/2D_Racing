import sys

import pygame


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


def render_pixel_text(font, text, color):
    rendered = font.render(text, False, color)
    pixel_size = (
        max(1, rendered.get_width() // 2),
        max(1, rendered.get_height() // 2),
    )
    reduced = pygame.transform.scale(rendered, pixel_size)
    return pygame.transform.scale(reduced, rendered.get_size())


def draw_button(surface, rect, text, font, mouse_position):
    color = BUTTON_HOVER if rect.collidepoint(mouse_position) else BUTTON
    pygame.draw.rect(surface, color, rect, border_radius=10)
    pygame.draw.rect(surface, (63, 83, 108), rect, width=2, border_radius=10)
    label = render_pixel_text(font, text, WHITE)
    surface.blit(label, label.get_rect(center=rect.center))


def main():
    pygame.init()

    resolution_index = 0
    screen = pygame.display.set_mode(RESOLUTIONS[resolution_index])
    pygame.display.set_caption("2D Racing")

    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 100)
    button_font = pygame.font.Font(None, 42)
    small_font = pygame.font.Font(None, 28)
    state = "menu"
    running = True

    # Game clock to control the frame rate

    while running:
        width, height = screen.get_size()
        center_x = width // 2
        scale = min(width / 1920, height / 1080)
        button_width = min(int(width * 0.42), 520)
        button_height = max(52, int(72 * scale))

        start_button = pygame.Rect(
            0, int(height * 0.56), button_width, button_height
        )
        start_button.centerx = center_x
        settings_button = start_button.copy()
        settings_button.y = int(height * 0.56) + button_height + max(16, int(20 * scale))

        selector_width = min(int(width * 0.42), 480)
        selector_height = max(54, int(68 * scale))
        arrow_width = max(52, int(68 * scale))
        selector_y = int(height * 0.52)
        previous_button = pygame.Rect(
            center_x - selector_width // 2 - arrow_width - 12,
            selector_y,
            arrow_width,
            selector_height,
        )
        resolution_button = pygame.Rect(
            center_x - selector_width // 2,
            selector_y,
            selector_width,
            selector_height,
        )
        next_button = pygame.Rect(
            center_x + selector_width // 2 + 12,
            selector_y,
            arrow_width,
            selector_height,
        )
        back_button = pygame.Rect(
            0, int(height * 0.72), button_width, button_height
        )
        back_button.centerx = center_x

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == "menu":
                        running = False
                    else:
                        state = "menu"
                elif state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    state = "game"
                elif state == "settings" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    step = -1 if event.key == pygame.K_LEFT else 1
                    resolution_index = (resolution_index + step) % len(RESOLUTIONS)
                    screen = pygame.display.set_mode(RESOLUTIONS[resolution_index])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "menu":
                    if start_button.collidepoint(event.pos):
                        state = "game"
                    elif settings_button.collidepoint(event.pos):
                        state = "settings"
                elif state == "settings":
                    if previous_button.collidepoint(event.pos):
                        resolution_index = (resolution_index - 1) % len(RESOLUTIONS)
                        screen = pygame.display.set_mode(RESOLUTIONS[resolution_index])
                    elif next_button.collidepoint(event.pos) or resolution_button.collidepoint(event.pos):
                        resolution_index = (resolution_index + 1) % len(RESOLUTIONS)
                        screen = pygame.display.set_mode(RESOLUTIONS[resolution_index])
                    elif back_button.collidepoint(event.pos):
                        state = "menu"

        mouse_position = pygame.mouse.get_pos()
        screen.fill(BACKGROUND)

        if state == "menu":
            title = render_pixel_text(title_font, "2D Racing", WHITE)
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.30))))
            subtitle = render_pixel_text(small_font, "A simple race starts here", MUTED)
            screen.blit(subtitle, subtitle.get_rect(center=(center_x, int(height * 0.39))))
            draw_button(screen, start_button, "START GAME", button_font, mouse_position)
            draw_button(screen, settings_button, "SETTINGS", button_font, mouse_position)
            hint = render_pixel_text(small_font, "ESC  QUIT", MUTED)
            screen.blit(hint, hint.get_rect(center=(center_x, int(height * 0.88))))

        elif state == "settings":
            title = render_pixel_text(title_font, "SETTINGS", WHITE)
            screen.blit(title, title.get_rect(center=(center_x, int(height * 0.30))))
            label = render_pixel_text(small_font, "SCREEN RESOLUTION", MUTED)
            screen.blit(label, label.get_rect(center=(center_x, int(height * 0.45))))
            draw_button(screen, previous_button, "<", button_font, mouse_position)
            draw_button(
                screen,
                resolution_button,
                "{} x {}".format(*RESOLUTIONS[resolution_index]),
                button_font,
                mouse_position,
            )
            draw_button(screen, next_button, ">", button_font, mouse_position)
            draw_button(screen, back_button, "BACK", button_font, mouse_position)
            hint = render_pixel_text(small_font, "Use LEFT / RIGHT to change resolution", MUTED)
            screen.blit(hint, hint.get_rect(center=(center_x, int(height * 0.87))))

        else:
            square_size = max(24, int(100 * scale))
            squares = (
                (int(width * 350 / 1920), int(height * 250 / 1080), (0, 255, 0)),
                (int(width * 500 / 1920), int(height * 350 / 1080), (255, 255, 0)),
                (int(width * 650 / 1920), int(height * 450 / 1080), (255, 0, 0)),
            )
            for x, y, color in squares:
                pygame.draw.rect(screen, color, (x, y, square_size, square_size))
            hint = render_pixel_text(small_font, "ESC  BACK TO MENU", WHITE)
            screen.blit(hint, (24, 20))

        pygame.display.flip()

        # --- Frame Rate Control ---
        clock.tick(60)

    # Quit Pygame and exit system
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
