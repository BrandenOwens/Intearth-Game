# main.py — ties everything together

import pygame
from constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS,
    KEY_JUMP,
    KEY_INTERACT,
)
from fighters import Fighter
from citygen import City


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    city = City()
    player = Fighter(100, 100)

    camera_x = 0

    running = True
    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == KEY_JUMP:
                    player.jump()
                elif event.key == KEY_INTERACT:
                    # try interacting with any building
                    for b in city.buildings:
                        action = b.interact(player)
                        if action:
                            kind, floor = action
                            if kind == "enter_building":
                                b.outside_visible = False
                                b.current_floor = 0
                            elif kind == "floor_up":
                                b.current_floor = floor
                            elif kind == "exit_building":
                                b.outside_visible = True
                            break

        keys = pygame.key.get_pressed()
        player.update(keys, city.platforms)

        # camera follow
        camera_x = int(player.x - WINDOW_WIDTH / 2)
        if camera_x < 0:
            camera_x = 0
        max_cam = city.platforms[0].width - WINDOW_WIDTH
        if camera_x > max_cam:
            camera_x = max_cam

        # draw
        city.draw(screen, camera_x)
        player.draw(screen, camera_x)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
