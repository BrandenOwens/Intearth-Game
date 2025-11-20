# fighters.py
import pygame
import math

GRAVITY = 0.6
MOVE_SPEED = 3.5
JUMP_VEL = -11
MAX_FALL = 18


class Fighter:
    def __init__(self, x, y):
        # Position & velocity
        self.x = float(x)
        self.y = float(y)
        self.vx = 0
        self.vy = 0
        self.on_ground = False

        # Animation
        self.walk_phase = 0
        self.is_moving = False
        self.is_attacking = False

        # Tall silhouette proportions
        self.head_w, self.head_h = 10, 8
        self.torso_w, self.torso_h = 14, 18
        self.leg_w, self.leg_h = 4, 22
        self.arm_w, self.arm_h = 4, 16

        self.width = self.torso_w + 6
        self.height = self.head_h + self.torso_h + self.leg_h

        # Debug colors
        self.head_color = (255, 255, 0)
        self.torso_color = (255, 255, 0)
        self.left_arm_color = (0, 200, 255)
        self.right_arm_color = (0, 255, 120)
        self.left_leg_color = (255, 140, 0)
        self.right_leg_color = (255, 0, 200)

    # Collision rect
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    # ------------------------------------------------------------
    # Main update entry point (called from main.py)
    # ------------------------------------------------------------
    def update_player(self, keys, platforms):
        self.handle_input(keys)
        self.apply_physics(platforms)
        self.update_animation()

    # ------------------------------------------------------------
    # Input
    # ------------------------------------------------------------
    def handle_input(self, keys):
        self.vx = 0
        self.is_moving = False

        if keys[pygame.K_a]:
            self.vx = -MOVE_SPEED
            self.is_moving = True
        if keys[pygame.K_d]:
            self.vx = MOVE_SPEED
            self.is_moving = True

        # Jump
        if self.on_ground and (keys[pygame.K_w] or keys[pygame.K_SPACE]):
            self.vy = JUMP_VEL
            self.on_ground = False

    # ------------------------------------------------------------
    # Physics + collision
    # ------------------------------------------------------------
    def apply_physics(self, platforms):
        # Gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        # Horizontal move
        self.x += self.vx
        r = self.rect
        for p in platforms:
            if r.colliderect(p.rect):
                if self.vx > 0:   # hit left side of platform
                    self.x = p.rect.left - self.width
                elif self.vx < 0: # hit right side
                    self.x = p.rect.right
                r = self.rect

        # Vertical move
        self.y += self.vy
        r = self.rect
        self.on_ground = False

        for p in platforms:
            if r.colliderect(p.rect):
                if self.vy > 0:  # landing
                    self.y = p.rect.top - self.height
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:  # head hit
                    self.y = p.rect.bottom
                    self.vy = 0
                r = self.rect

    # ------------------------------------------------------------
    # Animation updates
    # ------------------------------------------------------------
    def update_animation(self):
        if self.is_moving and self.on_ground:
            self.walk_phase += 0.3
        else:
            self.walk_phase = 0

    # ------------------------------------------------------------
    # Draw player
    # ------------------------------------------------------------
    def draw(self, surf, cam_x):
        px = int(self.x - cam_x)
        py = int(self.y)
        cx = px + self.width // 2

        head_top = py
        torso_top = head_top + self.head_h
        leg_top = torso_top + self.torso_h

        # Leg swing
        swing = int(math.sin(self.walk_phase) * 4)

        left_leg = pygame.Rect(cx - 6 - swing, leg_top, self.leg_w, self.leg_h)
        right_leg = pygame.Rect(cx + 2 + swing, leg_top, self.leg_w, self.leg_h)

        torso = pygame.Rect(cx - self.torso_w // 2, torso_top, self.torso_w, self.torso_h)
        head = pygame.Rect(cx - self.head_w // 2, head_top, self.head_w, self.head_h)

        # Arms swing opposite of legs
        arm_y = torso_top + 4
        left_arm = pygame.Rect(cx - self.torso_w // 2 - 4 - swing, arm_y, self.arm_w, self.arm_h)
        right_arm = pygame.Rect(cx + self.torso_w // 2 + swing, arm_y, self.arm_w, self.arm_h)

        pygame.draw.rect(surf, self.left_leg_color, left_leg)
        pygame.draw.rect(surf, self.right_leg_color, right_leg)
        pygame.draw.rect(surf, self.torso_color, torso)
        pygame.draw.rect(surf, self.left_arm_color, left_arm)
        pygame.draw.rect(surf, self.right_arm_color, right_arm)
        pygame.draw.rect(surf, self.head_color, head)
