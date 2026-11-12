import pygame
import sys

def main():
    # Initialize Pygame
    pygame.init()

    # Screen dimensions
    screen_width = 1920
    screen_height = 1080
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Basic Pygame Window")

    # Colors (RGB)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)

    # Game clock to control the frame rate
    clock = pygame.time.Clock()

    running = True
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # --- Game Logic (Updates) ---
        pass # Empty logic for now

        # --- Drawing ---
        screen.fill(BLACK)
        
        # Example: Draw a red rectangle in the center
        pygame.draw.rect(screen, GREEN, (350, 250, 100, 100))

        pygame.display.flip()

        # --- Frame Rate Control ---
        clock.tick(60)

    # Quit Pygame and exit system
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
