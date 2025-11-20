#VVVVVVVVVVVV IMPORTS AND GLOBAL CONFIG VVVVVVVV
import sys
import pygame
import random
import math

pygame.init()

WIDTH, HEIGHT = 960, 540
FPS = 60

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Intearth City Duel - Prototype")
CLOCK = pygame.time.Clock()

FONT_SMALL = pygame.font.SysFont("consolas", 16)
FONT_MED = pygame.font.SysFont("consolas", 20)

SKY_COLOR = (18, 14, 24)
GROUND_COLOR = (55, 44, 40)
UI_BG = (0, 0, 0, 180)

PLAYER_COLOR = (255, 215, 0)
ENEMY_COLOR = (255, 120, 40)
MERCHANT_COLOR = (120, 200, 255)
SWORD_COLOR = (230, 230, 230)
HITBOX_COLOR_DEBUG = (255, 0, 0, 120)

GRAVITY = 0.6
FRICTION = 0.80

GROUND_Y = HEIGHT - 60

WORLD_WIDTH = 2400  # side scroll area width per city
MAX_UNITS_PER_CITY = 20

DEBUG_HITBOXES = False
PROJECTILES = []  # global list of active projectiles
#^^^^^^^^^^^


#VVVVVVVVVVVV BALANCE CONFIG / STAGE SETTINGS VVVVVVVV
STAGE_SETTINGS = {
    1: {
        "enemy_hp": 20,
        "weapon_dmg_min": 10,
        "weapon_dmg_max": 16,
        "knockback_min": 2.0,
        "knockback_max": 4.0,
        "enemy_attack_delay_mult": 2.0,
        "allow_ranged_enemies": False,
    },
    2: {
        "enemy_hp": 40,
        "weapon_dmg_min": 12,
        "weapon_dmg_max": 22,
        "knockback_min": 2.5,
        "knockback_max": 4.5,
        "enemy_attack_delay_mult": 1.6,
        "allow_ranged_enemies": False,
    },
    3: {
        "enemy_hp": 60,
        "weapon_dmg_min": 15,
        "weapon_dmg_max": 28,
        "knockback_min": 3.0,
        "knockback_max": 5.0,
        "enemy_attack_delay_mult": 1.3,
        "allow_ranged_enemies": True,
    },
    4: {
        "enemy_hp": 80,
        "weapon_dmg_min": 18,
        "weapon_dmg_max": 36,
        "knockback_min": 3.5,
        "knockback_max": 5.5,
        "enemy_attack_delay_mult": 1.1,
        "allow_ranged_enemies": True,
    },
}

MELEE_WEAPON_NAMES = [
    "Short Sword",
    "Long Sword",
    "Battle Axe",
]

RARITY_THRESHOLDS = [
    (10, "green"),
    (18, "blue"),
    (26, "purple"),
    (34, "orange"),
    (44, "red"),
    (9999, "gold"),
]

RARITY_COLORS = {
    "green": (0, 220, 120),
    "blue": (80, 160, 255),
    "purple": (190, 90, 255),
    "orange": (255, 170, 60),
    "red": (255, 80, 80),
    "gold": (255, 220, 80),
}


def compute_item_rarity(power_score: float) -> str:
    for limit, name in RARITY_THRESHOLDS:
        if power_score <= limit:
            return name
    return "gold"
#^^^^^^^^^^^


#VVVVVVVVVVVV SIMPLE DATA CLASSES VVVVVVVV
class Item:
    def __init__(
        self,
        name,
        dmg=0,
        armor=0,
        atk_speed_bonus=0.0,
        knockback=0.0,
        price=10,
        visual=None,
        ranged=False,
    ):
        self.name = name
        self.dmg = dmg
        self.armor = armor
        self.atk_speed_bonus = atk_speed_bonus
        self.knockback = knockback
        self.price = max(1, int(price))
        self.visual = visual
        self.ranged = ranged

        power_score = (
            self.dmg
            + self.armor * 1.5
            + self.atk_speed_bonus * 10.0
            + self.knockback * 1.2
        )
        self.rarity = compute_item_rarity(power_score)

    def desc(self):
        parts = []
        if self.dmg:
            parts.append(f"Dmg+{self.dmg}")
        if self.armor:
            parts.append(f"Arm+{self.armor}")
        if self.atk_speed_bonus:
            parts.append(f"AS+{int(self.atk_speed_bonus * 100)}%")
        if self.knockback:
            parts.append(f"KB+{self.knockback:.1f}")
        if not parts:
            parts.append("No bonus")
        return ", ".join(parts)


class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)


class Ladder:
    def __init__(self, x, y, h, top_door=False, bottom_door=False):
        self.rect = pygame.Rect(x, y, 24, h)
        self.top_door = top_door
        self.bottom_door = bottom_door


