# fighters.py — player character

import pygame
from constants import (
    MOVE_SPEED,
    JUMP_SPEED,
    GRAVITY,
    MAX_FALL_SPEED,
    PLAYER_COLOR,
)


class Fighter:
    """
    Simple tall silhouette made of rectangles, with basic platformer physics.
    """

    def __init__(self, x: int, y: int):
        # logical position is the top-left of the hitbox
        self.x = x
        self.y = y

        # hitbox size
        self.width = 18
        self.height = 60

        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False

        # for walk animation
        self.walk_cycle = 0.0
        self.facing = 1  # 1 right, -1 left

    # ---------------- physics / update ----------------

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def handle_input(self, keys):
        self.vx = 0
        if keys[pygame.K_a]:
            self.vx -= MOVE_SPEED
            self.facing = -1
        if keys[pygame.K_d]:
            self.vx += MOVE_SPEED
            self.facing = 1

    def apply_gravity(self):
        self.vy += GRAVITY
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_SPEED
            self.on_ground = False

    def collide_axis(self, platforms, axis: str):
        r = self.rect()
        for p in platforms:
            if r.colliderect(p.rect):
                if axis == "x":
                    if self.vx > 0:
                        r.right = p.left
                    elif self.vx < 0:
                        r.left = p.right
                    self.x = r.x
                    self.vx = 0
                else:
                    if self.vy > 0:
                        r.bottom = p.top
                        self.on_ground = True
                    elif self.vy < 0:
                        r.top = p.bottom
                    self.y = r.y
                    self.vy = 0
        return r

    def update(self, keys, platforms):
        self.handle_input(keys)
        self.apply_gravity()

        # x axis
        self.x += self.vx
        self.on_ground = False
        self.collide_axis(platforms, "x")

        # y axis
        self.y += self.vy
        self.collide_axis(platforms, "y")

        # walk animation
        if self.vx != 0 and self.on_ground:
            self.walk_cycle += 0.25
        else:
            self.walk_cycle = 0.0

    # ---------------- drawing ----------------

    def draw(self, surface, camera_x: int):
        # base rect (torso + legs)
        r = self.rect().move(-camera_x, 0)

        # body proportions
        head_h = 12
        torso_h = 24
        leg_h = self.height - (head_h + torso_h)
        arm_len = 20
        arm_thick = 4

        # walk swing
        swing = int(4 * pygame.math.Vector2(1, 0).rotate(self.walk_cycle * 30).x)

        # head
        head_rect = pygame.Rect(
            r.x,
            r.y,
            r.width,
            head_h,
        )

        # torso
        torso_rect = pygame.Rect(
            r.x,
            r.y + head_h,
            r.width,
            torso_h,
        )

        # legs (two thin rectangles)
        leg_width = 4
        leg_y = r.y + head_h + torso_h
        left_leg = pygame.Rect(
            r.centerx - 6,
            leg_y,
            leg_width,
            leg_h,
        )
        right_leg = pygame.Rect(
            r.centerx + 2,
            leg_y,
            leg_width,
            leg_h,
        )

        if self.vx != 0:
            if self.facing > 0:
                left_leg.y += swing
                right_leg.y -= swing
            else:
                left_leg.y -= swing
                right_leg.y += swing

        # arms (simple rectangles that swing)
        shoulder_y = r.y + head_h + 4
        if self.facing > 0:
            arm_dir = 1
        else:
            arm_dir = -1

        arm_swing = swing
        left_arm = pygame.Rect(
            r.centerx - arm_dir * (r.width // 2 + 2),
            shoulder_y + arm_swing,
            arm_len,
            arm_thick,
        )
        right_arm = pygame.Rect(
            r.centerx + (arm_dir * (r.width // 2 - arm_len - 2)),
            shoulder_y - arm_swing,
            arm_len,
            arm_thick,
        )

        # draw all pieces
        for part in (head_rect, torso_rect, left_leg, right_leg, left_arm, right_arm):
            pygame.draw.rect(surface, PLAYER_COLOR, part)
