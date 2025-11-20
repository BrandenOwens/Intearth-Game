# main.py

import pygame
from constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, WHITE
from fighters import Fighter
from citygen import City

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    # Create world + player
    city = City()
    player = Fighter(100, 200)  # x, y world position

    camera_x = 0
    running = True

    while running:
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ------------------------------------
        # UPDATE PLAYER (movement + gravity)
        # ------------------------------------
        player.update_player(keys, city.platforms)

        # ------------------------------------
        # CAMERA FOLLOW LOGIC
        # ------------------------------------
        camera_x = player.x - WINDOW_WIDTH // 2
        if camera_x < 0:
            camera_x = 0

        # ------------------------------------
        # DRAW WORLD
        # ------------------------------------
        screen.fill(WHITE)
        city.draw(screen, camera_x)
        player.draw(screen, camera_x)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