class Door:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 40)
#^^^^^^^^^^^
class Projectile:
    """Simple straight-line projectile used by ranged weapons.

    - kind: 'wand', 'bow', or 'staff' (affects visuals and splash)
    - owner: Fighter that fired it (can't be hit by own projectile)
    - dmg, knockback, max_dist: combat stats
    """
    def __init__(self, x, y, vx, vy, dmg, knockback, max_dist, owner, kind, color, splash_radius=0):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.dmg = int(dmg)
        self.knockback = float(knockback)
        self.max_dist = float(max_dist)
        self.owner = owner
        self.kind = kind
        self.color = color
        self.splash_radius = float(splash_radius)
        self.traveled = 0.0
        self.alive = True

    def rect(self):
        # Small hitbox around the projectile center
        if self.kind == "staff":
            size = 14
        else:
            size = 10
        return pygame.Rect(int(self.x - size/2), int(self.y - size/2), size, size)

    def update(self, fighters):
        if not self.alive:
            return
        # Move
        self.x += self.vx
        self.y += self.vy
        self.traveled += abs(self.vx) + abs(self.vy)
        if self.traveled >= self.max_dist:
            self.alive = False
            return

        # Collision with fighters
        hit_target = None
        r = self.rect()
        for f in fighters:
            if f is self.owner or f.is_dead():
                continue
            if r.colliderect(f.rect):
                hit_target = f
                break

        if hit_target is not None:
            # Direct hit damage
            hit_target.take_hit(self.dmg)

            # Knockback
            if self.knockback != 0:
                direction = 1 if self.vx >= 0 else -1
                hit_target.vx += self.knockback * direction

            # Splash for staff-type projectiles
            if self.kind == "staff" and self.splash_radius > 0:
                cx, cy = r.center
                rad_sq = self.splash_radius * self.splash_radius
                for f in fighters:
                    if f is self.owner or f is hit_target or f.is_dead():
                        continue
                    dx = f.rect.centerx - cx
                    dy = f.rect.centery - cy
                    if dx*dx + dy*dy <= rad_sq:
                        # Splash does reduced damage
                        splash_dmg = max(1, int(self.dmg * 0.6))
                        f.take_hit(splash_dmg)

            self.alive = False

    def draw(self, surface, camera_x):
        if not self.alive:
            return
        cx = int(self.x - camera_x)
        cy = int(self.y)

        if self.kind == "wand":
            # Small glowing orb
            pygame.draw.circle(surface, self.color, (cx, cy), 4)
        elif self.kind == "bow":
            # Short horizontal line to suggest an arrow
            tail_x = cx - 6 if self.vx >= 0 else cx + 6
            head_x = cx + 6 if self.vx >= 0 else cx - 6
            pygame.draw.line(surface, self.color, (tail_x, cy), (head_x, cy), 3)
        elif self.kind == "staff":
            # Central orb with spikes
            pygame.draw.circle(surface, self.color, (cx, cy), 6)
            directions = [(8, 0), (-8, 0), (0, 8), (0, -8),
                          (6, 6), (6, -6), (-6, 6), (-6, -6)]
            for dx, dy in directions:
                pygame.draw.line(surface, self.color, (cx, cy), (cx + dx, cy + dy), 2)
        else:
            pygame.draw.circle(surface, self.color, (cx, cy), 3)
#^^^^^^^^^^^





