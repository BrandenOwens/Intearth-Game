import pygame

# ===============================
# FIGHTER CLASS (PLAYER ONLY NOW)
# ===============================

class Fighter:
    def __init__(self, x, y):
        # Position & physics
        self.x = x
        self.y = y
        self.vel_y = 0
        self.on_ground = False
        self.move_speed = 3
        self.jump_strength = -10
        self.gravity = 0.5

        # Collision box (covers entire body)
        self.width = 20
        self.height = 60

        # Limb proportions (Proportions B)
        self.head_h = 12
        self.head_w = 12

        self.torso_h = 22
        self.torso_w = 14

        self.arm_w = 4
        self.arm_h = 14      # upper + forearm segments

        self.leg_w = 6
        self.leg_h = 16

        # Colors for debugging (each limb different)
        self.col_head = (255, 255, 0)
        self.col_torso = (255, 200, 0)

        self.col_arm_l = (0, 255, 0)
        self.col_fore_l = (0, 200, 0)

        self.col_arm_r = (255, 0, 255)
        self.col_fore_r = (200, 0, 200)

        self.col_leg_l = (0, 0, 255)
        self.col_shin_l = (0, 0, 200)

        self.col_leg_r = (255, 128, 0)
        self.col_shin_r = (200, 100, 0)

    # -----------------------------------------
    # UPDATE (movement + gravity + collision)
    # -----------------------------------------
    def update_player(self, keys, platforms):
        # Horizontal movement
        if keys[pygame.K_a]:
            self.x -= self.move_speed
        if keys[pygame.K_d]:
            self.x += self.move_speed

        # Jump
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = self.jump_strength
            self.on_ground = False

        # Apply gravity
        self.vel_y += self.gravity
        self.y += self.vel_y

        # Handle collisions
        self.handle_collision(platforms)

    # -----------------------------------------
    # COLLISION
    # -----------------------------------------
    def handle_collision(self, platforms):
        self.on_ground = False
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)

        for p in platforms:
            plat_rect = pygame.Rect(p.x, p.y, p.width, p.height)

            if player_rect.colliderect(plat_rect):
                # Landing on top of platform
                if self.vel_y >= 0 and player_rect.bottom <= plat_rect.top + 10:
                    self.y = plat_rect.top - self.height
                    self.vel_y = 0
                    self.on_ground = True
                    player_rect.bottom = plat_rect.top

    # -----------------------------------------
    # DRAW LIMB-BY-LIMB (MULTICOLOR)
    # -----------------------------------------
    def draw(self, surface, camera_x):
        px = self.x - camera_x
        py = self.y

        # HEAD
        head = pygame.Rect(
            px + (self.width//2 - self.head_w//2),
            py,
            self.head_w,
            self.head_h
        )
        pygame.draw.rect(surface, self.col_head, head)

        # TORSO
        torso = pygame.Rect(
            px + (self.width//2 - self.torso_w//2),
            py + self.head_h,
            self.torso_w,
            self.torso_h
        )
        pygame.draw.rect(surface, self.col_torso, torso)

        # LEFT ARM (upper)
        arm_l = pygame.Rect(
            torso.left - self.arm_w,
            torso.top + 4,
            self.arm_w,
            self.arm_h
        )
        pygame.draw.rect(surface, self.col_arm_l, arm_l)

        # LEFT FOREARM
        fore_l = pygame.Rect(
            arm_l.left,
            arm_l.bottom,
            self.arm_w,
            self.arm_h
        )
        pygame.draw.rect(surface, self.col_fore_l, fore_l)

        # RIGHT ARM (upper)
        arm_r = pygame.Rect(
            torso.right,
            torso.top + 4,
            self.arm_w,
            self.arm_h
        )
        pygame.draw.rect(surface, self.col_arm_r, arm_r)

        # RIGHT FOREARM
        fore_r = pygame.Rect(
            arm_r.left,
            arm_r.bottom,
            self.arm_w,
            self.arm_h
        )
        pygame.draw.rect(surface, self.col_fore_r, fore_r)

        # LEFT LEG (thigh)
        leg_l = pygame.Rect(
            px + (self.width//2 - self.leg_w - 2),
            torso.bottom,
            self.leg_w,
            self.leg_h
        )
        pygame.draw.rect(surface, self.col_leg_l, leg_l)

        # LEFT SHIN
        shin_l = pygame.Rect(
            leg_l.left,
            leg_l.bottom,
            self.leg_w,
            self.leg_h
        )
        pygame.draw.rect(surface, self.col_shin_l, shin_l)

        # RIGHT LEG (thigh)
        leg_r = pygame.Rect(
            px + (self.width//2 + 2),
            torso.bottom,
            self.leg_w,
            self.leg_h
        )
        pygame.draw.rect(surface, self.col_leg_r, leg_r)

        # RIGHT SHIN
        shin_r = pygame.Rect(
            leg_r.left,
            leg_r.bottom,
            self.leg_w,
            self.leg_h
        )
        pygame.draw.rect(surface, self.col_shin_r, shin_r)
