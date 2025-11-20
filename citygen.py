# ============================================================
# citygen.py — Stage/City Generation and Platforms
# ============================================================

import pygame
import random

# These should line up with constants.py,
# but we keep local fallbacks so the module works on its own.
WORLD_WIDTH = 2400
HEIGHT = 540
GROUND_Y = HEIGHT - 60


# ------------------------------------------------------------
# Basic geometry objects
# ------------------------------------------------------------
class Platform:
    """
    Simple wrapper around a pygame.Rect so that existing code
    can use p.x, p.y, p.width, p.height, p.top, p.bottom, etc.
    """
    def __init__(self, x, y, w, h):
        # main rect
        self.rect = pygame.Rect(x, y, w, h)

        # legacy-style attributes used by collision code
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    @property
    def top(self):
        return self.rect.top

    @property
    def bottom(self):
        return self.rect.bottom

    @property
    def left(self):
        return self.rect.left

    @property
    def right(self):
        return self.rect.right


class City:
    """
    Very simple city/map for now:
    - one ground platform that spans the whole world
    - later we can add upper platforms, ladders, enemies, etc.
    """

    def __init__(self):
        self.platforms = []
        self.generate()

    def generate(self):
        self.platforms.clear()

        # Ground platform along the bottom
        ground = Platform(0, GROUND_Y, WORLD_WIDTH, 20)
        self.platforms.append(ground)

        # Example extra platforms (you can tweak/remove these)
        rng = random.Random(1234)
        for i in range(5):
            w = rng.randint(120, 220)
            h = 18
            x = rng.randint(50, WORLD_WIDTH - w - 50)
            y = rng.randint(GROUND_Y - 220, GROUND_Y - 120)
            self.platforms.append(Platform(x, y, w, h))

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------
    def draw(self, surface, camera_x):
        # simple background
        surface.fill((10, 10, 20))

        # draw platforms
        for p in self.platforms:
            r = p.rect.move(-camera_x, 0)
            pygame.draw.rect(surface, (60, 60, 60), r)