#VVVVVVVVVVVV FIGHTER CLASS AND COMBAT LOGIC VVVVVVVV
class Fighter:
    def __init__(self, x, y, color, is_player=False, is_merchant=False):
        self.x = x
        self.y = y
        self.w = 26
        self.h = 70
        self.color = color
        self.is_player = is_player
        self.is_merchant = is_merchant

        self.vx = 0
        self.vy = 0
        self.facing = 1
        self.on_ground = False
        self.climbing = False

        self.speed = 4.5
        self.jump_speed = -11.0

        self.base_dmg = 5
        self.base_armor = 0
        self.base_attack_delay = 22

        self.weapon = None
        self.armor_item = None

        self.hp_max = 100
        self.hp = self.hp_max
        self.money = 0

        self.inventory = []

        self.attack_timer = 0
        self.attack_frame = 0
        self.attack_active = False
        self.attack_has_hit = False
        self.attack_type = None
        self.attack_anim_angle = 0.0

        self.ai_attack_cooldown = 0

        # regen system
        self.last_damage_time = 0
        self.regen_cooldown = 3000  # ms
        self.regen_interval = 1000  # ms
        self.regen_accumulator = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y - self.h), self.w, self.h)

    # ---------- STATS ----------
    def total_damage(self):
        dmg = self.base_dmg
        if self.weapon:
            dmg += self.weapon.dmg
        return max(1, dmg)

    def total_armor(self):
        a = self.base_armor
        if self.armor_item:
            a += self.armor_item.armor
        return max(0, a)

    def attack_delay(self):
        bonus = 0.0
        if self.weapon:
            bonus += self.weapon.atk_speed_bonus
        delay = self.base_attack_delay / (1.0 + bonus)
        return max(6, int(delay))

    def take_hit(self, dmg):
        reduced = max(0, dmg - self.total_armor())
        if reduced <= 0:
            reduced = 1
        self.hp -= reduced
        if self.hp < 0:
            self.hp = 0

        self.last_damage_time = pygame.time.get_ticks()
        self.regen_accumulator = 0

    def is_dead(self):
        return self.hp <= 0

    def update_regen(self, dt):
        if not self.is_player or self.is_dead():
            return

        time_since_dmg = pygame.time.get_ticks() - self.last_damage_time
        if time_since_dmg < self.regen_cooldown:
            return

        self.regen_accumulator += dt
        if self.regen_accumulator >= self.regen_interval:
            self.hp = min(self.hp + 1, self.hp_max)
            self.regen_accumulator = 0

    # ---------- ATTACK ----------
    def start_attack(self, attack_type="swing"):
        if self.attack_timer > 0:
            return

        # If this fighter has a ranged weapon, we treat the attack as a shot
        # and spawn a projectile instead of using a melee swing hitbox.
        if self.weapon and getattr(self.weapon, "ranged", False):
            attack_type = "shoot"
            spawn_projectile(self)

        self.attack_type = attack_type
        self.attack_timer = self.attack_delay()
        self.attack_frame = 0
        self.attack_active = False
        self.attack_has_hit = False
        self.attack_anim_angle = -0.8 * self.facing

    def update_attack_state(self):
        if self.attack_timer > 0:
            self.attack_timer -= 1
            self.attack_frame += 1

            start = int(self.attack_delay() * 0.3)
            end = int(self.attack_delay() * 0.7)
            self.attack_active = start <= self.attack_frame <= end

            t_norm = self.attack_frame / max(1, self.attack_delay())
            self.attack_anim_angle = -0.8 * self.facing + 1.6 * self.facing * t_norm

            if self.attack_timer == 0:
                self.attack_active = False
                self.attack_has_hit = False
                self.attack_type = None
                self.attack_anim_angle = 0.0

    def get_attack_hitbox(self):
        if not self.attack_active:
            return None

        # Ranged weapons do not use a melee hitbox – their damage comes from projectiles.
        if self.weapon and getattr(self.weapon, "ranged", False):
            return None

        base = self.rect
        length = 50
        blade_w = 12
        if self.facing == 1:
            x = base.centerx + 10
        else:
            x = base.centerx - 10 - blade_w
        y = base.centery - 10
        return pygame.Rect(
            x if self.facing == 1 else x - length,
            y - 6,
            length + blade_w,
            18
        )

    # ---------- PHYSICS ----------
    def apply_gravity(self):
        if not self.climbing:
            self.vy += GRAVITY
            if self.vy > 16:
                self.vy = 16

    def move_and_collide(self, platforms):
        self.x += self.vx
        self.y += self.vy

        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        feet = pygame.Rect(self.rect.left, self.rect.bottom - 5,
                           self.rect.width, 10)
        for p in platforms:
            if feet.colliderect(p.rect) and self.vy >= 0:
                self.y = p.rect.top
                self.vy = 0
                self.on_ground = True

        if self.x < 0:
            self.x = 0
            self.vx = 0
        if self.x + self.w > WORLD_WIDTH:
            self.x = WORLD_WIDTH - self.w
            self.vx = 0

    # ---------- LADDERS ----------
    def update_ladders(self, ladders, keys_up, keys_down):
        self.climbing = False
        r = self.rect
        for lad in ladders:
            if (
                r.centerx in range(lad.rect.left - 8, lad.rect.right + 8)
                and r.bottom >= lad.rect.top
                and r.top <= lad.rect.bottom
            ):
                if keys_up:
                    self.climbing = True
                    self.vy = -self.speed
                    self.y -= self.speed
                elif keys_down:
                    self.climbing = True
                    self.vy = self.speed
                    self.y += self.speed
                else:
                    if self.climbing:
                        self.vy = 0
                break

    # ---------- UPDATE PLAYER ----------
    def update_player(self, key_state, platforms, ladders):
        left = key_state[pygame.K_a]
        right = key_state[pygame.K_d]
        up = key_state[pygame.K_w]
        down = key_state[pygame.K_s]

        if left:
            self.vx = -self.speed
            self.facing = -1
        elif right:
            self.vx = self.speed
            self.facing = 1
        else:
            self.vx *= FRICTION
            if abs(self.vx) < 0.2:
                self.vx = 0

        self.update_ladders(ladders, up, down)

        if up and self.on_ground and not self.climbing:
            self.vy = self.jump_speed
            self.on_ground = False

        self.apply_gravity()
        self.move_and_collide(platforms)
        self.update_attack_state()

    # ---------- ENEMY AI ----------
    def update_enemy_ai(self, player, platforms, ladders):
        if self.is_merchant or self.is_dead():
            self.vx = 0
            self.update_attack_state()
            self.apply_gravity()
            self.move_and_collide(platforms)
            return

        aggro_range = 260

        dx = player.x - self.x
        dist = abs(dx)

        if dist > aggro_range:
            self.vx = 0
            self.update_attack_state()
            self.apply_gravity()
            self.move_and_collide(platforms)
            return

        self.facing = 1 if dx > 0 else -1

        if dist > 60:
            self.vx = self.speed * self.facing
        else:
            self.vx = 0

        if player.y < self.y - 30 and self.on_ground and random.random() < 0.02:
            self.vy = self.jump_speed

        if self.ai_attack_cooldown > 0:
            self.ai_attack_cooldown -= 1

        if dist < 90 and self.ai_attack_cooldown <= 0:
            self.start_attack("swing")
            self.ai_attack_cooldown = self.attack_delay() + 12

        self.apply_gravity()
        self.move_and_collide(platforms)
        self.update_attack_state()

    # ---------- DRAW ----------

    # ---------- DRAW ----------
    def draw(self, surface, camera_x, debug=False):
        r = self.rect.move(-camera_x, 0)

        # Body
        pygame.draw.rect(surface, self.color, r)
        head = pygame.Rect(r.centerx - 9, r.top - 18, 18, 18)
        pygame.draw.rect(surface, self.color, head)

        # Weapon anchor (player hand)
        hand_x = r.centerx + (8 * self.facing)
        hand_y = r.centery - 10

        if self.weapon:
            visual = (self.weapon.visual or "").lower()
            color = SWORD_COLOR

            if "staff" in visual:
                # Vertical staff with slight tilt based on movement speed.
                base_angle = -math.pi / 2  # straight up
                speed_norm = max(-1.0, min(1.0, self.vx / 8.0))
                tilt_max = 0.30  # radians of lean
                tilt = speed_norm * tilt_max
                if self.attack_type:
                    tilt *= 1.4
                angle = base_angle + tilt
                length = 60

                bottom_x = hand_x
                bottom_y = hand_y + 10
                top_x = bottom_x + math.cos(angle) * length
                top_y = bottom_y + math.sin(angle) * length

                # Staff shaft
                pygame.draw.line(surface, color,
                                 (bottom_x, bottom_y),
                                 (top_x, top_y), 4)
                # Small head at the top
                pygame.draw.circle(surface, color,
                                   (int(top_x), int(top_y - 4)), 5)

            elif "wand" in visual:
                # Short rod, angled slightly forward.
                length = 28
                base_angle = -0.4 * self.facing
                dx = math.cos(base_angle) * self.facing
                dy = math.sin(base_angle)
                tip_x = hand_x + dx * length
                tip_y = hand_y + dy * length
                pygame.draw.line(surface, color, (hand_x, hand_y),
                                 (tip_x, tip_y), 3)
                pygame.draw.circle(surface, color,
                                   (int(tip_x), int(tip_y)), 3)

            elif "bow" in visual:
                # D-shaped bow: string near hand, limbs forward.
                string_x = hand_x
                top_y = hand_y - 18
                bot_y = hand_y + 18

                if self.facing == 1:
                    limb_x = hand_x + 16
                else:
                    limb_x = hand_x - 16

                # String
                pygame.draw.line(surface, color,
                                 (string_x, top_y),
                                 (string_x, bot_y), 2)
                # Limbs
                pygame.draw.line(surface, color,
                                 (string_x, top_y),
                                 (limb_x, hand_y - 8), 3)
                pygame.draw.line(surface, color,
                                 (string_x, bot_y),
                                 (limb_x, hand_y + 8), 3)

            else:
                # Default melee weapons: short sword / long sword / axe.
                length = 46
                width = 4

                base_angle = 0.0 if not self.attack_type else self.attack_anim_angle
                dx = math.cos(base_angle) * self.facing
                dy = math.sin(base_angle)
                tip_x = hand_x + dx * length
                tip_y = hand_y + dy * length

                # Main blade / handle.
                pygame.draw.line(surface, color,
                                 (hand_x, hand_y),
                                 (tip_x, tip_y), width)

                # Decorate based on name.
                name = visual
                if "longsword" in name:
                    # Cross-guard near the hand.
                    guard_len = 10
                    perp_dx = -dy
                    perp_dy = dx
                    gx1 = hand_x + perp_dx * guard_len
                    gy1 = hand_y + perp_dy * guard_len
                    gx2 = hand_x - perp_dx * guard_len
                    gy2 = hand_y - perp_dy * guard_len
                    pygame.draw.line(surface, color,
                                     (gx1, gy1), (gx2, gy2), 3)

                if "axe" in name:
                    # Axe head rectangle near the tip.
                    head_len = 14
                    head_w = 12
                    hx = tip_x - dx * 6
                    hy = tip_y - dy * 6
                    rect = pygame.Rect(0, 0, head_len, head_w)
                    rect.center = (hx + dx * head_len * 0.2,
                                   hy + dy * head_len * 0.2)
                    rect = rect.move(-camera_x, 0)
                    pygame.draw.rect(surface, color, rect)

        if debug:
            hb = self.get_attack_hitbox()
            if hb:
                hb_cam = hb.move(-camera_x, 0)
                s = pygame.Surface(hb_cam.size, pygame.SRCALPHA)
                s.fill(HITBOX_COLOR_DEBUG)
                surface.blit(s, hb_cam.topleft)
