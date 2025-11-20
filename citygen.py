# citygen.py — stage / city generation and buildings

import pygame
import random

from constants import (
    WORLD_WIDTH,
    GROUND_Y,
    GROUND_HEIGHT,
    WINDOW_WIDTH,
    BG_COLOR,
    PLATFORM_COLOR,
    BUILDING_FACADE_COLOR,
    BUILDING_INTERIOR_COLOR,
    WINDOW_COLOR,
    DOOR_COLOR,
    STAIRS_COLOR,
    BUILDING_WIDTH,
    BUILDING_NUM_FLOORS,
    BUILDING_FLOOR_HEIGHT,
)


class Platform:
    """Simple wrapper around a pygame.Rect used by the player for collision."""

    def __init__(self, x: int, y: int, w: int, h: int):
        self.rect = pygame.Rect(x, y, w, h)
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


class Building:
    """
    A big multi-floor building.

    - outside view with windows + door
    - when inside, only the current floor is drawn
    - `interact(player)` returns an action tuple or None:
        ("enter_building", 0)
        ("floor_up", new_floor_index)
        ("exit_building", None)
    """

    def __init__(self, x: int, width: int, num_floors: int, floor_height: int):
        self.x = x
        self.width = width
        self.num_floors = num_floors
        self.floor_height = floor_height

        self.height = num_floors * floor_height
        self.y = GROUND_Y - self.height
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # door on the outside
        door_w = 46
        door_h = int(floor_height * 0.7)
        door_x = self.x + (self.width - door_w) // 2
        door_y = GROUND_Y - door_h
        self.door_rect = pygame.Rect(door_x, door_y, door_w, door_h)

        # windows for outside facade (2 per floor)
        self.window_rects = []
        margin_x = 40
        win_w = 46
        win_h = 46
        for f in range(num_floors):
            base_y = GROUND_Y - (f + 1) * floor_height
            win_y = base_y + 20
            for col in range(2):
                if col == 0:
                    win_x = self.x + margin_x
                else:
                    win_x = self.x + self.width - margin_x - win_w
                self.window_rects.append(
                    pygame.Rect(win_x, win_y, win_w, win_h)
                )

        # interior "stairs" rectangles (teleporters) – one per floor except top
        self.interior_stairs = []
        stair_w = 46
        stair_h = 46
        stair_x = self.x + self.width - stair_w - 40
        for f in range(num_floors - 1):
            floor_top = GROUND_Y - (f + 1) * floor_height
            stair_y = floor_top + floor_height - stair_h - 4
            self.interior_stairs.append(
                pygame.Rect(stair_x, stair_y, stair_w, stair_h)
            )

        # exit teleport on ground floor interior
        self.exit_rect = pygame.Rect(
            self.door_rect.x,
            GROUND_Y - stair_h,
            self.door_rect.width,
            stair_h,
        )

        self.outside_visible = True
        self.current_floor = 0

    # ---------- drawing ----------

    def draw_outside(self, surface, camera_x: int):
        r = self.rect.move(-camera_x, 0)
        pygame.draw.rect(surface, BUILDING_FACADE_COLOR, r)

        for wr in self.window_rects:
            pygame.draw.rect(surface, WINDOW_COLOR, wr.move(-camera_x, 0))

        pygame.draw.rect(surface, DOOR_COLOR, self.door_rect.move(-camera_x, 0))

    def draw_inside(self, surface, camera_x: int):
        floor_top = GROUND_Y - (self.current_floor + 1) * self.floor_height
        floor_rect = pygame.Rect(
            self.x, floor_top, self.width, self.floor_height
        )
        pygame.draw.rect(
            surface, BUILDING_INTERIOR_COLOR, floor_rect.move(-camera_x, 0)
        )

        # floor line
        floor_line = pygame.Rect(
            self.x,
            floor_top + self.floor_height - 8,
            self.width,
            8,
        )
        pygame.draw.rect(surface, PLATFORM_COLOR, floor_line.move(-camera_x, 0))

        # stairs up (all floors except the top)
        if self.current_floor < self.num_floors - 1:
            sr = self.interior_stairs[self.current_floor].move(-camera_x, 0)
            pygame.draw.rect(surface, STAIRS_COLOR, sr)

        # exit on ground floor
        if self.current_floor == 0:
            pygame.draw.rect(
                surface, DOOR_COLOR, self.exit_rect.move(-camera_x, 0)
            )

    def draw(self, surface, camera_x: int):
        if self.outside_visible:
            self.draw_outside(surface, camera_x)
        else:
            self.draw_inside(surface, camera_x)

    # ---------- interaction ----------

    def interact(self, player):
        """
        Called when the player presses E.
        Returns (action_name, floor_index_or_None) or None.
        """

        # use a simple point at the player's feet
        px = player.x + player.width // 2
        py = player.y + player.height

        if self.outside_visible:
            if self.door_rect.collidepoint(px, py):
                # move player just inside on floor 0
                player.x = self.x + self.width // 2 - player.width // 2
                player.y = GROUND_Y - player.height
                return ("enter_building", 0)
        else:
            # exit building (ground floor only)
            if self.current_floor == 0 and self.exit_rect.collidepoint(px, py):
                player.x = self.door_rect.centerx - player.width // 2
                player.y = GROUND_Y - player.height
                return ("exit_building", None)

            # stairs up (if not on top floor)
            if self.current_floor < self.num_floors - 1:
                stairs_rect = self.interior_stairs[self.current_floor]
                if stairs_rect.collidepoint(px, py):
                    new_floor = self.current_floor + 1
                    player.y = (
                        GROUND_Y
                        - (new_floor + 1) * self.floor_height
                        + (self.floor_height - player.height)
                    )
                    return ("floor_up", new_floor)

        return None


class City:
    """Holds ground platforms and a row of large buildings."""

    def __init__(self):
        self.platforms = []
        self.buildings = []
        self.generate()

    def generate(self):
        self.platforms.clear()
        self.buildings.clear()

        # ground
        ground = Platform(0, GROUND_Y, WORLD_WIDTH, GROUND_HEIGHT)
        self.platforms.append(ground)

        # big buildings across the world
        spacing = 220
        x = 200
        while x < WORLD_WIDTH - BUILDING_WIDTH:
            b = Building(
                x,
                BUILDING_WIDTH,
                BUILDING_NUM_FLOORS,
                BUILDING_FLOOR_HEIGHT,
            )
            self.buildings.append(b)
            x += BUILDING_WIDTH + spacing

    def draw(self, surface, camera_x: int):
        surface.fill(BG_COLOR)

        for p in self.platforms:
            pygame.draw.rect(surface, PLATFORM_COLOR, p.rect.move(-camera_x, 0))

        for b in self.buildings:
            b.draw(surface, camera_x)