#^^^^^^^^^^^


#VVVVVVVVVVVV CITY GENERATION VVVVVVVV
class City:
    def __init__(self, stage, difficulty_factor=1.0, seed=None):
        self.stage = stage
        self.difficulty_factor = difficulty_factor
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.platforms = []
        self.ladders = []
        self.doors = []
        self.units = []
        self.bg_buildings_back = []
        self.bg_buildings_front = []
        self.generate()

    def generate_background(self):
        random.seed(self.seed)
        self.bg_buildings_back.clear()
        self.bg_buildings_front.clear()

        x = 0
        while x < WORLD_WIDTH:
            w = random.randint(120, 260)
            h = random.randint(140, 260)
            self.bg_buildings_back.append(
                pygame.Rect(x, GROUND_Y - h + 40, w, h)
            )
            x += w + random.randint(40, 90)

        x = 0
        while x < WORLD_WIDTH:
            w = random.randint(80, 200)
            h = random.randint(80, 180)
            self.bg_buildings_front.append(
                pygame.Rect(x, GROUND_Y - h + 50, w, h)
            )
            x += w + random.randint(30, 70)

    def generate_platforms_ladders_doors(self):
        self.platforms.clear()
        self.ladders.clear()
        self.doors.clear()

        random.seed(self.seed + 1)

        self.platforms.append(Platform(0, GROUND_Y, WORLD_WIDTH, 20))

        x = 80
        while x < WORLD_WIDTH - 200:
            height = random.choice([GROUND_Y - 120,
                                    GROUND_Y - 180,
                                    GROUND_Y - 240])
            width = random.randint(120, 220)
            plat = Platform(x, height, width, 18)
            self.platforms.append(plat)

            ladd_x = plat.rect.centerx - 12
            ladder_h = GROUND_Y - plat.rect.top
            ladder = Ladder(ladd_x, plat.rect.top, ladder_h,
                            top_door=True, bottom_door=True)
            self.ladders.append(ladder)

            self.doors.append(Door(plat.rect.left + 8, plat.rect.top - 40))

            if random.random() < 0.6:
                bridge_w = random.randint(80, 160)
                bridge_x = plat.rect.right + 20
                bridge_y = plat.rect.top - 40
                self.platforms.append(
                    Platform(bridge_x, bridge_y, bridge_w, 16)
                )
                self.doors.append(Door(bridge_x + bridge_w - 40, bridge_y - 40))

            x += width + random.randint(120, 260)

    def generate_weapon_for_stage(self, stage_settings):
        dmg_min = stage_settings["weapon_dmg_min"]
        dmg_max = stage_settings["weapon_dmg_max"]
        kb_min = stage_settings["knockback_min"]
        kb_max = stage_settings["knockback_max"]

        dmg = random.randint(dmg_min, dmg_max)
        knockback = round(random.uniform(kb_min, kb_max), 1)
        atk_speed_bonus = random.uniform(0.0, 0.3)
        name = random.choice(MELEE_WEAPON_NAMES)

        visual_map = {
            "Short Sword": "shortsword",
            "Long Sword": "longsword",
            "Battle Axe": "axe",
        }
        visual = visual_map.get(name, None)

        price = dmg * 6 + int(knockback * 4) + int(atk_speed_bonus * 50)

        return Item(
            name=name,
            dmg=dmg,
            armor=0,
            atk_speed_bonus=atk_speed_bonus,
            knockback=knockback,
            price=price,
            visual=visual,
        )

    def generate_armor_for_stage(self, stage_settings):
        base = stage_settings["enemy_hp"] // 10
        armor_val = random.randint(max(0, base - 1), base + 2)
        armor_val = max(0, armor_val)
        price = armor_val * 10 + 10
        return Item(
            name="Guard Armor",
            dmg=0,
            armor=armor_val,
            atk_speed_bonus=0.0,
            knockback=0.0,
            price=price,
        )

    def generate_units(self, player):
        self.units.clear()
        random.seed(self.seed + 2)

        settings = STAGE_SETTINGS.get(self.stage, STAGE_SETTINGS[4])

        non_ground_plats = [p for p in self.platforms if p.rect.top < GROUND_Y]
        if not non_ground_plats:
            return

        # one enemy near spawn (x < WIDTH)
        start_plats = [p for p in non_ground_plats if p.rect.left < WIDTH - 200]
        if not start_plats:
            start_plats = non_ground_plats
        first_plat = random.choice(start_plats)

        enemy_positions = []

        def spawn_fighter_on_platform(plat, is_merchant=False):
            spawn_x = plat.rect.left + 20 + random.randint(0, max(4, plat.rect.width - 60))
            spawn_y = plat.rect.top
            color = MERCHANT_COLOR if is_merchant else ENEMY_COLOR
            f = Fighter(spawn_x, spawn_y, color, is_player=False, is_merchant=is_merchant)

            f.hp_max = settings["enemy_hp"]
            f.hp = f.hp_max
            f.base_attack_delay = int(f.base_attack_delay * settings["enemy_attack_delay_mult"])

            weapon = self.generate_weapon_for_stage(settings)
            armor_item = self.generate_armor_for_stage(settings)
            f.weapon = weapon
            f.armor_item = armor_item
            f.inventory.append(weapon)
            f.inventory.append(armor_item)
            f.money = random.randint(5, 40)
            return f

        first_enemy = spawn_fighter_on_platform(first_plat, is_merchant=False)
        self.units.append(first_enemy)
        enemy_positions.append(first_enemy.x)

        if self.stage == 1:
            max_units = min(MAX_UNITS_PER_CITY, 10)
        else:
            max_units = MAX_UNITS_PER_CITY

        far_plats = [p for p in non_ground_plats if p.rect.left > WIDTH]
        if not far_plats:
            far_plats = non_ground_plats

        min_spacing = 260

        # Total fighters per Area (enemies + merchant) will be approximately
        # max_units. We reserve exactly one slot for the merchant.
        enemy_total = max(1, max_units - 1)

        # Spawn additional ENEMIES only (no merchants here).
        for i in range(1, enemy_total):
            for _ in range(20):
                plat = random.choice(far_plats)
                f = spawn_fighter_on_platform(plat, is_merchant=False)
                if all(abs(f.x - ex) >= min_spacing for ex in enemy_positions):
                    self.units.append(f)
                    enemy_positions.append(f.x)
                    break

        # Spawn EXACTLY ONE merchant on a non-ground platform.
        merchant_plats = [p for p in non_ground_plats if p.rect.left > 80]
        if not merchant_plats:
            merchant_plats = non_ground_plats
        m_plat = random.choice(merchant_plats)
        merchant = spawn_fighter_on_platform(m_plat, is_merchant=True)
        self.units.append(merchant)

    def generate(self):
        self.generate_background()
        self.generate_platforms_ladders_doors()

    def draw_background(self, surface, camera_x):
        surface.fill(SKY_COLOR)
        for b in self.bg_buildings_back:
            pygame.draw.rect(surface, (26, 20, 34), b.move(-camera_x, 0))
        for b in self.bg_buildings_front:
            pygame.draw.rect(surface, (36, 26, 40), b.move(-camera_x, 0))
        pygame.draw.rect(surface, GROUND_COLOR,
                         pygame.Rect(0 - camera_x, GROUND_Y,
                                     WORLD_WIDTH, HEIGHT - GROUND_Y))

    def draw_static_level(self, surface, camera_x):
        for p in self.platforms:
            pygame.draw.rect(surface, (90, 70, 70),
                             p.rect.move(-camera_x, 0))
        for lad in self.ladders:
            pygame.draw.rect(surface, (150, 120, 80),
                             lad.rect.move(-camera_x, 0))
        for d in self.doors:
            dr = d.rect.move(-camera_x, 0)
            pygame.draw.rect(surface, (80, 60, 40), dr)
            pygame.draw.rect(surface, (130, 110, 80),
                             dr.inflate(-6, -6))
#^^^^^^^^^^^


#VVVVVVVVVVVV SHOP UI VVVVVVVV
class ShopUI:
    def __init__(self):
        self.active = False
        self.merchant = None
        self.player = None
        self.focus = "shop"
        self.sel_index = 0

    def open(self, player, merchant):
        self.active = True
        self.player = player
        self.merchant = merchant
        self.focus = "shop"
        self.sel_index = 0

    def close(self):
        self.active = False
        self.merchant = None
        self.player = None

    def handle_input(self, events):
        if not self.active:
            return
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.close()
                elif e.key == pygame.K_TAB:
                    self.focus = "inv" if self.focus == "shop" else "shop"
                    self.sel_index = 0
                elif e.key == pygame.K_UP:
                    self.sel_index = max(0, self.sel_index - 1)
                elif e.key == pygame.K_DOWN:
                    max_len = len(self.current_list()) - 1
                    self.sel_index = min(max_len, self.sel_index + 1)
                elif e.key == pygame.K_b and self.focus == "shop":
                    self.buy_selected()
                elif e.key == pygame.K_s and self.focus == "inv":
                    self.sell_selected()

    def current_list(self):
        if not self.active:
            return []
        return self.merchant.inventory if self.focus == "shop" else self.player.inventory

    def buy_selected(self):
        lst = self.merchant.inventory
        if not lst or self.sel_index >= len(lst):
            return
        item = lst[self.sel_index]
        if self.player.money >= item.price:
            self.player.money -= item.price
            self.merchant.money += item.price
            self.player.inventory.append(item)
            del lst[self.sel_index]
            self.sel_index = max(0, self.sel_index - 1)

    def sell_selected(self):
        lst = self.player.inventory
        if not lst or self.sel_index >= len(lst):
            return
        item = lst[self.sel_index]
        if self.merchant.money >= item.price:
            self.merchant.money -= item.price
            self.player.money += item.price
            self.merchant.inventory.append(item)
            del lst[self.sel_index]
            self.sel_index = max(0, self.sel_index - 1)

    def draw(self, surface):
        if not self.active:
            return

        panel = pygame.Surface((WIDTH - 120, HEIGHT - 120), pygame.SRCALPHA)
        panel.fill(UI_BG)
        px, py = 60, 60
        surface.blit(panel, (px, py))

        title = FONT_MED.render("Trade", True, (220, 220, 220))
        surface.blit(title, (px + 20, py + 10))

        money_text = FONT_SMALL.render(
            f"Player money: {self.player.money}   Merchant money: {self.merchant.money}",
            True, (230, 230, 230)
        )
        surface.blit(money_text, (px + 20, py + 40))

        shop_label = FONT_SMALL.render(
            f"Merchant items [{'active' if self.focus == 'shop' else '   '}]", True,
            (200, 200, 200)
        )
        inv_label = FONT_SMALL.render(
            f"Your items [{'active' if self.focus == 'inv' else '   '}]", True,
            (200, 200, 200)
        )
        surface.blit(shop_label, (px + 20, py + 70))
        surface.blit(inv_label, (px + (WIDTH // 2) - 40, py + 70))

        def draw_list(items, ox, oy, selected):
            for i, it in enumerate(items):
                y = oy + i * 20
                col = (255, 255, 0) if i == selected else (220, 220, 220)
                name = FONT_SMALL.render(
                    f"{it.name} [{it.price}] ({it.desc()})", True, col)
                surface.blit(name, (ox, y))

        draw_list(self.merchant.inventory, px + 20, py + 100,
                  self.sel_index if self.focus == "shop" else -1)
        draw_list(self.player.inventory, px + (WIDTH // 2) - 40,
                  py + 100, self.sel_index if self.focus == "inv" else -1)

        help1 = FONT_SMALL.render("Up/Down move, Tab swap column, B buy, S sell, Esc exit",
                                  True, (210, 210, 210))
        surface.blit(help1, (px + 20, py + HEIGHT - 140))
#^^^^^^^^^^^


#VVVVVVVVVVVV PAUSE / INVENTORY MENU UI VVVVVVVV
class PauseMenuUI:
    def __init__(self):
        self.active = False
        self.player = None
        self.entries = []
        self.selected_index = 0
        self.request_quit = False

    def open(self, player):
        self.active = True
        self.player = player
        self.refresh_entries()
        self.selected_index = 0
        self.request_quit = False

    def close(self):
        self.active = False
        self.player = None
        self.entries = []
        self.request_quit = False

    def refresh_entries(self):
        if not self.player:
            self.entries = []
            return
        self.entries = list(self.player.inventory) + ["Quit Game"]

    def handle_key(self, e):
        if not self.active:
            return

        if e.key == pygame.K_ESCAPE:
            self.close()
            return

        if e.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)

        elif e.key == pygame.K_DOWN:
            self.selected_index = min(len(self.entries) - 1, self.selected_index + 1)

        elif e.key == pygame.K_RETURN:
            self.activate_selection()

    def activate_selection(self):
        if not self.entries:
            return
        entry = self.entries[self.selected_index]
        if isinstance(entry, Item):
            self.equip_item(entry)
        elif isinstance(entry, str) and entry == "Quit Game":
            self.request_quit = True

    def equip_item(self, item):
        if not self.player:
            return
        if item.dmg > 0:
            self.player.weapon = item
        elif item.armor > 0:
            self.player.armor_item = item
        self.refresh_entries()

    def draw(self, surface):
        if not self.active:
            return

        panel = pygame.Rect(WIDTH//2 - 260, HEIGHT//2 - 220, 520, 440)
        pygame.draw.rect(surface, (10, 10, 20), panel)
        pygame.draw.rect(surface, (80, 80, 140), panel, 3)

        title = FONT_MED.render("PAUSE / INVENTORY", True, (255, 255, 255))
        surface.blit(title, (panel.x + 140, panel.y + 10))

        y = panel.y + 60
        for i, entry in enumerate(self.entries):
            is_sel = (i == self.selected_index)
            prefix = "* " if is_sel else "  "
            if isinstance(entry, Item):
                label = entry.name
                if entry.dmg:
                    label += f" {entry.dmg} Dmg"
                if entry.armor:
                    label += f" {entry.armor} Arm"
                if entry is self.player.weapon or entry is self.player.armor_item:
                    label += " [Equipped]"
            else:
                label = entry

            col = (255, 255, 180) if is_sel else (210, 210, 210)
            txt = FONT_SMALL.render(prefix + label, True, col)
            surface.blit(txt, (panel.x + 30, y))
            y += 26

        help_txt = FONT_SMALL.render("Up/Down select, Enter equip/use, Esc close", True, (200, 200, 200))
        surface.blit(help_txt, (panel.x + 30, panel.y + panel.height - 40))
#^^^^^^^^^^^


#VVVVVVVVVVVV HELPERS (PLAYER, MERCHANT, COMBAT) VVVVVVVV
def spawn_projectile(shooter):
    """Creates a projectile based on the shooter's current ranged weapon."""
    if not shooter.weapon or not getattr(shooter.weapon, "ranged", False):
        return

    visual = (shooter.weapon.visual or "").lower()
    if "bow" in visual:
        kind = "bow"
        speed = 10.0
        max_dist = 520.0
        dmg_mult = 1.0
        splash_radius = 0.0
    elif "staff" in visual:
        kind = "staff"
        speed = 6.0
        max_dist = 380.0
        dmg_mult = 1.3
        splash_radius = 60.0
    else:
        kind = "wand"
        speed = 14.0
        max_dist = 260.0
        dmg_mult = 0.9
        splash_radius = 0.0

    dmg = max(1, int(shooter.total_damage() * dmg_mult))
    knockback = shooter.weapon.knockback if shooter.weapon else 2.0

    facing = shooter.facing if shooter.facing != 0 else 1
    vx = speed * facing
    vy = 0.0

    r = shooter.rect
    x = r.centerx + facing * 20
    y = r.centery - 15

    color = (255, 255, 255)
    if shooter.weapon and hasattr(shooter.weapon, "rarity"):
        color = RARITY_COLORS.get(shooter.weapon.rarity, color)

    proj = Projectile(x, y, vx, vy, dmg, knockback, max_dist, shooter, kind, color, splash_radius)
    PROJECTILES.append(proj)

def choose_starting_weapon():
    selecting = True
    options = [
        ("Short Sword", "shortsword"),
        ("Long Sword", "longsword"),
        ("Axe", "axe"),
        ("Bow", "bow"),
        ("Magic Staff", "staff"),
        ("Magic Wand", "wand")
    ]
    index = 0

    while selecting:
        SCREEN.fill((10, 10, 10))
        title = FONT_MED.render("Choose Your Starting Weapon", True, (255, 255, 255))
        SCREEN.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        y = 180
        for i, (name, code) in enumerate(options):
            color = (255, 255, 0) if i == index else (200, 200, 200)
            txt = FONT_SMALL.render(name, True, color)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, y))
            y += 40

        info = FONT_SMALL.render("Up/Down to choose, Enter to confirm, Esc to quit", True, (180, 180, 180))
        SCREEN.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT - 80))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif e.key == pygame.K_UP:
                    index = (index - 1) % len(options)
                elif e.key == pygame.K_DOWN:
                    index = (index + 1) % len(options)
                elif e.key == pygame.K_RETURN:
                    return options[index][1]


def generate_initial_player():
    chosen = choose_starting_weapon()

    p = Fighter(80, GROUND_Y, PLAYER_COLOR, is_player=True)

    starter_armor = Item("Cloth Armor", dmg=0, armor=2,
                         atk_speed_bonus=0.0, knockback=0.0, price=0)
    p.armor_item = starter_armor
    p.inventory.append(starter_armor)

    if chosen == "shortsword":
        w = Item("Short Sword", dmg=8, armor=0,
                 atk_speed_bonus=0.10, knockback=3, price=0,
                 visual="shortsword")
    elif chosen == "longsword":
        w = Item("Long Sword", dmg=12, armor=0,
                 atk_speed_bonus=0.00, knockback=4, price=0,
                 visual="longsword")
    elif chosen == "axe":
        w = Item("Axe", dmg=16, armor=0,
                 atk_speed_bonus=-0.10, knockback=5, price=0,
                 visual="axe")
    elif chosen == "bow":
        w = Item("Bow", dmg=6, armor=0,
                 atk_speed_bonus=0.20, knockback=2, price=0,
                 visual="bow", ranged=True)
    elif chosen == "staff":
        w = Item("Magic Staff", dmg=10, armor=0,
                 atk_speed_bonus=0.05, knockback=2, price=0,
                 visual="staff", ranged=True)
    elif chosen == "wand":
        w = Item("Magic Wand", dmg=5, armor=0,
                 atk_speed_bonus=0.30, knockback=1, price=0,
                 visual="wand", ranged=True)
    else:
        w = Item("Starter Blade", dmg=5, armor=0,
                 atk_speed_bonus=0.0, knockback=2.0, price=0,
                 visual="shortsword")

    p.weapon = w
    p.inventory.append(w)
    p.money = 20
    return p


def find_nearby_merchant(player, units):
    pr = player.rect
    for u in units:
        if u.is_merchant and not u.is_dead():
            if pr.colliderect(u.rect.inflate(60, 10)):
                return u
    return None


def handle_combat_between(attacker, defender):
    hb = attacker.get_attack_hitbox()
    if hb and not attacker.attack_has_hit and hb.colliderect(defender.rect):
        defender.take_hit(attacker.total_damage())
        attacker.attack_has_hit = True
#^^^^^^^^^^^


#VVVVVVVVVVVV MAIN GAME LOOP VVVVVVVV
def main():
    global DEBUG_HITBOXES

    player = generate_initial_player()
    current_area = 1

    city = City(stage=current_area, difficulty_factor=1.0)
    city.generate_units(player)

    camera_x = 0

    shop_ui = ShopUI()
    pause_menu = PauseMenuUI()

    running = True
    while running:
        dt = CLOCK.tick(FPS)
        events = pygame.event.get()
        key_state = pygame.key.get_pressed()

        # ---- EVENT HANDLING ----
        for e in events:
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:

                if e.key == pygame.K_ESCAPE:
                    if pause_menu.active:
                        pause_menu.close()
                    elif shop_ui.active:
                        shop_ui.close()
                    else:
                        pause_menu.open(player)

                elif pause_menu.active:
                    pause_menu.handle_key(e)

                elif shop_ui.active:
                    shop_ui.handle_input([e])

                else:
                    if e.key == pygame.K_SPACE:
                        player.start_attack("swing")
                    elif e.key == pygame.K_F1:
                        DEBUG_HITBOXES = not DEBUG_HITBOXES
                    elif e.key == pygame.K_e:
                        m = find_nearby_merchant(player, city.units)
                        if m and not m.is_dead():
                            shop_ui.open(player, m)

        if pause_menu.request_quit:
            running = False

        # ---- PAUSE: STOP SIMULATION ----
        if pause_menu.active or shop_ui.active:
            # only draw, no sim
            pass
        else:
            # ---- PLAYER UPDATE ----
            player.update_player(key_state, city.platforms, city.ladders)
            player.update_regen(dt)

            # ---- ENEMY AI ----
            for u in city.units:
                if not u.is_dead():
                    u.update_enemy_ai(player, city.platforms, city.ladders)

            # ---- PROJECTILES ----
            update_projectiles(PROJECTILES, player, city.units)

            # ---- COMBAT ----
            for u in city.units:
                if not u.is_dead():
                    handle_combat_between(player, u)
                    handle_combat_between(u, player)

            # ---- LOOT / CLEANUP ----
            for u in city.units:
                if u.is_dead() and not u.is_merchant and u.money > 0:
                    player.money += u.money
                    u.money = 0
            city.units = [u for u in city.units if not (u.is_dead() and not u.is_merchant)]

            # ---- CAMERA ----
            camera_x = max(0, min(int(player.x) - WIDTH // 2, WORLD_WIDTH - WIDTH))

            # ---- AREA TRANSITION ----
            if player.x + player.w >= WORLD_WIDTH - 5:
                current_area += 1
                diff = 1.0 + 0.2 * (current_area - 1)
                city = City(stage=current_area, difficulty_factor=diff)
                city.generate_units(player)
                player.x = 80
                player.y = GROUND_Y
                camera_x = 0

        # ---- DRAWING ----
        city.draw_background(SCREEN, camera_x)
        city.draw_static_level(SCREEN, camera_x)

        for u in city.units:
            if not u.is_dead():
                u.draw(SCREEN, camera_x, debug=DEBUG_HITBOXES)

        # Draw projectiles after units so they appear above the level but below UI
        for proj in PROJECTILES:
            proj.draw(SCREEN, camera_x)

        if not player.is_dead():
            player.draw(SCREEN, camera_x, debug=DEBUG_HITBOXES)

        hud_y = 8
        SCREEN.blit(
            FONT_SMALL.render(f"HP: {player.hp}/{player.hp_max}", True, (255, 255, 255)),
            (10, hud_y)
        )
        SCREEN.blit(
            FONT_SMALL.render(
                f"Dmg: {player.total_damage()}  Arm: {player.total_armor()}  Delay: {player.attack_delay()}f",
                True, (220, 220, 220)
            ),
            (10, hud_y + 20)
        )
        SCREEN.blit(
            FONT_SMALL.render(
                f"Money: {player.money}   Area: {current_area}",
                True, (255, 255, 0)
            ),
            (10, hud_y + 40)
        )

        if find_nearby_merchant(player, city.units) and not shop_ui.active and not pause_menu.active:
            hint = FONT_SMALL.render("Press E to trade", True, (200, 255, 200))
            SCREEN.blit(hint, (WIDTH // 2 - 60, HEIGHT - 40))

        if player.is_dead():
            over = FONT_MED.render("You have fallen. Esc to open menu / quit.", True, (255, 80, 80))
            SCREEN.blit(
                over,
                (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2)
            )

        shop_ui.draw(SCREEN)
        pause_menu.draw(SCREEN)

        pygame.display.flip()

    pygame.quit()
#^^^^^^^^^^^




# ===== PROJECTILE HELPERS =====
def update_projectiles(projectiles, player, units):
    fighters = [player] + list(units)
    # iterate copy
    for p in list(projectiles):
        p.update(fighters)
    # cleanup
    projectiles[:] = [p for p in projectiles if p.alive]

if __name__ == "__main__":
    main()
