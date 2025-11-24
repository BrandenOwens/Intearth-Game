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
ENEMY_COLOR = (255, 120, 40)  # Base color, enemies will have random variations
MERCHANT_COLOR = (120, 200, 255)
NPC_COLOR = (100, 150, 255)  # Blue for friendly NPCs
DOG_COLOR = (139, 90, 43)  # Brown for dog
SWORD_COLOR = (230, 230, 230)
HITBOX_COLOR_DEBUG = (255, 0, 0, 120)

GRAVITY = 0.6
FRICTION = 0.80

GROUND_Y = HEIGHT - 60

WORLD_WIDTH = 2400  # side scroll area width per city
MAX_UNITS_PER_CITY = 20

DEBUG_HITBOXES = False
PROJECTILES = []  # global list of active projectiles
ENEMY_PROJECTILE_LEASH = 520  # px distance from shooter before despawn
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
        heal_amount=0,
        is_potion=False,
        count=1,
    ):
        self.name = name
        self.dmg = dmg
        self.armor = armor
        self.atk_speed_bonus = atk_speed_bonus
        self.knockback = knockback
        self.price = max(1, int(price))
        self.visual = visual
        self.ranged = ranged
        self.heal_amount = heal_amount
        self.is_potion = is_potion
        self.count = count  # For stacking potions

        power_score = (
            self.dmg
            + self.armor * 1.5
            + self.atk_speed_bonus * 10.0
            + self.knockback * 1.2
        )
        self.rarity = compute_item_rarity(power_score)

    def desc(self):
        parts = []
        if self.is_potion:
            parts.append(f"Heal+{self.heal_amount}")
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


class Quest:
    """Represents a quest that the player can complete."""
    def __init__(self, quest_type, npc, description, target_building=None, target_floor=None, dog=None, target_stage=None):
        self.quest_type = quest_type  # "defeat_enemies", "find_dog", or "save_city"
        self.npc = npc  # The NPC who gave the quest
        self.description = description
        self.status = "offered"  # "offered", "active", "completed", "failed"
        self.target_building = target_building  # Building where quest takes place
        self.target_floor = target_floor  # Floor where NPC/dog is
        self.dog = dog  # Dog entity for find_dog quest
        self.initial_enemy_count = 0  # For defeat_enemies quest
        self.companion_npc = None  # NPC that follows player for defeat_enemies quest
        self.target_stage = target_stage  # For save_city quest - which stage to clear
        self.reward_money = 0  # Gold reward for completing quest


class PickupNotification:
    """Temporary notification for picked up items."""
    def __init__(self, text):
        self.text = text
        self.timer = 180  # 3 seconds at 60 FPS
        self.alpha = 255


class Dog:
    """Dog entity that follows the player."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.w = 20
        self.h = 20
        self.vx = 0
        self.vy = 0
        self.follow_player = None  # Player to follow
        self.follow_distance = 50  # Distance to maintain from player
        self.speed = 3.0
        self.on_ground = False
        self.inside_building = None  # Which building the dog is in
        self.building_floor_num = 0  # Which floor the dog is on
        self.hit_flash = 0  # Flash timer when hit
        self.hp = 50  # Dog has some HP
        self.hp_max = 50
        
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y - self.h), self.w, self.h)
    
    def update(self, player, platforms, building_bounds=None):
        """Update dog position to follow player."""
        if not player or player.is_dead():
            return
        
        # Calculate distance to player
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.sqrt(dx*dx + dy*dy) if dx != 0 or dy != 0 else 0
        
        # Move towards player if too far
        if dist > self.follow_distance:
            if dist > 0:
                self.vx = (dx / dist) * self.speed
            else:
                self.vx = 0
        else:
            self.vx *= 0.8  # Slow down when close
        
        # Apply gravity
        self.vy += GRAVITY
        if self.vy > 16:
            self.vy = 16
        
        # Move
        self.x += self.vx
        self.y += self.vy
        
        # Collision with ground/platforms
        if building_bounds:
            building_x, building_y, building_width, floor_y, ceiling_y = building_bounds
            if self.y >= floor_y:
                self.y = floor_y
                self.vy = 0
                self.on_ground = True
            else:
                self.on_ground = False
        
        # Platform collision
        feet = pygame.Rect(self.rect.left, self.rect.bottom - 5, self.rect.width, 10)
        for p in platforms:
            if feet.colliderect(p.rect) and self.vy >= 0:
                self.y = p.rect.top
                self.vy = 0
                self.on_ground = True
                break
    
    def draw(self, surface, camera_x, camera_y=0):
        """Draw the dog."""
        r = self.rect.move(-camera_x, -camera_y)
        # Flash red if hit (temporary effect)
        draw_color = DOG_COLOR if not hasattr(self, 'hit_flash') or self.hit_flash <= 0 else (255, 100, 100)
        
        # Simple dog shape - body
        pygame.draw.ellipse(surface, draw_color, r)
        # Head
        head = pygame.Rect(r.centerx - 6, r.top - 8, 12, 12)
        pygame.draw.ellipse(surface, draw_color, head)
        # Ears (black)
        pygame.draw.ellipse(surface, (0, 0, 0), (r.centerx - 8, r.top - 6, 6, 8))
        pygame.draw.ellipse(surface, (0, 0, 0), (r.centerx + 2, r.top - 6, 6, 8))
        # Eyes (black)
        pygame.draw.circle(surface, (0, 0, 0), (r.centerx - 3, r.top - 4), 2)
        pygame.draw.circle(surface, (0, 0, 0), (r.centerx + 3, r.top - 4), 2)
        # Nose (black)
        pygame.draw.circle(surface, (0, 0, 0), (r.centerx, r.top - 1), 3)
        # Tail
        tail_x = r.right - 5
        tail_y = r.centery
        pygame.draw.line(surface, draw_color, (r.right, tail_y), (tail_x, tail_y - 8), 3)
        
        # Draw "woof" text above dog
        woof_text = FONT_SMALL.render("woof", True, (255, 255, 200))
        text_rect = woof_text.get_rect(center=(r.centerx, r.top - 30))
        # Background for text
        bg_rect = pygame.Rect(text_rect.x - 5, text_rect.y - 2, text_rect.width + 10, text_rect.height + 4)
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect)
        surface.blit(woof_text, text_rect)


class Building:
    """A skyscraper with multiple floors that the player can enter."""
    def __init__(self, x, y, width, num_floors):
        self.x = x
        self.y = y  # Bottom of building
        self.width = width  # Very wide - 20 people side by side
        self.num_floors = num_floors
        self.floor_height = 160  # Height of each floor (fits two people stacked)
        self.total_height = num_floors * self.floor_height
        
        # Exterior appearance
        self.exterior_rect = pygame.Rect(x, y - self.total_height, width, self.total_height)
        
        # Interior floors - each floor has enemies, containers, background assets, elevator doors
        self.floors = []
        for i in range(num_floors):
            floor_y = y - (i + 1) * self.floor_height
            self.floors.append({
                'floor_num': i,
                'y': floor_y,
                'enemies': [],  # Will be populated with Fighter objects (in apartments only)
                'apartment_enemies': [],  # Enemies in the apartment room
                'containers': [],  # Lootable containers (chests, dressers, wardrobes) - in apartments only
                'background_assets': [],  # Decorative items (chairs, plants, TVs) - in halls
                'apartment_assets': [],  # Furniture in apartment rooms (bed, dresser, etc.)
                'elevator_up_x': x + width - 30,  # Up elevator on far right side
                'elevator_down_x': x + 30,  # Down elevator on far left side
                'elevator_exit_x': x + 60,  # Exit elevator (double down arrow) - spaced from down elevator
                'apartment_door_x': x + width // 2,  # Apartment door in middle of floor
                'windows': [],  # Window positions for background visibility
                'has_apartment': True  # Each floor has an apartment
            })
        
        # Entry door (first floor, center) - bigger sliding glass door style, at ground level
        self.entry_door_x = x + width // 2
        self.entry_door_y = y  # At ground level (y is GROUND_Y, bottom of building)
        self.entry_door_width = 60  # Wider sliding glass door
        self.entry_door_height = 80  # Taller door
        
        # Generate windows for each floor
        self.generate_windows()
    
    def generate_windows(self):
        """Generate window positions for each floor - occasional windows only."""
        window_width = 8
        window_height = 12
        window_spacing = 40  # Wider spacing for occasional windows
        
        for floor in self.floors:
            windows = []
            # Back wall windows (left side of building interior) - occasional only
            for wx in range(self.x + 10, self.x + self.width - 50, window_spacing):
                if random.random() < 0.25:  # 25% chance of window (occasional)
                    windows.append({
                        'x': wx,
                        'y': floor['y'] + 20,
                        'width': window_width,
                        'height': window_height
                    })
            floor['windows'] = windows
    
    @property
    def rect(self):
        return self.exterior_rect
    
    def get_floor_at_y(self, y):
        """Get the floor number at a given y position."""
        if y > self.y or y < self.y - self.total_height:
            return None
        floor_num = int((self.y - y) / self.floor_height)
        return min(floor_num, self.num_floors - 1)
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

        if self.owner and not self.owner.is_player:
            owner_rect = self.owner.rect
            dx = (self.x) - owner_rect.centerx
            dy = (self.y) - owner_rect.centery
            if dx * dx + dy * dy >= ENEMY_PROJECTILE_LEASH * ENEMY_PROJECTILE_LEASH:
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
            if hit_target.was_merchant and not hit_target.merchant_hostile:
                hit_target.become_hostile(self.owner)

            # Knockback - push target away from projectile direction
            if self.knockback > 0:
                # Use projectile velocity direction (same as attacker's facing direction)
                direction = 1 if self.vx >= 0 else -1
                # Apply knockback with timer - reduced by 70% (30% of original)
                hit_target.knockback_vx = self.knockback * direction * 2.4  # 30% of 8.0 = 2.4x multiplier
                hit_target.knockback_timer = 20  # Knockback lasts 20 frames

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

    def draw(self, surface, camera_x, camera_y=0):
        if not self.alive:
            return
        cx = int(self.x - camera_x)
        cy = int(self.y - camera_y)

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
    def __init__(self, x, y, color, is_player=False, is_merchant=False, is_boss=False):
        self.x = x
        self.y = y
        # Boss units are bigger
        if is_boss:
            self.w = 35  # 35% bigger width
            self.h = 90  # 28% bigger height
        else:
            self.w = 26
            self.h = 70
        self.color = color
        self.is_player = is_player
        self.is_merchant = is_merchant
        self.is_boss = is_boss
        self.is_npc = False  # Friendly NPC
        self.is_companion = False  # Companion NPC that follows player
        self.follow_target = None  # Target to follow (for companions)
        self.has_quest = False  # Whether NPC has a quest to offer
        self.dialogue = ""  # Dialogue text for NPC
        self.in_apartment = False  # Whether fighter is in apartment room

        self.vx = 0
        self.vy = 0
        self.facing = 1
        self.on_ground = False
        self.climbing = False
        
        # Building tracking
        self.inside_building = None  # Which Building object this fighter is in
        self.building_floor_num = 0  # Which floor number in the building

        self.speed = 4.5
        self.jump_speed = -11.0

        self.base_dmg = 5
        self.base_armor = 0
        self.base_attack_delay = 22

        self.weapon = None
        self.armor_item = None
        self.potion_slot = None  # Potion equipped to Q key

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
        self.aggro = False
        self.patrol_dir = random.choice([-1, 1])
        self.patrol_timer = random.randint(60, 240)
        self.was_merchant = is_merchant
        self.merchant_hostile = False
        
        # Knockback system
        self.knockback_timer = 0  # Frames remaining of knockback
        self.knockback_vx = 0  # Knockback velocity
        self.walk_anim_frame = 0

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
    
    def total_knockback(self):
        """Get total knockback value from weapon."""
        if self.weapon:
            return self.weapon.knockback if hasattr(self.weapon, 'knockback') else 0.0
        return 0.0

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

    def become_hostile(self, attacker=None):
        if self.merchant_hostile:
            return
        self.merchant_hostile = True
        if self.is_merchant:
            self.is_merchant = False
        self.aggro = True
        if attacker:
            self.facing = 1 if attacker.x > self.x else -1

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

    def move_and_collide(self, platforms, building_bounds=None):
        self.x += self.vx
        self.y += self.vy

        # Building bounds collision (walls, floor, ceiling)
        if building_bounds:
            building_x, building_y, building_width, floor_y, ceiling_y = building_bounds
            
            # Left wall collision
            if self.x < building_x:
                self.x = building_x
                self.vx = 0
            
            # Right wall collision
            if self.x + self.w > building_x + building_width:
                self.x = building_x + building_width - self.w
                self.vx = 0
            
            # Floor collision
            if self.y >= floor_y:
                self.y = floor_y
                self.vy = 0
                self.on_ground = True
            else:
                self.on_ground = False
            
            # Ceiling collision
            if self.y < ceiling_y:
                self.y = ceiling_y
                self.vy = 0
        else:
            # Outside building - use ground
            if self.y >= GROUND_Y:
                self.y = GROUND_Y
                self.vy = 0
                self.on_ground = True
            else:
                self.on_ground = False

        # Platform collision (for floor platforms)
        feet = pygame.Rect(self.rect.left, self.rect.bottom - 5,
                           self.rect.width, 10)
        for p in platforms:
            if feet.colliderect(p.rect) and self.vy >= 0:
                self.y = p.rect.top
                self.vy = 0
                self.on_ground = True

        # World bounds (only if not in building)
        if not building_bounds:
            if self.x < 0:
                self.x = 0
                self.vx = 0
            if self.x + self.w > WORLD_WIDTH:
                self.x = WORLD_WIDTH - self.w
                self.vx = 0

    # ---------- UPDATE PLAYER ----------
    def update_player(self, key_state, platforms, building_bounds=None):
        left = key_state[pygame.K_a]
        right = key_state[pygame.K_d]
        up = key_state[pygame.K_w]
        down = key_state[pygame.K_s]
        
        # Handle knockback first
        if self.knockback_timer > 0:
            self.knockback_timer -= 1
            # Apply knockback velocity
            self.vx = self.knockback_vx
            # Reduce knockback over time (friction effect) - slower decay for testing
            self.knockback_vx *= 0.92  # Slower decay (was 0.85)
            if abs(self.knockback_vx) < 1.0:  # Higher threshold (was 0.5)
                self.knockback_vx = 0
                self.knockback_timer = 0
            # Still allow jumping during knockback
            if up and self.on_ground:
                self.vy = self.jump_speed
            self.facing = -1 if self.vx < 0 else 1
        else:
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

            if up and self.on_ground:
                self.vy = self.jump_speed
                self.on_ground = False

        self.apply_gravity()
        self.move_and_collide(platforms, building_bounds)
        self.update_attack_state()

    # ---------- ENEMY AI ----------
    def update_enemy_ai(self, player, platforms, building_bounds=None):
        if (self.is_merchant and not self.merchant_hostile) or self.is_dead():
            # Still handle knockback even if merchant/dead
            if self.knockback_timer > 0:
                self.knockback_timer -= 1
                self.vx = self.knockback_vx
                self.knockback_vx *= 0.85
                if abs(self.knockback_vx) < 0.5:
                    self.knockback_vx = 0
                    self.knockback_timer = 0
            else:
                self.vx = 0
            self.update_attack_state()
            self.apply_gravity()
            self.move_and_collide(platforms, building_bounds)
            return

        # Calculate distance first (needed for both knockback and normal AI)
        aggro_range = 260
        aggro_drop_range = 360
        dx = player.x - self.x
        dist = abs(dx)
        
        # Handle knockback first - it overrides normal AI movement
        if self.knockback_timer > 0:
            self.knockback_timer -= 1
            self.vx = self.knockback_vx
            self.knockback_vx *= 0.92  # Slower decay for testing (was 0.85)
            if abs(self.knockback_vx) < 1.0:  # Higher threshold (was 0.5)
                self.knockback_vx = 0
                self.knockback_timer = 0
            self.facing = -1 if self.vx < 0 else 1
        else:
            # Normal AI movement
            if not self.aggro and dist <= aggro_range:
                self.aggro = True
            elif self.aggro and dist >= aggro_drop_range:
                self.aggro = False

            if self.aggro:
                self.facing = 1 if dx > 0 else -1

            if dist > 60:
                self.vx = self.speed * self.facing
            else:
                self.vx = 0

        if player.y < self.y - 30 and self.on_ground and random.random() < 0.02:
            self.vy = self.jump_speed
        
        # Only do patrol if not in knockback
        if self.knockback_timer <= 0:
            # Patrol: pace left/right until re-aggro.
            if not self.aggro:
                self.vx = self.speed * self.patrol_dir
                self.patrol_timer -= 1

                hit_left_edge = self.x <= 20
                hit_right_edge = self.x + self.w >= WORLD_WIDTH - 20
                if hit_left_edge or hit_right_edge:
                    self.patrol_dir *= -1
                    self.patrol_timer = random.randint(60, 200)

                if self.patrol_timer <= 0 or random.random() < 0.01:
                    self.patrol_dir *= -1
                    self.patrol_timer = random.randint(60, 200)

            self.facing = self.patrol_dir

        # Reset attack cooldown unless actively aggroed so they don't swing while wandering.
        if not self.aggro:
            self.ai_attack_cooldown = max(0, self.ai_attack_cooldown - 1)
        else:
            if self.ai_attack_cooldown > 0:
                self.ai_attack_cooldown -= 1

        if self.aggro and dist < 90 and self.ai_attack_cooldown <= 0:
            self.start_attack("swing")
            self.ai_attack_cooldown = self.attack_delay() + 12

        self.apply_gravity()
        self.move_and_collide(platforms, building_bounds)
        self.update_attack_state()

    # ---------- DRAW ----------

    # ---------- DRAW ----------
    def draw(self, surface, camera_x, camera_y=0, debug=False):
        r = self.rect.move(-camera_x, -camera_y)

        # Red glow/aura when health is low (30% or less) - for players only
        if self.is_player and not self.is_dead():
            health_percent = self.hp / self.hp_max if self.hp_max > 0 else 0
            if health_percent <= 0.3:
                # Create pulsing glow effect - more intense as HP gets lower
                low_health_threshold = 0.3
                intensity = int((low_health_threshold - health_percent) / low_health_threshold * 150)  # 0-150
                glow_radius = 35 + intensity // 8  # Radius grows as health decreases
                
                # Create glow surface with alpha channel
                glow_size = glow_radius * 2
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                
                # Draw multiple circles for smooth glow effect
                for radius in range(glow_radius, 0, -2):
                    # Alpha decreases from center outward
                    alpha = max(20, min(120, intensity - (glow_radius - radius) * 2))
                    glow_color = (255, 0, 0, alpha)  # Red with transparency
                    pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), radius)
                
                # Draw glow centered on player (below player sprite)
                glow_x = r.centerx - glow_radius
                glow_y = r.centery - glow_radius
                surface.blit(glow_surf, (glow_x, glow_y))

        # Walking animation state
        is_moving = abs(self.vx) > 0.1 and self.on_ground and not self.climbing
        if is_moving:
            self.walk_anim_frame += abs(self.vx) * 0.8
        walk_phase = int(self.walk_anim_frame) % 40
        walk_swing = math.sin(walk_phase * math.pi / 20) * 0.5

        # Torso: trapezoid (wider at top, narrower at bottom) - shortened
        # Boss units have larger torso
        if self.is_boss:
            torso_top_width = 24
            torso_bottom_width = 16
            torso_height = r.height - 36
        else:
            torso_top_width = 18
            torso_bottom_width = 12
            torso_height = r.height - 28  # Shortened more
        torso_top_y = r.bottom - torso_height
        torso_bottom_y = r.bottom - 2

        torso_points = [
            (r.centerx - torso_top_width // 2, torso_top_y),
            (r.centerx + torso_top_width // 2, torso_top_y),
            (r.centerx + torso_bottom_width // 2, torso_bottom_y),
            (r.centerx - torso_bottom_width // 2, torso_bottom_y),
        ]
        pygame.draw.polygon(surface, self.color, torso_points)

        # Boss units have larger head
        if self.is_boss:
            head_size = 15
            head = pygame.Rect(r.centerx - head_size // 2, torso_top_y - 15, head_size, head_size)
            pygame.draw.rect(surface, self.color, head, border_radius=4)
            
            # Draw horns on boss units (larger)
            horn_left_x = r.centerx - 7
            horn_left_y = torso_top_y - 15
            pygame.draw.polygon(surface, (60, 60, 60), [
                (horn_left_x - 2, horn_left_y - 2),
                (horn_left_x + 2, horn_left_y - 8),
                (horn_left_x + 5, horn_left_y - 5),
                (horn_left_x, horn_left_y)
            ])
            # Right horn
            horn_right_x = r.centerx + 7
            horn_right_y = torso_top_y - 15
            pygame.draw.polygon(surface, (60, 60, 60), [
                (horn_right_x + 2, horn_right_y - 2),
                (horn_right_x - 2, horn_right_y - 8),
                (horn_right_x - 5, horn_right_y - 5),
                (horn_right_x, horn_right_y)
            ])
        else:
            head = pygame.Rect(r.centerx - 6, torso_top_y - 12, 12, 12)
            pygame.draw.rect(surface, self.color, head, border_radius=3)

        accent = tuple(max(0, c - 30) for c in self.color)
        highlight = tuple(min(255, c + 40) for c in self.color)

        shoulder_y = torso_top_y + 10
        shoulder_x = r.centerx - 2 * self.facing

        # Arms with walking animation
        if is_moving:
            front_arm_swing = walk_swing * 8
            back_arm_swing = -walk_swing * 8
        else:
            front_arm_swing = 0
            back_arm_swing = 0

        hand_x = shoulder_x + (20 + front_arm_swing) * self.facing
        hand_y = shoulder_y + 4 + abs(front_arm_swing) * 0.3
        pygame.draw.line(surface, highlight,
                         (shoulder_x, shoulder_y),
                         (hand_x, hand_y), 5)

        back_hand_x = shoulder_x + (-12 + back_arm_swing) * self.facing
        back_hand_y = shoulder_y + 2 + abs(back_arm_swing) * 0.3
        pygame.draw.line(surface, accent,
                         (shoulder_x, shoulder_y + 3),
                         (back_hand_x, back_hand_y), 4)

        # Legs with walking animation
        hip_y = torso_bottom_y
        hip_x = r.centerx

        if is_moving:
            front_leg_swing = walk_swing * 10
            back_leg_swing = -walk_swing * 10
        else:
            front_leg_swing = 0
            back_leg_swing = 0

        front_foot = (hip_x + (12 + front_leg_swing) * self.facing,
                     hip_y + 18 - abs(front_leg_swing) * 0.4)
        back_foot = (hip_x + (-10 + back_leg_swing) * self.facing,
                    hip_y + 16 - abs(back_leg_swing) * 0.4)

        pygame.draw.line(surface, self.color,
                         (hip_x, hip_y),
                         front_foot, 5)
        pygame.draw.line(surface, accent,
                         (hip_x - 4 * self.facing, hip_y),
                         back_foot, 4)

        # Armor graphics (drawn after body/legs)
        if self.armor_item:
            armor_name = (self.armor_item.name or "").lower()
            if "cloth" in armor_name:
                armor_color = (255, 255, 255)  # White fabric
            elif "leather" in armor_name:
                armor_color = (139, 90, 43)  # Brown leather
            elif "plate" in armor_name:
                armor_color = (192, 192, 192)  # Silver/grey metal
            else:
                armor_color = (200, 200, 200)  # Default grey

            # Head/Helmet
            helmet = pygame.Rect(r.centerx - 7, torso_top_y - 13, 14, 10)
            pygame.draw.rect(surface, armor_color, helmet, border_radius=2)

            # Chest/Chestplate
            chest_top_width = torso_top_width - 2
            chest_bottom_width = torso_bottom_width - 2
            chest_points = [
                (r.centerx - chest_top_width // 2, torso_top_y + 2),
                (r.centerx + chest_top_width // 2, torso_top_y + 2),
                (r.centerx + chest_bottom_width // 2, torso_bottom_y - 4),
                (r.centerx - chest_bottom_width // 2, torso_bottom_y - 4),
            ]
            pygame.draw.polygon(surface, armor_color, chest_points)

            # Leggings (on legs)
            leg_armor_y = hip_y + 2
            pygame.draw.line(surface, armor_color,
                             (hip_x, leg_armor_y),
                             front_foot, 6)
            pygame.draw.line(surface, armor_color,
                             (hip_x - 4 * self.facing, leg_armor_y),
                             back_foot, 5)

            # Boots (on feet)
            boot_size = 4
            front_boot = pygame.Rect(front_foot[0] - boot_size // 2,
                                    front_foot[1] - 2,
                                    boot_size, boot_size + 2)
            back_boot = pygame.Rect(back_foot[0] - boot_size // 2,
                                    back_foot[1] - 2,
                                    boot_size, boot_size + 2)
            pygame.draw.rect(surface, armor_color, front_boot)
            pygame.draw.rect(surface, armor_color, back_boot)

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
                # D-shaped bow: vertical string with curved limbs.
                string_x = hand_x
                top_y = hand_y - 20
                bot_y = hand_y + 20
                bow_height = bot_y - top_y
                bow_width = 28

                # String
                pygame.draw.line(surface, color,
                                 (string_x, top_y),
                                 (string_x, bot_y), 2)

                if self.facing == 1:
                    bow_rect = pygame.Rect(string_x - 2, top_y,
                                            bow_width, bow_height)
                    start_angle = -math.pi / 2
                    end_angle = math.pi / 2
                else:
                    bow_rect = pygame.Rect(string_x - bow_width + 2, top_y,
                                            bow_width, bow_height)
                    start_angle = math.pi / 2
                    end_angle = 3 * math.pi / 2

                pygame.draw.arc(surface, color,
                                bow_rect, start_angle, end_angle, 4)

            elif "axe" in visual:
                # Axe: stylized hatchet with angled handle and wedge head.
                shaft_length = 40
                swing_progress = 0.0
                if self.attack_type:
                    swing_progress = min(1.0, self.attack_frame / max(1, self.attack_delay()))

                start_angle = -math.pi / 2
                end_angle = 0.0 if self.facing == 1 else math.pi
                angle = start_angle + (end_angle - start_angle) * swing_progress

                dir_x = math.cos(angle)
                dir_y = math.sin(angle)
                rest_angle = -math.pi / 4
                if not self.attack_type:
                    angle = rest_angle
                    dir_x = math.cos(angle)
                    dir_y = math.sin(angle)
                    swing_progress = 0.0

                tip_x = hand_x + dir_x * shaft_length
                tip_y = hand_y + dir_y * shaft_length

                handle_color = (160, 90, 50)
                pygame.draw.line(surface, handle_color,
                                 (hand_x, hand_y),
                                 (tip_x, tip_y), 5)

                head_width = 20
                head_height = 24
                anchor_distance = shaft_length * 0.72
                base_center_x = hand_x + dir_x * anchor_distance
                base_center_y = hand_y + dir_y * anchor_distance

                tangent_x = -dir_y
                tangent_y = dir_x

                half_h = head_height * 0.5
                back_bottom = (
                    base_center_x - tangent_x * half_h,
                    base_center_y - tangent_y * half_h,
                )
                back_top = (
                    base_center_x + tangent_x * half_h,
                    base_center_y + tangent_y * half_h,
                )

                front_mid_x = base_center_x + self.facing * head_width
                front_mid_y = base_center_y
                front_top = (
                    front_mid_x + tangent_x * (head_height * 0.25),
                    front_mid_y + tangent_y * (head_height * 0.25),
                )
                front_bottom = (
                    front_mid_x - tangent_x * (head_height * 0.25),
                    front_mid_y - tangent_y * (head_height * 0.25),
                )
                toe = (
                    front_mid_x + self.facing * head_width * 0.35,
                    front_mid_y,
                )

                head_color = (235, 235, 235)
                blade_points = [
                    back_bottom,
                    front_bottom,
                    toe,
                    front_top,
                    back_top,
                ]
                pygame.draw.polygon(surface, head_color,
                                    [(int(x), int(y)) for x, y in blade_points])

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
        self.platforms = []  # Keep for ground platform
        self.buildings = []  # Skyscrapers
        self.units = []
        self.player_inside_building = None  # Which building player is in
        self.player_current_floor = 0  # Current floor when inside
        self.player_in_apartment = False  # Whether player is in apartment room (not hall)
        self.bg_buildings_back = []
        self.bg_buildings_front = []
        self.bg_buildings_detailed = []  # Stores building data with windows
        self.hillside_buildings = []  # Hillside cityscape layer
        self.streetlights = []  # Streetlight positions
        self.quests = []  # Active quests
        self.pickup_notifications = []  # Pickup notification messages
        self.dogs = []  # Dog entities
        self.generate()

    def generate_window_pattern(self, building_rect, window_colors, pattern_type=None):
        """Generate windows with variety: grid, horizontal strips, vertical stripes, or random."""
        windows = []
        w = building_rect.width
        h = building_rect.height
        
        if pattern_type is None:
            pattern_type = random.choice(['grid', 'horizontal', 'vertical', 'mixed', 'sparse'])
        
        if pattern_type == 'grid':
            # Organized grid pattern
            window_w = 2
            window_h = 2
            spacing_x = 6
            spacing_y = 8
            for wy in range(building_rect.top + 10, building_rect.bottom - 8, spacing_y):
                for wx in range(building_rect.left + 4, building_rect.right - 4, spacing_x):
                    if random.random() < 0.75:
                        windows.append((wx, wy, random.choice(window_colors), window_w, window_h))
        
        elif pattern_type == 'horizontal':
            # Horizontal strips of windows
            strip_height = 3
            spacing_y = 10
            for wy in range(building_rect.top + 12, building_rect.bottom - 8, spacing_y):
                strip_start = building_rect.left + 4
                strip_end = building_rect.right - 4
                # Create continuous horizontal strip
                for wx in range(strip_start, strip_end, 4):
                    if random.random() < 0.8:
                        windows.append((wx, wy, random.choice(window_colors), 3, strip_height))
        
        elif pattern_type == 'vertical':
            # Vertical stripes
            stripe_width = 2
            spacing_x = 8
            for wx in range(building_rect.left + 6, building_rect.right - 6, spacing_x):
                stripe_start = building_rect.top + 10
                stripe_end = building_rect.bottom - 8
                # Create continuous vertical stripe
                for wy in range(stripe_start, stripe_end, 4):
                    if random.random() < 0.7:
                        windows.append((wx, wy, random.choice(window_colors), stripe_width, 3))
        
        elif pattern_type == 'mixed':
            # Mix of patterns - some floors with horizontal, some with grid
            floor_height = 12
            for floor_y in range(building_rect.top + 10, building_rect.bottom - 8, floor_height):
                floor_pattern = random.choice(['horizontal', 'grid'])
                if floor_pattern == 'horizontal':
                    for wx in range(building_rect.left + 4, building_rect.right - 4, 4):
                        if random.random() < 0.7:
                            windows.append((wx, floor_y, random.choice(window_colors), 3, 2))
                else:
                    for wx in range(building_rect.left + 4, building_rect.right - 4, 6):
                        if random.random() < 0.6:
                            windows.append((wx, floor_y, random.choice(window_colors), 2, 2))
        
        else:  # sparse or random
            # Sparse random windows
            window_spacing = 8
            for wy in range(building_rect.top + 10, building_rect.bottom - 8, window_spacing):
                for wx in range(building_rect.left + 4, building_rect.right - 4, window_spacing):
                    if random.random() < 0.4:
                        windows.append((wx, wy, random.choice(window_colors), 2, 2))
        
        return windows

    def generate_background(self):
        random.seed(self.seed)
        self.bg_buildings_back.clear()
        self.bg_buildings_front.clear()
        self.bg_buildings_detailed.clear()
        self.hillside_buildings.clear()
        self.streetlights.clear()

        # Generate unbroken hillside cityscape (furthest back layer)
        # This layer must completely fill the viewport with no gaps
        # Extend well beyond WORLD_WIDTH to cover all camera positions
        extended_width = WORLD_WIDTH * 4  # Much larger than viewport
        x = -WIDTH * 2  # Start well before viewport
        
        # Create multiple rows of buildings stacked vertically to fill entire height
        while x < extended_width:
            # Generate buildings in vertical columns to ensure no gaps
            current_y = HEIGHT  # Start from bottom
            
            while current_y > 0:  # Fill from bottom to top
                # Building width - vary for organic look
                w = random.randint(20, 45)
                
                # Building height - varies to create dense packing
                h = random.randint(30, HEIGHT // 2)
                
                # Ensure building doesn't go above viewport
                if current_y - h < 0:
                    h = current_y
                
                if h > 10:  # Only create buildings of reasonable size
                    building_x = x
                    building_y = current_y - h
                    
                    # Generate windows with variety
                    window_colors = [
                        (100, 70, 40),    # Very dim orange
                        (90, 60, 35),     # Very dim yellow
                        (75, 55, 30),     # Extremely dim
                        (85, 65, 40),     # Very dim warm
                    ]
                    building_rect = pygame.Rect(building_x, building_y, w, h)
                    windows = self.generate_window_pattern(building_rect, window_colors)
                    
                    # Building colors (furthest back - darkest)
                    # Darken all colors significantly for distance
                    base_colors = [
                        (70, 80, 90),    # Dark steel blue-grey
                        (90, 95, 100),   # Smoked glass grey
                        (60, 65, 70),    # Charcoal steel
                        (100, 105, 110), # Brushed metal grey
                        (50, 55, 60),    # Deep graphite
                        (120, 125, 130), # Concrete grey
                        (80, 90, 100),   # Blue-tinted skyscraper glass
                        (55, 60, 65)     # Darkened structural metal
                    ]
                    # Darken by 70% for furthest layer
                    base_color = random.choice(base_colors)
                    building_color = tuple(max(0, int(c * 0.3)) for c in base_color)
                    
                    self.hillside_buildings.append({
                        'rect': pygame.Rect(building_x, building_y, w, h),
                        'windows': windows,
                        'color': building_color,
                        'hill_y': current_y
                    })
                
                # Move up for next building in this column
                current_y -= h
                
                # Small random gap between buildings in same column (0-3 pixels)
                current_y -= random.randint(0, 3)
            
            # Move to next column - very tight spacing (0-2 pixel gaps)
            x += w + random.randint(0, 2)

        # Generate detailed skyscrapers with windows (back layer - very dense)
        x = 0
        while x < WORLD_WIDTH + WIDTH:
            w = random.randint(40, 140)
            h = random.randint(250, 500)
            building_rect = pygame.Rect(x, GROUND_Y - h, w, h)
            self.bg_buildings_back.append(building_rect)
            
            # Generate windows with variety
            window_colors = [
                (180, 140, 70),   # Dimmer orange
                (200, 160, 100),  # Dimmer yellow
                (160, 120, 60),   # Dimmer deep orange
                (150, 110, 70),   # Dim orange
            ]
            windows = self.generate_window_pattern(building_rect, window_colors)
            
            self.bg_buildings_detailed.append({
                'rect': building_rect,
                'windows': windows,
                'color': (15, 12, 18),  # Very dark purple-grey (darker than before)
                'layer': 'back'  # Back layer for parallax
            })
            
            x += w + random.randint(5, 25)  # Much denser spacing

        # Generate mid-layer buildings (medium height, dense)
        x = 0
        while x < WORLD_WIDTH + WIDTH:
            w = random.randint(50, 120)
            h = random.randint(150, 300)
            building_rect = pygame.Rect(x, GROUND_Y - h - 20, w, h)
            
            # Generate windows with variety
            window_colors = [
                (220, 170, 90),   # Medium orange
                (230, 190, 130),  # Medium yellow
                (200, 150, 70),   # Medium deep orange
                (180, 130, 90),   # Medium orange
            ]
            windows = self.generate_window_pattern(building_rect, window_colors)
            
            self.bg_buildings_detailed.append({
                'rect': building_rect,
                'windows': windows,
                'color': (22, 16, 28),  # Medium dark (darker than before)
                'layer': 'mid'  # Mid layer for parallax
            })
            
            x += w + random.randint(8, 30)

        # Generate foreground buildings (shorter, very dense)
        x = 0
        while x < WORLD_WIDTH + WIDTH:
            w = random.randint(60, 140)
            h = random.randint(100, 280)
            building_rect = pygame.Rect(x, GROUND_Y - h + 30, w, h)
            self.bg_buildings_front.append(building_rect)
            
            # Generate windows with variety
            window_colors = [
                (255, 200, 100),  # Bright orange
                (255, 220, 150),  # Bright yellow
                (200, 150, 100),  # Bright dim orange
            ]
            windows = self.generate_window_pattern(building_rect, window_colors)
            
            self.bg_buildings_detailed.append({
                'rect': building_rect,
                'windows': windows,
                'color': (35, 28, 42),  # Brightest (lighter than before)
                'layer': 'front'  # Front layer for parallax
            })
            
            x += w + random.randint(10, 40)  # Dense but with occasional gaps for streets

        # Generate streetlights
        x = 50
        while x < WORLD_WIDTH:
            if random.random() < 0.3:  # 30% chance per position
                self.streetlights.append({
                    'x': x,
                    'y': GROUND_Y - 40,
                    'glow_radius': random.randint(25, 40)
                })
            x += random.randint(80, 200)

    def generate_platforms_ladders_doors(self):
        self.platforms.clear()
        self.buildings.clear()

        random.seed(self.seed + 1)

        # Ground platform
        self.platforms.append(Platform(0, GROUND_Y, WORLD_WIDTH, 20))

        # Generate skyscrapers
        x = 100
        EXIT_BUFFER = 250  # Keep buildings away from the exit area
        while x < WORLD_WIDTH - EXIT_BUFFER:
            # Building dimensions - randomize width
            building_width = random.randint(400, 700)  # Vary building widths
            num_floors = random.randint(5, 20)
            
            # Check if this building would extend into exit area
            if x + building_width >= WORLD_WIDTH - EXIT_BUFFER:
                break  # Stop generating if this building would be too close to exit
            
            building = Building(x, GROUND_Y, building_width, num_floors)
            self.buildings.append(building)
            
            # Populate floors with enemies and items
            settings = STAGE_SETTINGS.get(self.stage, STAGE_SETTINGS[4])
            for floor in building.floors:
                # Enemies only spawn in apartments (not halls)
                # Some floors have enemies in their apartments
                if random.random() < 0.4:  # 40% chance per floor
                    num_enemies = random.randint(1, 3)
                    for _ in range(num_enemies):
                        # Enemies spawn in apartment room (to the right of apartment door)
                        apartment_room_x = floor['apartment_door_x'] + 50  # Inside apartment
                        enemy_x = apartment_room_x + random.randint(0, 150)  # Random position in apartment
                        # Spawn enemy on the floor (floor['y'] is the floor level, Fighter y is bottom)
                        # Random enemy color variation
                        base_r, base_g, base_b = ENEMY_COLOR
                        color_variation = random.randint(-40, 40)
                        enemy_color = (
                            max(100, min(255, base_r + color_variation)),
                            max(80, min(200, base_g + color_variation // 2)),
                            max(0, min(100, base_b + color_variation // 3))
                        )
                        enemy = Fighter(enemy_x, floor['y'], enemy_color, is_player=False)
                        # Mark enemy as inside this building and in apartment
                        enemy.inside_building = building
                        enemy.building_floor_num = floor['floor_num']
                        enemy.in_apartment = True  # Enemy is in apartment room
                        # Set enemy on ground immediately
                        enemy.on_ground = True
                        enemy.vy = 0
                        enemy.hp_max = settings["enemy_hp"]
                        enemy.hp = enemy.hp_max
                        enemy.base_attack_delay = int(enemy.base_attack_delay * settings["enemy_attack_delay_mult"])
                        weapon = self.generate_weapon_for_stage(settings)
                        armor_item = self.generate_armor_for_stage(settings)
                        enemy.weapon = weapon
                        enemy.armor_item = armor_item
                        enemy.inventory.append(weapon)
                        enemy.inventory.append(armor_item)
                        enemy.money = random.randint(5, 40)
                        floor['apartment_enemies'].append(enemy)
                        self.units.append(enemy)
                
                # Elevator door positions - avoid placing items on them (increased buffer)
                ELEVATOR_WIDTH = 60  # Increased buffer zone around elevators
                elevator_down_left = floor['elevator_down_x'] - ELEVATOR_WIDTH // 2
                elevator_down_right = floor['elevator_down_x'] + ELEVATOR_WIDTH // 2
                elevator_up_left = floor['elevator_up_x'] - ELEVATOR_WIDTH // 2
                elevator_up_right = floor['elevator_up_x'] + ELEVATOR_WIDTH // 2
                
                # Containers only spawn in apartments (not halls)
                # Some apartment rooms have lootable containers
                if random.random() < 0.4:  # 40% chance per floor
                    num_containers = random.randint(1, 2)
                    for _ in range(num_containers):
                        # Containers spawn in apartment room
                        apartment_room_x = floor['apartment_door_x'] + 50
                        container_x = apartment_room_x + random.randint(20, 150)
                        
                        container_type = random.choice(['chest', 'dresser', 'wardrobe'])
                        # Container may or may not have an item
                        container_item = None
                        if random.random() < 0.7:  # 70% chance container has an item
                            item_roll = random.random()
                            if item_roll < 0.4:  # 40% weapon
                                container_item = self.generate_weapon_for_stage(settings)
                            elif item_roll < 0.7:  # 30% armor
                                container_item = self.generate_armor_for_stage(settings)
                            else:  # 30% potion
                                container_item = self.generate_potion_for_stage(settings)
                        floor['containers'].append({
                            'type': container_type,
                            'x': container_x,
                            'y': floor['y'],
                            'item': container_item,
                            'looted': False
                        })
                
                # Add background assets for HALLS only (no cabinets)
                # Halls only have: vending machines, fire extinguishers, security cameras, emergency signs
                num_hall_assets = random.randint(2, 4)
                hall_asset_types_wall = [
                    'fire_extinguisher', 'security_camera', 'emergency_exit_sign'
                ]
                hall_asset_types_floor = [
                    'vending_machine'
                ]
                
                # Add apartment furniture (bed, dresser, nightstand, lamp)
                apartment_furniture_types = ['bed_single', 'bed_double', 'dresser', 'refrigerator', 'television']
                num_furniture = random.randint(3, 5)
                
                # Place hall assets (vending machines, fire extinguishers, etc.) - in halls only
                existing_hall_positions = []
                vending_machine_count = 0  # Track vending machines - max 1 per floor
                for _ in range(num_hall_assets):
                    max_attempts = 30
                    asset_x = None
                    asset_y = None
                    asset_type = None
                    
                    for attempt in range(max_attempts):
                        # Randomly choose wall or floor mounted (but no vending machine if already have one)
                        if random.random() < 0.5:  # 50% chance wall mounted
                            asset_type = random.choice(hall_asset_types_wall)
                            test_x = building.x + random.randint(60, building.width - 60)
                            test_y = floor['y'] - building.floor_height // 2  # Middle of wall
                        else:
                            # Only add vending machine if we don't have one yet
                            if vending_machine_count >= 1:
                                asset_type = random.choice(hall_asset_types_wall)  # Fall back to wall mounted
                                test_x = building.x + random.randint(60, building.width - 60)
                                test_y = floor['y'] - building.floor_height // 2
                            else:
                                asset_type = random.choice(hall_asset_types_floor)
                                test_x = building.x + random.randint(60, building.width - 60)
                                test_y = floor['y']  # On floor
                        
                        # Check if not on elevator doors (with increased buffer)
                        if (elevator_down_left <= test_x <= elevator_down_right or
                                elevator_up_left <= test_x <= elevator_up_right):
                            continue
                        
                        # Check if not overlapping with existing assets
                        overlap = False
                        for existing in existing_hall_positions:
                            spacing_needed = 60 if asset_type == 'vending_machine' else 50  # More space for vending machines
                            if abs(existing['x'] - test_x) < spacing_needed:
                                overlap = True
                                break
                        
                        if not overlap:
                            asset_x = test_x
                            asset_y = test_y
                            break
                    
                    if asset_x is None:
                        continue
                    
                    # Skip if trying to add vending machine but already have one
                    if asset_type == 'vending_machine' and vending_machine_count >= 1:
                        continue
                    
                    # Add to hall assets
                    asset_data = {
                        'type': asset_type,
                        'x': asset_x,
                        'y': asset_y
                    }
                    # Vending machines sometimes have healing potions
                    if asset_type == 'vending_machine':
                        vending_machine_count += 1
                        if random.random() < 0.3:
                            asset_data['has_potion'] = True
                    floor['background_assets'].append(asset_data)
                    existing_hall_positions.append({'x': asset_x, 'y': asset_y})
                
                # Place apartment furniture (bed, dresser, nightstand, lamp) - in apartment room
                apartment_room_x = floor['apartment_door_x'] + 50
                for _ in range(num_furniture):
                    furniture_type = random.choice(apartment_furniture_types)
                    # Place furniture in apartment room (to the right of door)
                    furniture_x = apartment_room_x + random.randint(20, 150)
                    furniture_y = floor['y']
                    
                    floor['apartment_assets'].append({
                        'type': furniture_type,
                        'x': furniture_x,
                        'y': furniture_y
                    })
            
            x += building_width + random.randint(100, 200)

    def generate_weapon_for_stage(self, stage_settings):
        dmg_min = stage_settings["weapon_dmg_min"]
        dmg_max = stage_settings["weapon_dmg_max"]
        kb_min = stage_settings["knockback_min"]
        kb_max = stage_settings["knockback_max"]

        dmg = random.randint(dmg_min, dmg_max)
        knockback = round(random.uniform(kb_min, kb_max), 1)
        name = random.choice(MELEE_WEAPON_NAMES)

        # Set attack speed bonus based on weapon type
        if name == "Short Sword":
            atk_speed_bonus = random.uniform(0.25, 0.45)  # Fast attack speed
        elif name == "Long Sword":
            atk_speed_bonus = random.uniform(-0.05, 0.05)  # Slower attack speed
        else:  # Battle Axe
            atk_speed_bonus = random.uniform(-0.15, 0.0)  # Slowest attack speed
            # Increase knockback SIGNIFICANTLY for Battle Axes (debug)
            knockback = round(random.uniform(kb_min * 5.0, kb_max * 5.0), 1)  # 5x knockback for testing

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
        
        # Randomly choose armor type based on stage
        if self.stage <= 1:
            armor_type = "Cloth"
        elif self.stage <= 2:
            armor_type = random.choice(["Cloth", "Leather"])
        else:
            armor_type = random.choice(["Cloth", "Leather", "Plate"])
        
        return Item(
            name=f"{armor_type} Armor",
            dmg=0,
            armor=armor_val,
            atk_speed_bonus=0.0,
            knockback=0.0,
            price=price,
        )

    def generate_potion_for_stage(self, stage_settings):
        # Fixed healing amounts based on stage
        if self.stage == 1:
            potion_name = "Small Potion"
            heal_amount = 20
        elif self.stage == 2:
            potion_name = "Medium Potion"
            heal_amount = 40
        else:  # Stage 3+
            potion_name = "Large Potion"
            heal_amount = 80
        
        # Price based on heal amount
        price = heal_amount * 2 + 5
        
        return Item(
            name=potion_name,
            dmg=0,
            armor=0,
            atk_speed_bonus=0.0,
            knockback=0.0,
            price=price,
            heal_amount=heal_amount,
            is_potion=True,
            count=1,
        )

    def generate_units(self, player):
        # Units are now generated inside buildings during building generation
        # Just spawn one merchant on the ground
        settings = STAGE_SETTINGS.get(self.stage, STAGE_SETTINGS[4])
        merchant_x = random.randint(200, WORLD_WIDTH - 200)
        merchant = Fighter(merchant_x, GROUND_Y, MERCHANT_COLOR, is_player=False, is_merchant=True)
        
        # Give merchant items to sell
        num_items = random.randint(3, 6)
        for _ in range(num_items):
            item_roll = random.random()
            if item_roll < 0.4:  # 40% weapon
                item = self.generate_weapon_for_stage(settings)
            elif item_roll < 0.7:  # 30% armor
                item = self.generate_armor_for_stage(settings)
            else:  # 30% potion
                item = self.generate_potion_for_stage(settings)
            merchant.inventory.append(item)
        
        # Always add at least 1-2 potions to merchant
        for _ in range(random.randint(1, 2)):
            potion = self.generate_potion_for_stage(settings)
            merchant.inventory.append(potion)
        
        # Give merchant some money
        merchant.money = random.randint(200, 500)
        
        self.empower_merchant(merchant)
        self.units.append(merchant)
        
        # Generate one boss unit per game - spawn in a random building room
        boss_settings = STAGE_SETTINGS.get(2, STAGE_SETTINGS[2])  # Stage 2 quality items
        
        # Find a random building and floor for the boss
        if self.buildings:
            # Pick a random building
            boss_building = random.choice(self.buildings)
            # Pick a random floor (not ground floor, make it more interesting)
            available_floors = [f for f in boss_building.floors if f['floor_num'] > 0]  # Skip ground floor
            if not available_floors:
                available_floors = boss_building.floors  # Fallback to all floors if only 1 floor
            
            boss_floor = random.choice(available_floors)
            boss_x = boss_building.x + random.randint(50, boss_building.width - 50)
            
            # Spawn boss on the selected floor
            # Random boss color variation
            base_r, base_g, base_b = ENEMY_COLOR
            color_variation = random.randint(-40, 40)
            boss_color = (
                max(100, min(255, base_r + color_variation)),
                max(80, min(200, base_g + color_variation // 2)),
                max(0, min(100, base_b + color_variation // 3))
            )
            boss = Fighter(boss_x, boss_floor['y'], boss_color, is_player=False, is_boss=True)
            # Mark boss as inside this building
            boss.inside_building = boss_building
            boss.building_floor_num = boss_floor['floor_num']
            boss.on_ground = True
            boss.vy = 0
            
            # Add boss to the floor's apartment enemies list
            boss_floor['apartment_enemies'].append(boss)
            boss.in_apartment = True  # Boss is in apartment
        else:
            # Fallback: spawn on ground if no buildings (shouldn't happen)
            boss_x = random.randint(300, WORLD_WIDTH - 300)
            # Random boss color variation (fallback)
            base_r, base_g, base_b = ENEMY_COLOR
            color_variation = random.randint(-40, 40)
            boss_color = (
                max(100, min(255, base_r + color_variation)),
                max(80, min(200, base_g + color_variation // 2)),
                max(0, min(100, base_b + color_variation // 3))
            )
            boss = Fighter(boss_x, GROUND_Y, boss_color, is_player=False, is_boss=True)
        
        # Boss has stage 2 quality items
        boss_weapon = self.generate_weapon_for_stage(boss_settings)
        boss_armor = self.generate_armor_for_stage(boss_settings)
        boss.weapon = boss_weapon
        boss.armor_item = boss_armor
        boss.inventory.append(boss_weapon)
        boss.inventory.append(boss_armor)
        # Boss always drops an item when killed
        boss.always_drops_item = True
        boss.drop_item = random.choice([boss_weapon, boss_armor])  # Drop one of the items
        
        # Boss is tougher - 2x HP, more damage, more armor
        boss.hp_max = int(settings["enemy_hp"] * 2.5)
        boss.hp = boss.hp_max
        boss.base_dmg = int(boss.base_dmg * 1.5)
        boss.base_armor = int(boss.base_armor * 2)
        boss.base_attack_delay = int(boss.base_attack_delay * settings["enemy_attack_delay_mult"] * 0.8)  # Faster attacks
        boss.money = random.randint(100, 200)  # More money than regular enemies
        
        self.units.append(boss)
        
        # Generate starter NPC for stage 1
        if self.stage == 1:
            self.generate_starter_npc()
        
        # Generate NPCs with quests
        self.generate_quest_npcs()

    def generate_quest_npcs(self):
        """Generate NPCs with quests in buildings."""
        if not self.buildings:
            return
        
        # Generate 1-2 quest NPCs per stage
        num_quests = random.randint(1, 2)
        
        for _ in range(num_quests):
            quest_type = random.choice(["defeat_enemies", "find_dog"])
            
            if quest_type == "defeat_enemies":
                # Find a building with enemies
                target_building = None
                for building in self.buildings:
                    total_enemies = sum(len(f['enemies']) for f in building.floors)
                    if total_enemies >= 3:  # Need at least 3 enemies
                        target_building = building
                        break
                
                if not target_building:
                    continue  # Skip if no suitable building
                
                # Pick a floor with enemies (in apartments)
                floors_with_enemies = [f for f in target_building.floors if len(f.get('apartment_enemies', [])) >= 2]
                if not floors_with_enemies:
                    continue
                
                target_floor = random.choice(floors_with_enemies)
                npc_x = target_building.x + random.randint(50, target_building.width - 50)
                npc_y = target_floor['y']
                
                # Create NPC
                npc = Fighter(npc_x, npc_y, NPC_COLOR, is_player=False, is_merchant=False)
                npc.inside_building = target_building
                npc.building_floor_num = target_floor['floor_num']
                npc.on_ground = True
                npc.vy = 0
                npc.is_npc = True  # Mark as NPC
                npc.hp_max = 80  # NPCs have moderate HP
                npc.hp = npc.hp_max
                
                # Create companion NPC for following player
                companion = Fighter(npc_x + 20, npc_y, NPC_COLOR, is_player=False, is_merchant=False)
                companion.inside_building = target_building
                companion.building_floor_num = target_floor['floor_num']
                companion.on_ground = True
                companion.vy = 0
                companion.is_npc = True
                companion.is_companion = True  # Mark as companion
                companion.hp_max = 80
                companion.hp = companion.hp_max
                companion.follow_target = None  # Will be set to player when quest starts
                
                # Count initial enemies in building (apartment enemies)
                initial_enemy_count = sum(len(f.get('apartment_enemies', [])) for f in target_building.floors)
                
                # Create quest
                quest = Quest(
                    quest_type="defeat_enemies",
                    npc=npc,
                    description="Help me! Defeat the enemies nearby!",
                    target_building=target_building,
                    target_floor=target_floor
                )
                quest.status = "offered"  # Quest starts as offered
                quest.companion_npc = companion
                quest.initial_enemy_count = initial_enemy_count
                npc.has_quest = True
                npc.dialogue = "Help me! Defeat the enemies nearby!"
                
                self.quests.append(quest)
                self.units.append(npc)
                self.units.append(companion)
                
            elif quest_type == "find_dog":
                # Find a building for the NPC
                target_building = random.choice(self.buildings)
                target_floor = random.choice(target_building.floors)
                npc_x = target_building.x + random.randint(50, target_building.width - 50)
                npc_y = target_floor['y']
                
                # Create NPC
                npc = Fighter(npc_x, npc_y, NPC_COLOR, is_player=False, is_merchant=False)
                npc.inside_building = target_building
                npc.building_floor_num = target_floor['floor_num']
                npc.on_ground = True
                npc.vy = 0
                npc.is_npc = True
                npc.hp_max = 50  # NPCs are not fighters
                npc.hp = npc.hp_max
                
                # Find a different location for the dog (different floor or building)
                dog_building = random.choice(self.buildings)
                dog_floor = random.choice(dog_building.floors)
                dog_x = dog_building.x + random.randint(50, dog_building.width - 50)
                dog_y = dog_floor['y']
                
                # Create dog
                dog = Dog(dog_x, dog_y)
                dog.inside_building = dog_building
                dog.building_floor_num = dog_floor['floor_num']
                
                # Create quest
                quest = Quest(
                    quest_type="find_dog",
                    npc=npc,
                    description="Help me find my dog",
                    target_building=target_building,
                    target_floor=target_floor,
                    dog=dog
                )
                
                self.quests.append(quest)
                self.units.append(npc)
                self.dogs.append(dog)
    
    def generate_starter_npc(self):
        """Generate starter NPC at the beginning of stage 1."""
        # Place NPC near the start of the map
        starter_x = 150
        starter_y = GROUND_Y
        
        starter_npc = Fighter(starter_x, starter_y, NPC_COLOR, is_player=False, is_merchant=False)
        starter_npc.is_npc = True
        starter_npc.hp_max = 50
        starter_npc.hp = starter_npc.hp_max
        starter_npc.has_quest = True
        starter_npc.dialogue = "Help! Our neighborhood has been overrun with bandits!"
        
        # Create "save our city" quest (offered, not active)
        quest = Quest(
            quest_type="save_city",
            npc=starter_npc,
            description="Help! Our neighborhood has been overrun with bandits!",
            target_stage=1
        )
        quest.status = "offered"  # Quest starts as offered, not active
        
        self.quests.append(quest)
        self.units.append(starter_npc)
    
    def check_nearby_npc(self, player):
        """Check if player is near an NPC. Returns NPC and quest if available."""
        for unit in self.units:
            if unit.is_npc and not unit.is_dead() and getattr(unit, 'has_quest', False):
                # Check distance to NPC
                dx = unit.x - player.x
                dy = unit.y - player.y
                dist_sq = dx*dx + dy*dy
                if dist_sq < 2500:  # Within 50 pixels
                    # Find quest for this NPC
                    for quest in self.quests:
                        if quest.npc == unit and quest.status == "offered":
                            return unit, quest
        return None, None
    
    def accept_quest(self, quest):
        """Accept a quest - change status from offered to active."""
        if quest.status == "offered":
            quest.status = "active"
            self.pickup_notifications.append(PickupNotification(f"Quest Accepted: {quest.description}"))
    
    def check_nearby_completed_quest_npc(self, player):
        """Check if player is near an NPC with a completed quest. Returns NPC and quest if available."""
        for unit in self.units:
            if unit.is_npc and not unit.is_dead() and getattr(unit, 'has_quest', False):
                # Check distance to NPC
                dx = unit.x - player.x
                dy = unit.y - player.y
                dist_sq = dx*dx + dy*dy
                if dist_sq < 2500:  # Within 50 pixels
                    # Find completed quest for this NPC
                    for quest in self.quests:
                        if quest.npc == unit and quest.status == "completed":
                            return unit, quest
        return None, None
    
    def claim_quest_reward(self, quest, player):
        """Claim quest reward from NPC - give gold and remove quest."""
        if quest.status == "completed":
            reward = getattr(quest, 'reward_money', 0) or 0
            player.money += reward
            self.pickup_notifications.append(PickupNotification(f"Quest Reward: {reward} gold!"))
            # Remove quest from active list
            if quest in self.quests:
                self.quests.remove(quest)

    def update_quests(self, player):
        """Update quest status and handle quest logic."""
        for quest in self.quests[:]:
            if quest.status != "active":
                continue
            
            if quest.quest_type == "defeat_enemies":
                # Check if companion NPC died
                if quest.companion_npc and quest.companion_npc.is_dead():
                    quest.status = "failed"
                    self.pickup_notifications.append(PickupNotification("Quest Failed: Companion died!"))
                    continue
                
                # Check if player left building - companion should stop following
                if self.player_inside_building != quest.target_building:
                    if quest.companion_npc:
                        quest.companion_npc.follow_target = None
                
                # Count remaining enemies in building (apartment enemies only)
                current_enemy_count = sum(len(f.get('apartment_enemies', [])) for f in quest.target_building.floors)
                # Filter out NPCs from enemy count
                for floor in quest.target_building.floors:
                    for enemy in floor.get('apartment_enemies', []):
                        if enemy.is_npc:
                            current_enemy_count -= 1
                
                # Quest complete if all enemies defeated
                if current_enemy_count == 0 and quest.status == "active":
                    quest.status = "completed"
                    self.pickup_notifications.append(PickupNotification("Quest Complete! Return to quest giver for reward."))
                    # Set reward
                    quest.reward_money = random.randint(50, 150)
                    # Companion NPC stops following
                    if quest.companion_npc:
                        quest.companion_npc.follow_target = None
            
            elif quest.quest_type == "find_dog":
                # Check if dog is near merchant and player is near merchant (dog was sold)
                if quest.dog:
                    for merchant in self.units:
                        if merchant.is_merchant and not merchant.is_dead():
                            merchant_rect = merchant.rect
                            dog_rect = quest.dog.rect
                            player_rect = player.rect
                            # Check if dog and player are both near merchant (within 50 pixels)
                            dog_dx = merchant_rect.centerx - dog_rect.centerx
                            dog_dy = merchant_rect.centery - dog_rect.centery
                            dog_dist_sq = dog_dx*dog_dx + dog_dy*dog_dy
                            player_dx = merchant_rect.centerx - player_rect.centerx
                            player_dy = merchant_rect.centery - player_rect.centery
                            player_dist_sq = player_dx*player_dx + player_dy*player_dy
                            if dog_dist_sq < 2500 and player_dist_sq < 2500:  # Both within 50 pixels
                                # Dog is near merchant with player - consider it sold
                                quest.status = "failed"
                                self.pickup_notifications.append(PickupNotification("Quest Failed: Dog was sold!"))
                                if quest.dog in self.dogs:
                                    self.dogs.remove(quest.dog)
                                quest.dog = None
                                break
                
                # Check if dog reached NPC
                if quest.dog and quest.npc:
                    dog_rect = quest.dog.rect
                    npc_rect = quest.npc.rect
                    if dog_rect.colliderect(npc_rect):
                        # Dog found NPC - quest complete
                        quest.status = "completed"
                        self.pickup_notifications.append(PickupNotification("Quest Completed: Dog returned!"))
                        # Remove dog from game
                        if quest.dog in self.dogs:
                            self.dogs.remove(quest.dog)
                        quest.dog = None
                        # Set reward
                        quest.reward_money = random.randint(50, 150)
            
            elif quest.quest_type == "save_city":
                # Check if all enemies in target stage are defeated
                if self.stage == quest.target_stage:
                    # Count all enemies in stage buildings (apartment enemies only)
                    total_enemies = 0
                    for building in self.buildings:
                        for floor in building.floors:
                            for enemy in floor.get('apartment_enemies', []):
                                if not enemy.is_npc and not enemy.is_dead():
                                    total_enemies += 1
                    
                    if total_enemies == 0 and quest.status == "active":
                        quest.status = "completed"
                        self.pickup_notifications.append(PickupNotification("Quest Complete! Return to quest giver for reward."))
                        # Set reward
                        quest.reward_money = random.randint(100, 200)
    
    def update_companion_npc(self, companion, player, building, floor_num):
        """Update companion NPC to follow player and fight enemies."""
        if companion.is_dead():
            return
        
        # Only follow if player is in the same building
        if building and companion.inside_building == building:
            companion.follow_target = player
            companion.building_floor_num = floor_num
            
            # Move towards player
            dx = player.x - companion.x
            dist = abs(dx)
            
            if dist > 50:  # Follow distance
                companion.vx = 4.0 if dx > 0 else -4.0
                companion.facing = 1 if dx > 0 else -1
            else:
                companion.vx = 0
            
            # Attack nearby enemies (in apartments)
            if building:
                floor = building.floors[floor_num]
                for enemy in floor.get('apartment_enemies', []):
                    if enemy.is_dead() or enemy.is_npc:
                        continue
                    enemy_dx = enemy.x - companion.x
                    enemy_dist = abs(enemy_dx)
                    if enemy_dist < 80:  # Attack range
                        companion.start_attack("swing")
                        break
        else:
            # Player left building - stop following
            companion.follow_target = None
            companion.vx = 0
        
        # Apply gravity and movement
        companion.apply_gravity()
        if building:
            floor = building.floors[floor_num]
            floor_platform = Platform(building.x, floor['y'], building.width, 5)
            building_bounds = self.get_building_bounds()
            companion.move_and_collide([floor_platform], building_bounds)
        companion.update_attack_state()

    def empower_merchant(self, merchant):
        mult = 1.5  # Reduced from 3.0 - merchant is tough but killable
        merchant.hp_max = int(merchant.hp_max * mult)
        merchant.hp = merchant.hp_max
        merchant.base_dmg = int(merchant.base_dmg * mult)
        merchant.base_armor = int(merchant.base_armor * mult) + 3
        if merchant.weapon:
            merchant.weapon.dmg = int(merchant.weapon.dmg * mult)
            merchant.weapon.knockback = merchant.weapon.knockback * 1.2
        if merchant.armor_item:
            merchant.armor_item.armor = int(merchant.armor_item.armor * mult) + 2
        merchant.money *= 2

    def generate(self):
        self.generate_background()
        self.generate_platforms_ladders_doors()
    
    def check_building_entry(self, player):
        """Check if player can enter a building at the door."""
        if self.player_inside_building is not None:
            return None
        
        for building in self.buildings:
            # Door collision area - extend down a bit for easier access
            door_rect = pygame.Rect(building.entry_door_x - building.entry_door_width // 2, 
                                   building.entry_door_y - building.entry_door_height - 10, 
                                   building.entry_door_width, building.entry_door_height + 20)
            if player.rect.colliderect(door_rect):
                return building
        return None
    
    def enter_building(self, player, building):
        """Enter a building - move player to first floor hall."""
        self.player_inside_building = building
        self.player_current_floor = 0
        self.player_in_apartment = False  # Start in hall
        floor = building.floors[0]
        player.x = building.x + 50
        player.y = floor['y']
        player.vx = 0
        player.vy = 0
    
    def check_apartment_door(self, player):
        """Check if player is at an apartment door. Returns True if can enter/exit."""
        try:
            if self.player_inside_building is None:
                return False
            
            building = self.player_inside_building
            if building is None or self.player_current_floor < 0 or self.player_current_floor >= len(building.floors):
                return False
            
            floor = building.floors[self.player_current_floor]
            if 'apartment_door_x' not in floor:
                return False
            
            apartment_door_x = floor['apartment_door_x']
            door_rect = pygame.Rect(apartment_door_x - 20, floor['y'] - building.floor_height, 40, building.floor_height)
            return player.rect.colliderect(door_rect)
        except (KeyError, IndexError, AttributeError):
            return False
    
    def enter_apartment(self, player):
        """Enter apartment room from hall."""
        try:
            if self.player_inside_building is None:
                return
            if self.player_current_floor < 0 or self.player_current_floor >= len(self.player_inside_building.floors):
                return
            self.player_in_apartment = True
            building = self.player_inside_building
            floor = building.floors[self.player_current_floor]
            if 'apartment_door_x' not in floor:
                return
            # Move player into apartment room (to the right of door)
            player.x = floor['apartment_door_x'] + 50
            player.y = floor['y']
        except (KeyError, IndexError, AttributeError):
            pass
    
    def exit_apartment(self, player):
        """Exit apartment room to hall."""
        try:
            if self.player_inside_building is None:
                return
            if self.player_current_floor < 0 or self.player_current_floor >= len(self.player_inside_building.floors):
                return
            self.player_in_apartment = False
            building = self.player_inside_building
            floor = building.floors[self.player_current_floor]
            if 'apartment_door_x' not in floor:
                return
            # Move player to hall (to the left of door)
            player.x = floor['apartment_door_x'] - 50
            player.y = floor['y']
        except (KeyError, IndexError, AttributeError):
            pass
    
    def exit_building(self, player):
        """Exit the current building."""
        if self.player_inside_building:
            building = self.player_inside_building
            player.x = building.entry_door_x
            player.y = GROUND_Y  # Exit at ground level
            self.player_inside_building = None
            self.player_current_floor = 0
            self.player_in_apartment = False
    
    def check_elevator(self, player):
        """Check if player is at an elevator. Returns 'up', 'down', 'exit', or None."""
        if self.player_inside_building is None:
            return None
        
        # Only check elevators when in hall (not in apartment)
        if self.player_in_apartment:
            return None
        
        building = self.player_inside_building
        floor = building.floors[self.player_current_floor]
        
        # Check exit elevator (double down arrow) - only on ground floor
        if self.player_current_floor == 0:
            exit_elevator_rect = pygame.Rect(floor['elevator_exit_x'] - 15, floor['y'] - building.floor_height, 30, building.floor_height)
            if player.rect.colliderect(exit_elevator_rect):
                return 'exit'
        
        # Check up elevator
        if self.player_current_floor < building.num_floors - 1:
            up_elevator_rect = pygame.Rect(floor['elevator_up_x'] - 15, floor['y'] - building.floor_height, 30, building.floor_height)
            if player.rect.colliderect(up_elevator_rect):
                return 'up'
        
        # Check down elevator
        if self.player_current_floor > 0:
            down_elevator_rect = pygame.Rect(floor['elevator_down_x'] - 15, floor['y'] - building.floor_height, 30, building.floor_height)
            if player.rect.colliderect(down_elevator_rect):
                return 'down'
        
        return None
    
    def use_elevator(self, player, direction):
        """Move player up or down one floor."""
        if not self.player_inside_building:
            return

        if direction == 'up' and self.player_current_floor < self.player_inside_building.num_floors - 1:
            self.player_current_floor += 1
            floor = self.player_inside_building.floors[self.player_current_floor]
            player.x = self.player_inside_building.x + 50
            player.y = floor['y']
            player.vx = 0
            player.vy = 0
        elif direction == 'down' and self.player_current_floor > 0:
            self.player_current_floor -= 1
            floor = self.player_inside_building.floors[self.player_current_floor]
            player.x = self.player_inside_building.x + 50
            player.y = floor['y']
            player.vx = 0
            player.vy = 0
        
            floor = self.player_inside_building.floors[self.player_current_floor]
            player.x = self.player_inside_building.x + 50
            player.y = floor['y']
            player.vx = 0
            player.vy = 0
    
    
    def get_current_floor_enemies(self):
        """Get enemies on the current floor (only if player is in apartment)."""
        if self.player_inside_building:
            building = self.player_inside_building
            floor = building.floors[self.player_current_floor]
            # If player is in apartment, return apartment enemies; if in hall, return empty (halls are safe)
            if self.player_in_apartment:
                return floor.get('apartment_enemies', [])
            else:
                return []  # Halls are safe - no enemies
        return []
    
    def get_current_floor_containers(self):
        """Get containers on the current floor."""
        if self.player_inside_building:
            building = self.player_inside_building
            floor = building.floors[self.player_current_floor]
            return floor['containers']
        return []
    
    def get_current_floor_assets(self):
        """Get background assets on the current floor."""
        if self.player_inside_building:
            building = self.player_inside_building
            floor = building.floors[self.player_current_floor]
            return floor['background_assets']
        return []
    
    def check_container_loot(self, player):
        """Check if player can loot a container on current floor. Returns container or None."""
        if self.player_inside_building is None:
            return None
        
        building = self.player_inside_building
        floor = building.floors[self.player_current_floor]
        
        for container in floor['containers']:
            if container['looted']:
                continue
            container_rect = pygame.Rect(container['x'] - 20, container['y'] - 30, 40, 30)
            if player.rect.colliderect(container_rect):
                return container
        return None
    
    def add_potion_to_inventory(self, player, potion):
        """Add potion to inventory, stacking if already exists."""
        # Check if player already has a health potion
        for item in player.inventory:
            if item.is_potion and item.name == potion.name:
                # Stack the potions
                item.count += potion.count
                # Show pickup notification
                self.pickup_notifications.append(PickupNotification(f"Picked up: {potion.name} (x{potion.count})"))
                return
        
        # No existing potion, add new one
        player.inventory.append(potion)
        # Show pickup notification
        self.pickup_notifications.append(PickupNotification(f"Picked up: {potion.name} (x{potion.count})"))
    
    def loot_container(self, player, container):
        """Loot a container - add item to inventory if it has one."""
        if container['looted'] or not container['item']:
            return False
        
        item = container['item']
        # Stack potions if it's a potion
        if item.is_potion:
            self.add_potion_to_inventory(player, item)
            # Show pickup notification
            self.pickup_notifications.append(PickupNotification(f"Picked up: {item.name} (x{item.count})"))
        else:
            player.inventory.append(item)
            # Show pickup notification
            self.pickup_notifications.append(PickupNotification(f"Picked up: {item.name}"))
        container['looted'] = True
        return True
    
    def add_pickup_notification(self, text):
        """Add a pickup notification."""
        self.pickup_notifications.append(PickupNotification(text))
    
    def get_building_bounds(self):
        """Get building bounds for collision: (x, y, width, floor_y, ceiling_y) or None if outside."""
        if self.player_inside_building:
            building = self.player_inside_building
            floor = building.floors[self.player_current_floor]
            floor_y = floor['y']
            ceiling_y = floor_y - building.floor_height
            return (building.x, building.y, building.width, floor_y, ceiling_y)
        return None
    
    def get_enemy_building_bounds(self, enemy):
        """Get building bounds for an enemy if they're inside a building."""
        if enemy.inside_building:
            building = enemy.inside_building
            floor = building.floors[enemy.building_floor_num]
            floor_y = floor['y']
            ceiling_y = floor_y - building.floor_height
            return (building.x, building.y, building.width, floor_y, ceiling_y)
        return None
    
    def is_enemy_visible_through_window(self, enemy, camera_x):
        """Check if an enemy inside a building is visible through any window."""
        if not enemy.inside_building:
            return True  # Enemies outside buildings are always visible
        
        building = enemy.inside_building
        floor = building.floors[enemy.building_floor_num]
        
        # Check if enemy is near any window on their floor
        enemy_rect = enemy.rect
        for window in floor['windows']:
            # Window area - enemy must be horizontally aligned with window
            # and vertically within the window's vertical range
            win_left = window['x'] - 15  # Slight expansion for visibility
            win_right = window['x'] + window['width'] + 15
            win_top = window['y'] - 5
            win_bottom = window['y'] + window['height'] + 5
            
            # Check if enemy's center or edges overlap with window area
            enemy_center_x = enemy_rect.centerx
            if (win_left <= enemy_center_x <= win_right and
                enemy_rect.bottom > win_top and enemy_rect.top < win_bottom):
                return True
        
        return False

    def draw_background(self, surface, camera_x, camera_y=0):
        # Very dark sky (almost black) - buildings will fill the space
        surface.fill((8, 6, 12))  # Very dark purple-black
        
        # Draw hillside cityscape (distant layer, parallax effect - moves slower)
        parallax_factor = 0.3  # Moves at 30% of camera speed
        hillside_camera = int(camera_x * parallax_factor)
        
        for building_data in self.hillside_buildings:
            b_rect = building_data['rect'].move(-hillside_camera, 0)
            
            # Only draw if visible
            if b_rect.right > -50 and b_rect.left < WIDTH + 50:
                # Building base
                pygame.draw.rect(surface, building_data['color'], b_rect)
                
                # Windows (smaller and dimmer for distance)
                for window_data in building_data['windows']:
                    if len(window_data) == 5:
                        wx, wy, wcolor, ww, wh = window_data
                    else:
                        wx, wy, wcolor = window_data
                        ww, wh = 1, 1
                    win_x = wx - hillside_camera
                    if 0 <= win_x < WIDTH and b_rect.top <= wy <= b_rect.bottom:
                        pygame.draw.rect(surface, wcolor, 
                                        (win_x, wy, ww, wh))
                
                # Draw building base on hill
                hill_y = building_data['hill_y']
                pygame.draw.line(surface, (80, 60, 40),
                               (b_rect.left, hill_y),
                               (b_rect.right, hill_y), 2)
        
        # Draw reflections area (wet ground)
        reflection_y = GROUND_Y
        reflection_height = HEIGHT - GROUND_Y
        reflection_surface = pygame.Surface((WIDTH, reflection_height), pygame.SRCALPHA)
        
        # Draw buildings with windows (foreground cityscape) - back layer first
        for building_data in self.bg_buildings_detailed:
            if building_data.get('layer') == 'back':
                # Back layer moves at 60% speed
                parallax_camera = int(camera_x * 0.6)
                b_rect = building_data['rect'].move(-parallax_camera, 0)
                
                # Only draw if visible
                if b_rect.right > -20 and b_rect.left < WIDTH + 20:
                    # Building base
                    pygame.draw.rect(surface, building_data['color'], b_rect)
                    
                    # Windows
                    for window_data in building_data['windows']:
                        if len(window_data) == 5:
                            wx, wy, wcolor, ww, wh = window_data
                        else:
                            wx, wy, wcolor = window_data
                            ww, wh = 2, 2
                        win_x = wx - parallax_camera
                        if -5 <= win_x < WIDTH + 5 and b_rect.top <= wy <= b_rect.bottom:
                            pygame.draw.rect(surface, wcolor, 
                                            (win_x, wy, ww, wh))
                            # Glow effect
                            glow_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                            glow_color = (*wcolor[:3], 60)
                            pygame.draw.circle(glow_surf, glow_color, (3, 3), 3)
                            surface.blit(glow_surf, (win_x - 2, wy - 2))
        
        # Draw mid-layer buildings
        for building_data in self.bg_buildings_detailed:
            if building_data.get('layer') == 'mid':
                # Mid layer moves at 75% speed
                parallax_camera = int(camera_x * 0.75)
                b_rect = building_data['rect'].move(-parallax_camera, 0)
                
                # Only draw if visible
                if b_rect.right > -20 and b_rect.left < WIDTH + 20:
                    # Building base
                    pygame.draw.rect(surface, building_data['color'], b_rect)
                    
                    # Windows
                    for window_data in building_data['windows']:
                        if len(window_data) == 5:
                            wx, wy, wcolor, ww, wh = window_data
                        else:
                            wx, wy, wcolor = window_data
                            ww, wh = 2, 2
                        win_x = wx - parallax_camera
                        if -5 <= win_x < WIDTH + 5 and b_rect.top <= wy <= b_rect.bottom:
                            pygame.draw.rect(surface, wcolor, 
                                            (win_x, wy, ww, wh))
                            # Glow effect
                            glow_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                            glow_color = (*wcolor[:3], 60)
                            pygame.draw.circle(glow_surf, glow_color, (3, 3), 3)
                            surface.blit(glow_surf, (win_x - 2, wy - 2))
        
        # Draw streetlights with glow (move at 80% speed for mid-ground effect)
        for light in self.streetlights:
            parallax_camera = int(camera_x * 0.8)
            lx = light['x'] - parallax_camera
            if -50 <= lx <= WIDTH + 50:
                # Glow circle
                glow_surf = pygame.Surface((light['glow_radius'] * 2, 
                                           light['glow_radius'] * 2), 
                                          pygame.SRCALPHA)
                for radius in range(light['glow_radius'], 0, -2):
                    alpha = max(0, 100 - radius * 3)
                    pygame.draw.circle(glow_surf, (255, 180, 80, alpha),
                                     (light['glow_radius'], light['glow_radius']), radius)
                surface.blit(glow_surf, 
                           (lx - light['glow_radius'], 
                            light['y'] - light['glow_radius']))
                
                # Light pole
                pygame.draw.line(surface, (60, 60, 60),
                               (lx, light['y']),
                               (lx, GROUND_Y), 3)
                # Lamp
                pygame.draw.circle(surface, (255, 200, 100),
                                 (lx, light['y']), 4)
        
        # Draw front layer buildings (move at 90% speed)
        for building_data in self.bg_buildings_detailed:
            if building_data.get('layer') == 'front':
                parallax_camera = int(camera_x * 0.9)
                b_rect = building_data['rect'].move(-parallax_camera, 0)
                
                # Only draw if visible
                if b_rect.right > 0 and b_rect.left < WIDTH:
                    # Building base
                    pygame.draw.rect(surface, building_data['color'], b_rect)
                    
                    # Windows
                    for window_data in building_data['windows']:
                        if len(window_data) == 5:
                            wx, wy, wcolor, ww, wh = window_data
                        else:
                            wx, wy, wcolor = window_data
                            ww, wh = 2, 2
                        win_x = wx - parallax_camera
                        if 0 <= win_x < WIDTH and b_rect.top <= wy <= b_rect.bottom:
                            pygame.draw.rect(surface, wcolor, 
                                            (win_x, wy, ww, wh))
                            # Glow effect
                            glow_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                            glow_color = (*wcolor[:3], 60)
                            pygame.draw.circle(glow_surf, glow_color, (3, 3), 3)
                            surface.blit(glow_surf, (win_x - 2, wy - 2))
        
        # Draw ground with reflections (moves at 100% speed - foreground)
        # Make ground darker to blend with buildings
        ground_rect = pygame.Rect(0 - camera_x, GROUND_Y,
                                  WORLD_WIDTH, HEIGHT - GROUND_Y)
        pygame.draw.rect(surface, (12, 10, 15), ground_rect)
        
        # Draw building reflections (simplified) - use same parallax as buildings
        for building_data in self.bg_buildings_detailed:
            if building_data.get('layer') == 'back':
                parallax_camera = int(camera_x * 0.6)
            elif building_data.get('layer') == 'mid':
                parallax_camera = int(camera_x * 0.75)
            else:
                parallax_camera = int(camera_x * 0.9)
            b_rect = building_data['rect'].move(-parallax_camera, 0)
            if b_rect.right > 0 and b_rect.left < WIDTH:
                # Reflection (flipped and darker)
                refl_rect = pygame.Rect(b_rect.x, 
                                       GROUND_Y + (GROUND_Y - b_rect.bottom),
                                       b_rect.width, b_rect.height)
                if refl_rect.bottom > GROUND_Y:
                    refl_rect.height = max(0, GROUND_Y + HEIGHT - refl_rect.top)
                    if refl_rect.height > 0:
                        refl_color = tuple(max(0, c - 40) for c in building_data['color'])
                        pygame.draw.rect(surface, refl_color, refl_rect)
                        
                        # Reflected windows (dimmer)
                        for window_data in building_data['windows']:
                            if len(window_data) == 5:
                                wx, wy, wcolor, ww, wh = window_data
                            else:
                                wx, wy, wcolor = window_data
                                ww, wh = 2, 2
                            win_x = wx - parallax_camera
                            refl_y = GROUND_Y + (GROUND_Y - wy)
                            if 0 <= win_x < WIDTH and refl_y < HEIGHT:
                                refl_wcolor = tuple(max(0, c - 60) for c in wcolor)
                                pygame.draw.rect(surface, refl_wcolor,
                                               (win_x, refl_y, ww, wh))
        
        # Draw light reflections on ground
        for light in self.streetlights:
            parallax_camera = int(camera_x * 0.8)
            lx = light['x'] - parallax_camera
            if -50 <= lx <= WIDTH + 50:
                refl_y = GROUND_Y + 10
                refl_glow = pygame.Surface((light['glow_radius'] * 2, 30), 
                                          pygame.SRCALPHA)
                for radius in range(light['glow_radius'], 0, -2):
                    alpha = max(0, 80 - radius * 2)
                    pygame.draw.ellipse(refl_glow, (255, 180, 80, alpha),
                                      (light['glow_radius'] - radius, 0,
                                       radius * 2, 30))
                surface.blit(refl_glow, 
                           (lx - light['glow_radius'], refl_y))

    def draw_static_level(self, surface, camera_x, camera_y=0, player=None):
        # Draw ground platform
        for p in self.platforms:
            p_rect = p.rect.move(-camera_x, -camera_y)
            pygame.draw.rect(surface, (90, 70, 70), p_rect)
        
        # Draw buildings
        for building in self.buildings:
            if self.player_inside_building is building:
                # Draw interior of current building
                self.draw_building_interior(surface, camera_x, camera_y, building, player)
            else:
                # Draw exterior of building
                self.draw_building_exterior(surface, camera_x, building)
        
        # Draw ground graphic to cover bottom of buildings (drawn after buildings)
        ground_graphic_height = 30  # Height of ground graphic above GROUND_Y
        ground_graphic_rect = pygame.Rect(0 - camera_x, GROUND_Y - ground_graphic_height,
                                         WORLD_WIDTH, ground_graphic_height)
        # Draw ground with texture/pattern
        base_ground_color = (25, 20, 18)
        pygame.draw.rect(surface, base_ground_color, ground_graphic_rect)
        
        # Add some texture lines to make it look like ground/asphalt
        for i in range(0, WORLD_WIDTH, 40):
            line_x = i - camera_x
            if 0 <= line_x < WIDTH:
                pygame.draw.line(surface, (20, 16, 14), 
                                (line_x, GROUND_Y - ground_graphic_height),
                                (line_x, GROUND_Y), 1)
        
        # Add a darker line at the top edge to separate from buildings
        pygame.draw.line(surface, (15, 12, 10),
                        (0 - camera_x, GROUND_Y - ground_graphic_height),
                        (WORLD_WIDTH - camera_x, GROUND_Y - ground_graphic_height), 2)
    
    def draw_building_exterior(self, surface, camera_x, building):
        """Draw the exterior of a building."""
        b_rect = building.exterior_rect.move(-camera_x, 0)
        if b_rect.right > -50 and b_rect.left < WIDTH + 50:
            # Save current random state
            import random as random_module
            old_state = random_module.getstate()
            
            # Use building's x position as seed for random but consistent texture per building
            building_seed = int(building.x) % 10000
            random_module.seed(building_seed)
            
            try:
                # Random base color per building (darker, varied)
                base_color_variations = [
                    (35, 35, 40), (42, 38, 45), (38, 42, 48), (40, 40, 45),
                    (45, 40, 42), (38, 45, 40), (40, 38, 48)
                ]
                base_color = random_module.choice(base_color_variations)
                pygame.draw.rect(surface, base_color, b_rect)
                
                # Random texture size per building
                texture_size_options = [15, 18, 20, 22, 25, 30, 35]
                texture_size = random_module.choice(texture_size_options)
                
                # Sporadic texture pattern - random rectangles, not uniform grid
                num_texture_patches = random_module.randint(30, 80)  # Random number of texture patches
                texture_patches = []
                
                for _ in range(num_texture_patches):
                    # Random position and size for each patch
                    patch_x = random_module.randint(b_rect.left, b_rect.right - texture_size)
                    patch_y = random_module.randint(b_rect.top, b_rect.bottom - texture_size)
                    patch_w = random_module.randint(texture_size // 2, texture_size * 2)
                    patch_h = random_module.randint(texture_size // 2, texture_size * 2)
                    
                    # Random color variation (more dramatic)
                    color_var = random_module.randint(-25, 25)
                    texture_color = (
                        max(20, min(65, base_color[0] + color_var)),
                        max(20, min(65, base_color[1] + color_var)),
                        max(25, min(70, base_color[2] + color_var))
                    )
                    
                    texture_patches.append((patch_x, patch_y, patch_w, patch_h, texture_color))
                
                # Draw texture patches
                for patch_x, patch_y, patch_w, patch_h, patch_color in texture_patches:
                    patch_rect = pygame.Rect(patch_x, patch_y, patch_w, patch_h)
                    patch_rect = patch_rect.clip(b_rect)
                    if patch_rect.width > 0 and patch_rect.height > 0:
                        pygame.draw.rect(surface, patch_color, patch_rect)
                
                # Random vertical lines - sporadic placement, not uniform
                num_panels = random_module.randint(2, 8)
                panel_positions = []
                for _ in range(num_panels):
                    panel_x = random_module.randint(b_rect.left + 20, b_rect.right - 20)
                    panel_positions.append(panel_x)
                
                # Remove duplicates and sort
                panel_positions = sorted(set(panel_positions))
                
                for panel_x in panel_positions:
                    # Random chance to draw line, and random line color
                    if random_module.random() < 0.6:  # 60% chance to draw
                        line_color_variants = [
                            (30, 30, 35), (35, 35, 40), (45, 40, 45),
                            (25, 35, 40), (40, 30, 35)
                        ]
                        line_color = random_module.choice(line_color_variants)
                        line_width = random_module.randint(1, 2)
                        # Sometimes partial lines (not full height)
                        if random_module.random() < 0.3:
                            # Partial line
                            line_start_y = random_module.randint(b_rect.top, b_rect.top + b_rect.height // 3)
                            line_end_y = random_module.randint(b_rect.top + b_rect.height * 2 // 3, b_rect.bottom)
                            pygame.draw.line(surface, line_color,
                                           (panel_x, line_start_y),
                                           (panel_x, line_end_y), line_width)
                        else:
                            # Full line
                            pygame.draw.line(surface, line_color,
                                           (panel_x, b_rect.top),
                                           (panel_x, b_rect.bottom), line_width)
            finally:
                # Restore random state
                random_module.setstate(old_state)
            
            # Windows on exterior
            window_colors = [
                (255, 200, 100),  # Bright orange
                (255, 220, 150),  # Bright yellow
                (200, 150, 100),  # Bright dim orange
            ]
            for floor in building.floors:
                for window in floor['windows']:
                    win_x = window['x'] - camera_x
                    win_y = window['y']
                    if -10 <= win_x < WIDTH + 10:
                        # First floor windows are see-through (drawn later)
                        if floor['floor_num'] == 0:
                            # Draw window frame but make it semi-transparent
                            win_surf = pygame.Surface((window['width'], window['height']), pygame.SRCALPHA)
                            win_color = random.choice(window_colors)
                            pygame.draw.rect(win_surf, (*win_color, 180), (0, 0, window['width'], window['height']))
                            surface.blit(win_surf, (win_x, win_y))
                        else:
                            # Regular windows
                            win_color = random.choice(window_colors)
                            pygame.draw.rect(surface, win_color, 
                                            (win_x, win_y, window['width'], window['height']))
            
            # Entry door - sliding glass door style
            door_x = building.entry_door_x - camera_x
            door_y = building.entry_door_y
            door_w = building.entry_door_width
            door_h = building.entry_door_height
            if -50 <= door_x < WIDTH + 50:
                # Glass door (semi-transparent)
                door_rect = pygame.Rect(door_x - door_w // 2, door_y - door_h, door_w, door_h)
                door_surf = pygame.Surface((door_w, door_h), pygame.SRCALPHA)
                pygame.draw.rect(door_surf, (100, 150, 200, 180), (0, 0, door_w, door_h))  # Light blue glass
                surface.blit(door_surf, (door_x - door_w // 2, door_y - door_h))
                # Frame
                pygame.draw.rect(surface, (60, 100, 150), door_rect, 3)
                # Door panels (sliding glass door has two panels)
                panel_width = door_w // 2 - 2
                pygame.draw.line(surface, (40, 60, 80), 
                               (door_x - panel_width // 2, door_y - door_h),
                               (door_x - panel_width // 2, door_y), 2)
                # Door handle
                pygame.draw.circle(surface, (200, 200, 200), (door_x + door_w // 2 - 10, door_y - door_h // 2), 4)
            
            # Draw enemies visible through first floor windows (drawn after building so they appear on top)
            # This is handled in main drawing loop now
    
    def draw_building_interior(self, surface, camera_x, camera_y, building, player):
        """Draw the interior of a building when player is inside."""
        floor = building.floors[self.player_current_floor]
        floor_y = floor['y']
        
        # Draw dark overlay covering everything except current room
        dark_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(dark_overlay, (0, 0, 0, 220), (0, 0, WIDTH, HEIGHT))
        
        # Cut out the current room area (bright area)
        room_left = building.x - camera_x
        room_right = room_left + building.width
        room_top = floor_y - building.floor_height - camera_y
        room_bottom = floor_y - camera_y
        
        # Clear the room area from dark overlay
        if room_left < WIDTH and room_right > 0:
            clear_top = max(0, room_top)
            clear_bottom = min(HEIGHT, room_bottom)
            clear_left = max(0, room_left)
            clear_right = min(WIDTH, room_right)
            if clear_bottom > clear_top and clear_right > clear_left:
                dark_overlay.set_clip(pygame.Rect(clear_left, clear_top, clear_right - clear_left, clear_bottom - clear_top))
                dark_overlay.fill((0, 0, 0, 0))
                dark_overlay.set_clip(None)
        
        # Also clear the back wall area (keep it visible)
        back_wall_left = building.x - camera_x
        back_wall_right = back_wall_left + 20
        if back_wall_left < WIDTH and back_wall_right > 0:
            wall_top = max(0, room_top)
            wall_bottom = min(HEIGHT, room_bottom)
            wall_left = max(0, back_wall_left)
            wall_right = min(WIDTH, back_wall_right)
            if wall_bottom > wall_top and wall_right > wall_left:
                dark_overlay.set_clip(pygame.Rect(wall_left, wall_top, wall_right - wall_left, wall_bottom - wall_top))
                dark_overlay.fill((0, 0, 0, 0))
                dark_overlay.set_clip(None)
        
        # Apply dark overlay
        surface.blit(dark_overlay, (0, 0))
        
        # Floor and ceiling
        floor_rect = pygame.Rect(building.x - camera_x, floor_y - camera_y, building.width, 5)
        ceiling_rect = pygame.Rect(building.x - camera_x, floor_y - building.floor_height - camera_y, building.width, 5)
        pygame.draw.rect(surface, (80, 80, 80), floor_rect)
        pygame.draw.rect(surface, (60, 60, 60), ceiling_rect)
        
        # Background wall (full width, behind everything)
        bg_wall_rect = pygame.Rect(building.x - camera_x, 
                                   floor_y - building.floor_height - camera_y,
                                   building.width, building.floor_height)
        pygame.draw.rect(surface, (45, 45, 50), bg_wall_rect)
        
        # Back wall with windows (left side, thinner)
        back_wall_rect = pygame.Rect(building.x - camera_x, 
                                     floor_y - building.floor_height - camera_y,
                                     20, building.floor_height)
        pygame.draw.rect(surface, (50, 50, 55), back_wall_rect)
        
        # Draw windows in back wall - show background through them
        for window in floor['windows']:
            win_x = window['x'] - camera_x
            win_y = window['y'] - camera_y
            if 0 <= win_x < WIDTH:
                # Window frame
                pygame.draw.rect(surface, (30, 30, 35), 
                               (win_x, win_y, window['width'], window['height']))
                # Window shows background (drawn as transparent area)
                # We'll draw a darker version to simulate looking out
                win_surf = pygame.Surface((window['width'], window['height']), pygame.SRCALPHA)
                pygame.draw.rect(win_surf, (20, 20, 30, 200), 
                                (0, 0, window['width'], window['height']))
                surface.blit(win_surf, (win_x, win_y))
        
        # Front wall (where player entered) - make it invisible/transparent
        # Actually, we don't draw it so player can see out
        
        # Up elevator door (only visible in hall, not in apartment)
        if not self.player_in_apartment and self.player_current_floor < building.num_floors - 1:
            up_elevator_x = floor['elevator_up_x'] - camera_x
            up_elevator_rect = pygame.Rect(up_elevator_x - 15, floor_y - building.floor_height - camera_y, 30, building.floor_height)
            pygame.draw.rect(surface, (120, 120, 120), up_elevator_rect)
            pygame.draw.rect(surface, (80, 80, 80), up_elevator_rect, 2)  # Frame
            # Up arrow indicator
            arrow_y = floor_y - building.floor_height // 2 - camera_y
            pygame.draw.polygon(surface, (255, 200, 0), [
                (up_elevator_x, arrow_y - 8),
                (up_elevator_x - 6, arrow_y),
                (up_elevator_x + 6, arrow_y)
            ])
            # Button
            pygame.draw.circle(surface, (255, 200, 0), (up_elevator_x, floor_y - 20 - camera_y), 5)
            # Floor number
            floor_text = FONT_SMALL.render(f"F{self.player_current_floor}", True, (255, 255, 255))
            surface.blit(floor_text, (up_elevator_x - 10, floor_y - building.floor_height - camera_y - 20))
        
        # Down elevator door (only visible in hall, not in apartment)
        if not self.player_in_apartment and self.player_current_floor > 0:
            down_elevator_x = floor['elevator_down_x'] - camera_x
            down_elevator_rect = pygame.Rect(down_elevator_x - 15, floor_y - building.floor_height - camera_y, 30, building.floor_height)
            pygame.draw.rect(surface, (120, 120, 120), down_elevator_rect)
            pygame.draw.rect(surface, (80, 80, 80), down_elevator_rect, 2)  # Frame
            # Down arrow indicator
            arrow_y = floor_y - building.floor_height // 2 - camera_y
            pygame.draw.polygon(surface, (255, 200, 0), [
                (down_elevator_x, arrow_y + 8),
                (down_elevator_x - 6, arrow_y),
                (down_elevator_x + 6, arrow_y)
            ])
            # Button
            pygame.draw.circle(surface, (255, 200, 0), (down_elevator_x, floor_y - 20 - camera_y), 5)
            # Floor number
            floor_text = FONT_SMALL.render(f"F{self.player_current_floor}", True, (255, 255, 255))
            surface.blit(floor_text, (down_elevator_x - 10, floor_y - building.floor_height - camera_y - 20))
        
        # Exit elevator (double down arrow) - only on ground floor, only visible in hall
        if not self.player_in_apartment and self.player_current_floor == 0:
            exit_elevator_x = floor['elevator_exit_x'] - camera_x
            exit_elevator_rect = pygame.Rect(exit_elevator_x - 15, floor_y - building.floor_height - camera_y, 30, building.floor_height)
            pygame.draw.rect(surface, (120, 120, 120), exit_elevator_rect)
            pygame.draw.rect(surface, (80, 80, 80), exit_elevator_rect, 2)  # Frame
            # Double down arrow indicator
            arrow_y = floor_y - building.floor_height // 2 - camera_y
            # First arrow
            pygame.draw.polygon(surface, (255, 100, 100), [
                (exit_elevator_x, arrow_y + 8),
                (exit_elevator_x - 6, arrow_y),
                (exit_elevator_x + 6, arrow_y)
            ])
            # Second arrow (below first)
            pygame.draw.polygon(surface, (255, 100, 100), [
                (exit_elevator_x, arrow_y + 16),
                (exit_elevator_x - 6, arrow_y + 8),
                (exit_elevator_x + 6, arrow_y + 8)
            ])
            # Button
            pygame.draw.circle(surface, (255, 100, 100), (exit_elevator_x, floor_y - 20 - camera_y), 5)
            # Floor number
            floor_text = FONT_SMALL.render(f"F{self.player_current_floor}", True, (255, 255, 255))
            surface.blit(floor_text, (exit_elevator_x - 10, floor_y - building.floor_height - camera_y - 20))
        
        # Draw background assets (decorative items) - only show in halls, not in apartments
        if not self.player_in_apartment:
            for asset in floor['background_assets']:
                asset_x = asset['x'] - camera_x
                asset_y = asset['y'] - camera_y
                if -50 <= asset_x < WIDTH + 50:
                    if asset['type'] == 'chair':
                        # Draw a simple chair
                        chair_base_y = asset_y - 15
                        # Chair seat
                        pygame.draw.rect(surface, (139, 90, 43), 
                                       (asset_x - 12, chair_base_y, 24, 8))
                        # Chair back
                        pygame.draw.rect(surface, (139, 90, 43), 
                                       (asset_x - 12, chair_base_y - 20, 24, 20))
                        # Chair legs
                        pygame.draw.line(surface, (100, 70, 30), 
                                       (asset_x - 10, chair_base_y + 8),
                                       (asset_x - 10, asset_y), 2)
                        pygame.draw.line(surface, (100, 70, 30), 
                                       (asset_x + 10, chair_base_y + 8),
                                       (asset_x + 10, asset_y), 2)
                    elif asset['type'] == 'plant':
                        # Draw a potted plant
                        pot_y = asset_y - 12
                        # Pot
                        pygame.draw.rect(surface, (80, 60, 40), 
                                       (asset_x - 8, pot_y, 16, 12))
                        # Plant leaves (simple circles)
                        pygame.draw.circle(surface, (34, 139, 34), (asset_x, pot_y - 5), 10)
                        pygame.draw.circle(surface, (50, 150, 50), (asset_x - 5, pot_y - 8), 8)
                        pygame.draw.circle(surface, (50, 150, 50), (asset_x + 5, pot_y - 8), 8)
                    elif asset['type'] == 'tv':
                        # Draw a TV hanging on the wall
                        tv_y = asset_y - 20
                        # TV screen (hanging on wall)
                        pygame.draw.rect(surface, (20, 20, 20), 
                                       (asset_x - 14, tv_y, 28, 18))
                        # Screen glow
                        pygame.draw.rect(surface, (100, 150, 200), 
                                       (asset_x - 12, tv_y + 2, 24, 14))
                        # TV frame
                        pygame.draw.rect(surface, (40, 40, 40), 
                                       (asset_x - 14, tv_y, 28, 18), 2)
                        # Wall mount/bracket
                        pygame.draw.rect(surface, (60, 60, 60), 
                                       (asset_x - 16, tv_y - 3, 32, 3))
                        # Mounting screws
                        pygame.draw.circle(surface, (100, 100, 100), (asset_x - 12, tv_y - 1), 2)
                        pygame.draw.circle(surface, (100, 100, 100), (asset_x + 12, tv_y - 1), 2)
                    elif asset['type'] == 'fire_extinguisher':
                        # Fire extinguisher cabinet on wall
                        cabinet_y = asset_y - 25
                        # Cabinet body
                        pygame.draw.rect(surface, (180, 50, 50), 
                                       (asset_x - 8, cabinet_y, 16, 25))
                        # Glass front
                        pygame.draw.rect(surface, (200, 220, 255, 150), 
                                       (asset_x - 6, cabinet_y + 2, 12, 20))
                        # Handle
                        pygame.draw.rect(surface, (60, 60, 60), 
                                       (asset_x - 10, cabinet_y + 8, 20, 4))
                        # Label text area
                        pygame.draw.rect(surface, (255, 255, 255), 
                                       (asset_x - 7, cabinet_y + 5, 14, 3))
                    elif asset['type'] == 'mailbox':
                        # Mailbox on wall
                        box_y = asset_y - 15
                        # Mailbox body
                        pygame.draw.rect(surface, (70, 70, 80), 
                                       (asset_x - 10, box_y, 20, 15))
                        # Mail slot
                        pygame.draw.rect(surface, (20, 20, 25), 
                                       (asset_x - 8, box_y + 3, 16, 8))
                        # Door handle
                        pygame.draw.circle(surface, (100, 100, 100), 
                                         (asset_x + 8, box_y + 9), 2)
                    elif asset['type'] == 'door_buzzer':
                        # Door buzzer/intercom on wall
                        buzzer_y = asset_y - 12
                        # Main panel
                        pygame.draw.rect(surface, (50, 50, 60), 
                                       (asset_x - 10, buzzer_y, 20, 15))
                        # Speaker grill
                        for i in range(3):
                            pygame.draw.line(surface, (80, 80, 90), 
                                           (asset_x - 8, buzzer_y + 5 + i * 2),
                                           (asset_x + 8, buzzer_y + 5 + i * 2), 1)
                        # Buttons
                        pygame.draw.circle(surface, (150, 150, 150), 
                                         (asset_x - 4, buzzer_y + 11), 3)
                        pygame.draw.circle(surface, (150, 150, 150), 
                                         (asset_x + 4, buzzer_y + 11), 3)
                    elif asset['type'] == 'security_camera':
                        # Security camera on wall/ceiling
                        cam_y = asset_y - 18
                        # Camera body
                        pygame.draw.circle(surface, (40, 40, 45), (asset_x, cam_y), 8)
                        # Lens
                        pygame.draw.circle(surface, (20, 20, 30), (asset_x, cam_y), 5)
                        pygame.draw.circle(surface, (100, 100, 120), (asset_x, cam_y), 3)
                        # Mount bracket
                        pygame.draw.rect(surface, (60, 60, 65), 
                                       (asset_x - 10, cam_y - 12, 20, 4))
                        # LED indicator
                        pygame.draw.circle(surface, (255, 0, 0), 
                                         (asset_x + 6, cam_y - 2), 2)
                    elif asset['type'] == 'vending_machine':
                        # Vending machine on floor (much bigger - 50px wide, 80px tall)
                        machine_y = asset_y - 80  # Much taller machine
                        # Machine body (bigger)
                        pygame.draw.rect(surface, (60, 80, 100), 
                                       (asset_x - 25, machine_y, 50, 80))
                        # Glass front
                        pygame.draw.rect(surface, (150, 180, 200, 120), 
                                       (asset_x - 23, machine_y + 3, 46, 70))
                        # Product slots (grid) - more slots
                        for row in range(5):
                            for col in range(2):
                                slot_x = asset_x - 20 + col * 18
                                slot_y = machine_y + 10 + row * 13
                                pygame.draw.rect(surface, (100, 120, 140), 
                                               (slot_x, slot_y, 14, 12), 1)
                                # Sometimes show healing potion in slot
                                if hasattr(asset, 'has_potion') and asset.get('has_potion', False) and row == 0 and col == 0:
                                    pygame.draw.circle(surface, (255, 100, 100), (slot_x + 7, slot_y + 6), 4)
                        # Coin slot
                        pygame.draw.circle(surface, (80, 80, 80), 
                                         (asset_x, machine_y + 75), 4)
                        # Selection buttons
                        pygame.draw.circle(surface, (200, 200, 200), 
                                         (asset_x - 15, machine_y + 75), 3)
                        pygame.draw.circle(surface, (200, 200, 200), 
                                         (asset_x + 15, machine_y + 75), 3)
                    elif asset['type'] == 'trash_bin':
                        # Trash bin on floor
                        bin_y = asset_y - 20
                        # Bin body
                        pygame.draw.rect(surface, (50, 50, 55), 
                                       (asset_x - 8, bin_y, 16, 20))
                        # Lid
                        pygame.draw.ellipse(surface, (60, 60, 65), 
                                          (asset_x - 8, bin_y - 3, 16, 6))
                        # Recycling symbol area (colored section)
                        pygame.draw.rect(surface, (0, 120, 0), 
                                       (asset_x - 6, bin_y + 2, 12, 16))
                        # Handles
                        pygame.draw.arc(surface, (80, 80, 80), 
                                      (asset_x - 10, bin_y + 5, 8, 10), 0, 3.14, 2)
                        pygame.draw.arc(surface, (80, 80, 80), 
                                      (asset_x + 2, bin_y + 5, 8, 10), 0, 3.14, 2)
                    elif asset['type'] == 'bulletin_board':
                        # Bulletin board on wall
                        board_y = asset_y - 25
                        # Board frame
                        pygame.draw.rect(surface, (139, 90, 43), 
                                       (asset_x - 15, board_y, 30, 25))
                        # Cork board surface
                        pygame.draw.rect(surface, (139, 110, 80), 
                                       (asset_x - 13, board_y + 2, 26, 21))
                        # Notices/papers (random)
                        pygame.draw.rect(surface, (255, 255, 255), 
                                       (asset_x - 10, board_y + 5, 8, 6))
                        pygame.draw.rect(surface, (255, 255, 255), 
                                       (asset_x + 2, board_y + 8, 8, 6))
                        pygame.draw.rect(surface, (255, 255, 200), 
                                       (asset_x - 8, board_y + 15, 10, 5))
                        # Push pins
                        pygame.draw.circle(surface, (200, 50, 50), 
                                         (asset_x - 7, board_y + 7), 1)
                        pygame.draw.circle(surface, (200, 50, 50), 
                                         (asset_x + 5, board_y + 11), 1)
                        pygame.draw.circle(surface, (200, 50, 50), 
                                         (asset_x - 5, board_y + 17), 1)
                    elif asset['type'] == 'elevator_panel':
                        # Elevator control panel on wall
                        panel_y = asset_y - 20
                        # Panel body
                        pygame.draw.rect(surface, (40, 40, 50), 
                                       (asset_x - 8, panel_y, 16, 20))
                        # Buttons grid (4x4)
                        for row in range(3):
                            for col in range(2):
                                btn_x = asset_x - 6 + col * 6
                                btn_y = panel_y + 3 + row * 5
                                pygame.draw.circle(surface, (100, 150, 200), 
                                                 (btn_x, btn_y), 2)
                                # Button glow
                                pygame.draw.circle(surface, (150, 200, 255), 
                                                 (btn_x, btn_y), 1)
                        # Up/Down arrows
                        pygame.draw.polygon(surface, (200, 200, 0), [
                            (asset_x - 6, panel_y + 18),
                            (asset_x - 2, panel_y + 14),
                            (asset_x + 2, panel_y + 14)
                        ])
                        pygame.draw.polygon(surface, (200, 200, 0), [
                            (asset_x + 6, panel_y + 18),
                            (asset_x + 2, panel_y + 14),
                            (asset_x - 2, panel_y + 14)
                        ])
                    elif asset['type'] == 'emergency_exit_sign':
                        # Emergency exit sign on wall/ceiling
                        sign_y = asset_y - 12
                        # Sign box
                        pygame.draw.rect(surface, (200, 50, 50), 
                                       (asset_x - 12, sign_y, 24, 12))
                        # Exit text area (white)
                        pygame.draw.rect(surface, (255, 255, 255), 
                                       (asset_x - 10, sign_y + 2, 20, 6))
                        # Arrow
                        pygame.draw.polygon(surface, (255, 255, 0), [
                            (asset_x + 8, sign_y + 5),
                            (asset_x + 6, sign_y + 3),
                            (asset_x + 6, sign_y + 7)
                        ])
                        # Glow effect
                        glow_surf = pygame.Surface((26, 14), pygame.SRCALPHA)
                        pygame.draw.rect(glow_surf, (255, 150, 150, 60), (0, 0, 26, 14))
                        surface.blit(glow_surf, (asset_x - 13, sign_y - 1))
                    elif asset['type'] == 'utility_panel':
                        # Utility panel/breaker box on wall
                        panel_y = asset_y - 18
                        # Panel box
                        pygame.draw.rect(surface, (30, 30, 35), 
                                       (asset_x - 10, panel_y, 20, 18))
                        # Door
                        pygame.draw.rect(surface, (50, 50, 55), 
                                       (asset_x - 9, panel_y + 1, 18, 16))
                        # Hinges
                        pygame.draw.circle(surface, (80, 80, 80), 
                                         (asset_x - 8, panel_y + 4), 1)
                        pygame.draw.circle(surface, (80, 80, 80), 
                                         (asset_x - 8, panel_y + 14), 1)
                        # Breaker switches (rows)
                        for i in range(4):
                            switch_x = asset_x - 6 + (i % 2) * 6
                            switch_y = panel_y + 4 + (i // 2) * 5
                            pygame.draw.rect(surface, (200, 200, 200), 
                                           (switch_x - 2, switch_y, 4, 3))
                            # Switch indicator
                            pygame.draw.circle(surface, (0, 200, 0), 
                                             (switch_x, switch_y + 1), 1)
        
        # Draw apartment door (visible in both hall and apartment)
        apartment_door_x = floor['apartment_door_x'] - camera_x
        apartment_door_y = floor_y - camera_y
        if -50 <= apartment_door_x < WIDTH + 50:
            if self.player_in_apartment:
                # In apartment - show door back to hall (on left side)
                door_rect = pygame.Rect(apartment_door_x - 20, apartment_door_y - building.floor_height, 40, building.floor_height)
                pygame.draw.rect(surface, (100, 80, 60), door_rect)  # Brown door
                pygame.draw.rect(surface, (60, 40, 20), door_rect, 2)  # Frame
                # Door handle
                pygame.draw.circle(surface, (200, 200, 200), (apartment_door_x - 10, apartment_door_y - building.floor_height // 2), 3)
            else:
                # In hall - show door to apartment (on right side)
                door_rect = pygame.Rect(apartment_door_x - 20, apartment_door_y - building.floor_height, 40, building.floor_height)
                pygame.draw.rect(surface, (100, 80, 60), door_rect)  # Brown door
                pygame.draw.rect(surface, (60, 40, 20), door_rect, 2)  # Frame
                # Door handle
                pygame.draw.circle(surface, (200, 200, 200), (apartment_door_x + 10, apartment_door_y - building.floor_height // 2), 3)
        
        # Draw lootable containers (only in apartments)
        if self.player_in_apartment:
            for container in floor['containers']:
                container_x = container['x'] - camera_x
                container_y = container['y'] - camera_y
                if -50 <= container_x < WIDTH + 50:
                    if container['type'] == 'chest':
                        # Draw a chest
                        chest_y = container_y - 20
                        # Chest base
                        pygame.draw.rect(surface, (139, 90, 43), 
                                       (container_x - 15, chest_y, 30, 15))
                        # Chest lid (slightly open if looted)
                        lid_offset = 2 if container['looted'] else 0
                        pygame.draw.rect(surface, (120, 80, 40), 
                                       (container_x - 15, chest_y - 5 + lid_offset, 30, 5))
                        # Chest lock/handle
                        if not container['looted']:
                            pygame.draw.circle(surface, (200, 200, 200), 
                                             (container_x, chest_y + 5), 3)
                        # Glow if has item
                        if container['item'] and not container['looted']:
                            glow_surf = pygame.Surface((35, 25), pygame.SRCALPHA)
                            pygame.draw.circle(glow_surf, (255, 200, 0, 100), (17, 12), 15)
                            surface.blit(glow_surf, (container_x - 17, chest_y - 5))
                    elif container['type'] == 'dresser':
                        # Draw a dresser
                        dresser_y = container_y - 25
                        # Dresser body
                        pygame.draw.rect(surface, (139, 90, 43), 
                                       (container_x - 18, dresser_y, 36, 25))
                        # Drawers
                        pygame.draw.line(surface, (100, 70, 30), 
                                       (container_x - 18, dresser_y + 8),
                                       (container_x + 18, dresser_y + 8), 2)
                        pygame.draw.line(surface, (100, 70, 30), 
                                       (container_x - 18, dresser_y + 16),
                                       (container_x + 18, dresser_y + 16), 2)
                        # Drawer handles
                        if not container['looted']:
                            pygame.draw.circle(surface, (200, 200, 200), 
                                             (container_x - 10, dresser_y + 4), 2)
                            pygame.draw.circle(surface, (200, 200, 200), 
                                             (container_x + 10, dresser_y + 4), 2)
                            pygame.draw.circle(surface, (200, 200, 200), 
                                             (container_x - 10, dresser_y + 12), 2)
                            pygame.draw.circle(surface, (200, 200, 200), 
                                             (container_x + 10, dresser_y + 12), 2)
                        # Glow if has item
                        if container['item'] and not container['looted']:
                            glow_surf = pygame.Surface((40, 30), pygame.SRCALPHA)
                            pygame.draw.circle(glow_surf, (255, 200, 0, 100), (20, 15), 18)
                            surface.blit(glow_surf, (container_x - 20, dresser_y - 5))
                    elif container['type'] == 'wardrobe':
                        # Draw a wardrobe
                        wardrobe_y = container_y - 35
                        # Wardrobe body
                        pygame.draw.rect(surface, (139, 90, 43), 
                                       (container_x - 12, wardrobe_y, 24, 35))
                        # Door
                        door_color = (120, 80, 40) if container['looted'] else (139, 90, 43)
                        pygame.draw.rect(surface, door_color, 
                                       (container_x - 12, wardrobe_y, 12, 35))
                        # Door handle
                        if not container['looted']:
                            pygame.draw.circle(surface, (200, 200, 200), 
                                             (container_x - 3, wardrobe_y + 17), 2)
                        # Glow if has item
                        if container['item'] and not container['looted']:
                            glow_surf = pygame.Surface((30, 40), pygame.SRCALPHA)
                            pygame.draw.circle(glow_surf, (255, 200, 0, 100), (15, 20), 18)
                            surface.blit(glow_surf, (container_x - 15, wardrobe_y - 5))
        
        # Draw apartment furniture (only in apartments)
        if self.player_in_apartment:
            for furniture in floor.get('apartment_assets', []):
                furniture_x = furniture['x'] - camera_x
                furniture_y = furniture['y'] - camera_y
                if -50 <= furniture_x < WIDTH + 50:
                    if furniture['type'] == 'bed_single':
                        # Single bed
                        bed_y = furniture_y - 15
                        # Mattress
                        pygame.draw.rect(surface, (200, 200, 220), (furniture_x - 25, bed_y, 50, 20))
                        # Pillow
                        pygame.draw.ellipse(surface, (255, 255, 255), (furniture_x - 20, bed_y - 3, 15, 8))
                        # Bed frame
                        pygame.draw.rect(surface, (139, 90, 43), (furniture_x - 25, bed_y + 20, 50, 5))
                    elif furniture['type'] == 'bed_double':
                        # Double bed
                        bed_y = furniture_y - 15
                        # Mattress
                        pygame.draw.rect(surface, (200, 200, 220), (furniture_x - 35, bed_y, 70, 20))
                        # Pillows
                        pygame.draw.ellipse(surface, (255, 255, 255), (furniture_x - 30, bed_y - 3, 15, 8))
                        pygame.draw.ellipse(surface, (255, 255, 255), (furniture_x + 15, bed_y - 3, 15, 8))
                        # Bed frame
                        pygame.draw.rect(surface, (139, 90, 43), (furniture_x - 35, bed_y + 20, 70, 5))
                    elif furniture['type'] == 'dresser':
                        # Dresser
                        dresser_y = furniture_y - 30
                        pygame.draw.rect(surface, (139, 90, 43), (furniture_x - 15, dresser_y, 30, 30))
                        # Drawer lines
                        pygame.draw.line(surface, (100, 70, 30), (furniture_x - 15, dresser_y + 10), (furniture_x + 15, dresser_y + 10), 2)
                        pygame.draw.line(surface, (100, 70, 30), (furniture_x - 15, dresser_y + 20), (furniture_x + 15, dresser_y + 20), 2)
                        # Handles
                        pygame.draw.circle(surface, (200, 200, 200), (furniture_x - 8, dresser_y + 5), 2)
                        pygame.draw.circle(surface, (200, 200, 200), (furniture_x + 8, dresser_y + 5), 2)
                    elif furniture['type'] == 'refrigerator':
                        # Refrigerator (bigger)
                        fridge_y = furniture_y - 70  # Much taller
                        # Body (bigger - 28px wide, 70px tall)
                        pygame.draw.rect(surface, (220, 220, 220), (furniture_x - 14, fridge_y, 28, 70))
                        # Door
                        pygame.draw.rect(surface, (200, 200, 200), (furniture_x - 14, fridge_y, 14, 70))
                        # Handle
                        pygame.draw.circle(surface, (100, 100, 100), (furniture_x + 10, fridge_y + 35), 2)
                        # Freezer section (top)
                        pygame.draw.line(surface, (180, 180, 180), (furniture_x - 14, fridge_y + 20), (furniture_x + 14, fridge_y + 20), 2)
                    elif furniture['type'] == 'television':
                        # Television (on wall or stand)
                        tv_y = furniture_y - 25
                        # TV screen
                        pygame.draw.rect(surface, (20, 20, 20), (furniture_x - 18, tv_y, 36, 22))
                        # Screen glow
                        pygame.draw.rect(surface, (100, 150, 200), (furniture_x - 16, tv_y + 2, 32, 18))
                        # TV frame
                        pygame.draw.rect(surface, (40, 40, 40), (furniture_x - 18, tv_y, 36, 22), 2)
                        # Stand/base
                        pygame.draw.rect(surface, (60, 60, 60), (furniture_x - 12, tv_y + 22, 24, 3))
        
        # Draw enemies on floor (they will be drawn separately in main loop, but we can add a marker)
        # Actually, enemies are drawn in main loop, so we don't need to draw them here
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
        if merchant.merchant_hostile or merchant.is_dead() or not merchant.is_merchant:
            return
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
        if (not self.merchant or not self.merchant.is_merchant or
                self.merchant.merchant_hostile or self.merchant.is_dead()):
            self.close()
            return
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.close()
                elif e.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_a,
                               pygame.K_RIGHT, pygame.K_d):
                    prev_focus = self.focus
                    if e.key in (pygame.K_RIGHT, pygame.K_d):
                        self.focus = "inv"
                    elif e.key in (pygame.K_LEFT, pygame.K_a):
                        self.focus = "shop"
                    else:
                        self.focus = "inv" if self.focus == "shop" else "shop"
                    if self.focus != prev_focus:
                        self.sel_index = 0
                elif e.key in (pygame.K_UP, pygame.K_w):
                    self.sel_index = max(0, self.sel_index - 1)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    max_len = len(self.current_list()) - 1
                    self.sel_index = min(max_len, self.sel_index + 1)
                elif e.key == pygame.K_RETURN:
                    if self.focus == "shop":
                        self.buy_selected()
                    else:
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
            # Stack potions if it's a potion
            if item.is_potion:
                # Check if player already has this potion type
                found = False
                for inv_item in self.player.inventory:
                    if inv_item.is_potion and inv_item.name == item.name:
                        inv_item.count += item.count
                        found = True
                        break
                if not found:
                    self.player.inventory.append(item)
            else:
                self.player.inventory.append(item)
            del lst[self.sel_index]
            self.sel_index = max(0, self.sel_index - 1)

    def sell_selected(self):
        lst = self.player.inventory
        if not lst or self.sel_index >= len(lst):
            return
        item = lst[self.sel_index]
        if self.merchant.money >= item.price:
            # Check if player is selling near a dog (dog selling detection)
            # This would need city reference - for now, we'll handle it in quest updates
            # Unequip if selling equipped item
            if self.player.weapon is item:
                self.player.weapon = None
            elif self.player.armor_item is item:
                self.player.armor_item = None
            
            self.merchant.money -= item.price
            self.player.money += item.price
            self.merchant.inventory.append(item)
            del lst[self.sel_index]
            self.sel_index = max(0, self.sel_index - 1)

    def draw(self, surface):
        if not self.active:
            return
        if (not self.merchant or not self.merchant.is_merchant or
                self.merchant.merchant_hostile or self.merchant.is_dead()):
            self.close()
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
                item_name = it.name
                if it.is_potion:
                    item_name += f" (x{it.count})"
                name = FONT_SMALL.render(
                    f"{item_name} [{it.price}] ({it.desc()})", True, col)
                surface.blit(name, (ox, y))

        draw_list(self.merchant.inventory, px + 20, py + 100,
                  self.sel_index if self.focus == "shop" else -1)
        draw_list(self.player.inventory, px + (WIDTH // 2) - 40,
                  py + 100, self.sel_index if self.focus == "inv" else -1)

        help1 = FONT_SMALL.render("W/S or Up/Down move, A/D or Tab swap column, Enter buy/sell, Esc exit",
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

    def open(self, player, city=None):
        self.active = True
        self.player = player
        self.city = city  # Store city reference for quests
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
    
    def set_city(self, city):
        """Set the city reference for quest display."""
        self.city = city

    def handle_key(self, e):
        if not self.active:
            return

        if e.key == pygame.K_ESCAPE:
            self.close()
            return

        if e.key in (pygame.K_UP, pygame.K_w):
            self.selected_index = max(0, self.selected_index - 1)

        elif e.key in (pygame.K_DOWN, pygame.K_s):
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
        if item.is_potion:
            # Equip potion to Q slot
            self.player.potion_slot = item
        elif item.dmg > 0:
            # Toggle weapon: if already equipped, unequip it
            if self.player.weapon is item:
                self.player.weapon = None
            else:
                self.player.weapon = item
        elif item.armor > 0:
            # Toggle armor: if already equipped, unequip it
            if self.player.armor_item is item:
                self.player.armor_item = None
            else:
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

        # Player stats display (like in shop)
        if self.player:
            stats_y = panel.y + 35
            # Calculate additional stats
            attack_delay = self.player.attack_delay()
            knockback = self.player.total_knockback()
            # Show all stats similar to shop format
            stats_parts = [
                f"HP: {self.player.hp}/{self.player.hp_max}",
                f"Dmg: {self.player.total_damage()}",
                f"Arm: {self.player.total_armor()}",
                f"AS: {attack_delay}f",
                f"KB: {knockback:.1f}" if knockback > 0 else "",
                f"Money: {self.player.money}"
            ]
            stats_text = " | ".join([s for s in stats_parts if s])  # Filter out empty strings
            stats_display = FONT_SMALL.render(stats_text, True, (200, 255, 200))
            surface.blit(stats_display, (panel.x + 30, stats_y))

        # Show active quests
        y = panel.y + 60
        if hasattr(self, 'city') and self.city and self.city.quests:
            quest_title = FONT_SMALL.render("ACTIVE QUESTS:", True, (255, 200, 100))
            surface.blit(quest_title, (panel.x + 30, y))
            y += 22
            for quest in self.city.quests:
                if quest.status == "active":
                    status_color = (150, 255, 150) if quest.status == "completed" else (255, 150, 150) if quest.status == "failed" else (200, 200, 255)
                    quest_text = FONT_SMALL.render(f"• {quest.description}", True, status_color)
                    surface.blit(quest_text, (panel.x + 40, y))
                    y += 20
            y += 10  # Spacing before inventory

        # Inventory items
        for i, entry in enumerate(self.entries):
            is_sel = (i == self.selected_index)
            prefix = "* " if is_sel else "  "
            if isinstance(entry, Item):
                label = entry.name
                if entry.is_potion:
                    label += f" (x{entry.count})"
                    if entry is self.player.potion_slot:
                        label += " [Q]"
                # Show full stats like in shop (Dmg, Arm, AS, KB)
                stats_desc = entry.desc()
                if stats_desc and stats_desc != "No bonus":
                    label += f" ({stats_desc})"
                if entry is self.player.weapon or entry is self.player.armor_item:
                    label += " [Equipped]"
            else:
                label = entry

            col = (255, 255, 180) if is_sel else (210, 210, 210)
            txt = FONT_SMALL.render(prefix + label, True, col)
            surface.blit(txt, (panel.x + 30, y))
            y += 26

        # Abbreviation key
        abbrev_y = panel.y + panel.height - 80
        abbrev_text = FONT_SMALL.render(
            "Abbreviations: Dmg=Damage, Arm=Armor, AS=Attack Speed, KB=Knockback",
            True, (180, 180, 255)
        )
        surface.blit(abbrev_text, (panel.x + 30, abbrev_y))
        
        help_txt = FONT_SMALL.render("W/S or Up/Down select, Enter equip/use, Esc close", True, (200, 200, 200))
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

        info = FONT_SMALL.render("W/S or Up/Down to choose, Enter to confirm, Esc to quit", True, (180, 180, 180))
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
                elif e.key in (pygame.K_UP, pygame.K_w):
                    index = (index - 1) % len(options)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
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
                 atk_speed_bonus=0.35, knockback=3, price=0,
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
        if u.is_merchant and not u.is_dead() and not getattr(u, "merchant_hostile", False):
            if pr.colliderect(u.rect.inflate(60, 10)):
                return u
    return None


def handle_combat_between(attacker, defender):
    hb = attacker.get_attack_hitbox()
    if hb and not attacker.attack_has_hit and hb.colliderect(defender.rect):
        # Apply damage
        defender.take_hit(attacker.total_damage())
        attacker.attack_has_hit = True
        
        # Apply knockback based on attacker's weapon
        knockback = attacker.total_knockback()
        if knockback > 0:
            # Determine knockback direction (from attacker to defender)
            direction = 1 if attacker.x < defender.x else -1
            # Apply knockback with timer - reduced by 70% (30% of original)
            defender.knockback_vx = knockback * direction * 2.4  # 30% of 8.0 = 2.4x multiplier
            defender.knockback_timer = 20  # Knockback lasts 20 frames
        
        if defender.was_merchant and not defender.merchant_hostile:
            defender.become_hostile(attacker)
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
                        pause_menu.open(player, city)

                elif pause_menu.active:
                    pause_menu.handle_key(e)

                elif shop_ui.active:
                    shop_ui.handle_input([e])

                else:
                    if e.key == pygame.K_q:
                        # Use potion from Q slot - can't use when dead
                        if not player.is_dead() and player.potion_slot and player.potion_slot.count > 0:
                            # Heal player
                            heal_amount = player.potion_slot.heal_amount
                            player.hp = min(player.hp_max, player.hp + heal_amount)
                            # Consume one potion
                            player.potion_slot.count -= 1
                            # Remove if count reaches 0
                            if player.potion_slot.count <= 0:
                                # Remove from inventory
                                if player.potion_slot in player.inventory:
                                    player.inventory.remove(player.potion_slot)
                                player.potion_slot = None
                    elif e.key == pygame.K_RETURN:
                        # Check building interactions first
                        if city.player_inside_building:
                            # Check apartment door first (Enter key can also interact with doors)
                            if city.check_apartment_door(player):
                                if city.player_in_apartment:
                                    city.exit_apartment(player)
                                else:
                                    city.enter_apartment(player)
                            # Check container looting (only if not at door)
                            else:
                                container = city.check_container_loot(player)
                                if container:
                                    city.loot_container(player, container)
                                else:
                                    # Attack
                                    player.start_attack("swing")
                        else:
                            # Check building entry
                            building = city.check_building_entry(player)
                            if building:
                                city.enter_building(player, building)
                            else:
                                # Attack
                                player.start_attack("swing")
                    elif e.key == pygame.K_F1:
                        DEBUG_HITBOXES = not DEBUG_HITBOXES
                    elif e.key == pygame.K_e:
                        if city.player_inside_building:
                            # Check apartment door first
                            if city.check_apartment_door(player):
                                if city.player_in_apartment:
                                    city.exit_apartment(player)
                                else:
                                    city.enter_apartment(player)
                            else:
                                # Check elevator (E key triggers elevators)
                                elevator_dir = city.check_elevator(player)
                                if elevator_dir:
                                    city.use_elevator(player, elevator_dir)
                                else:
                                    # Check for completed quest NPC to claim reward
                                    npc, quest = city.check_nearby_completed_quest_npc(player)
                                    if npc and quest:
                                        city.claim_quest_reward(quest, player)
                        else:
                            # Check for NPC with quest
                            npc, quest = city.check_nearby_npc(player)
                            if npc and quest:
                                city.accept_quest(quest)
                            else:
                                # Check for merchant
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
            # Create floor platform if inside building
            building_bounds = city.get_building_bounds()
            if city.player_inside_building:
                building = city.player_inside_building
                floor = building.floors[city.player_current_floor]
                # Create temporary platform for floor
                floor_platform = Platform(building.x, floor['y'], building.width, 5)
                player_platforms = [floor_platform]
            else:
                player_platforms = city.platforms
            
            # Update player with building bounds for collision
            player.update_player(key_state, player_platforms, building_bounds)
            
            player.update_regen(dt)

            # ---- QUEST UPDATES ----
            city.update_quests(player)
            
            # ---- DOG UPDATES ----
            for dog in city.dogs:
                # Dog follows player once player gets close (within 100 pixels)
                dx = player.x - dog.x
                dy = player.y - dog.y
                dist = math.sqrt(dx*dx + dy*dy) if dx != 0 or dy != 0 else 0
                if dist < 100:  # Player is close - dog starts following
                    dog.follow_player = player
                    # Update dog's building/floor to match player's
                    if city.player_inside_building:
                        dog.inside_building = city.player_inside_building
                        dog.building_floor_num = city.player_current_floor
                    else:
                        dog.inside_building = None
                
                # Only update dog if it's following player
                if dog.follow_player:
                    if city.player_inside_building:
                        building = city.player_inside_building
                        floor = building.floors[city.player_current_floor]
                        floor_platform = Platform(building.x, floor['y'], building.width, 5)
                        building_bounds = city.get_building_bounds()
                        dog.update(player, [floor_platform], building_bounds)
                        # Update dog's floor to match player's
                        dog.building_floor_num = city.player_current_floor
                    else:
                        dog.update(player, city.platforms, None)
                        dog.inside_building = None
            
            # ---- ENEMY AI ----
            # Update enemies on current floor if inside building
            if city.player_inside_building:
                floor_enemies = city.get_current_floor_enemies()
                building_bounds = city.get_building_bounds()
                for u in floor_enemies:
                    if not u.is_dead():
                        # Skip NPCs - they have their own AI
                        if u.is_npc and not u.is_companion:
                            continue
                        # Companion NPCs follow player
                        if u.is_companion:
                            city.update_companion_npc(u, player, city.player_inside_building, city.player_current_floor)
                            continue
                        building = city.player_inside_building
                        floor = building.floors[city.player_current_floor]
                        floor_platform = Platform(building.x, floor['y'], building.width, 5)
                        u.update_enemy_ai(player, [floor_platform], building_bounds)
            else:
                # Update all enemies - check if they're in buildings
                for u in city.units:
                    if not u.is_dead():
                        # Skip NPCs - they have their own AI
                        if u.is_npc and not u.is_companion:
                            continue
                        # Companion NPCs follow player
                        if u.is_companion:
                            city.update_companion_npc(u, player, None, 0)
                            continue
                        # Check if enemy is inside a building
                        enemy_building_bounds = city.get_enemy_building_bounds(u)
                        if enemy_building_bounds:
                            # Enemy is in a building - use building floor platform
                            building = u.inside_building
                            floor = building.floors[u.building_floor_num]
                            floor_platform = Platform(building.x, floor['y'], building.width, 5)
                            u.update_enemy_ai(player, [floor_platform], enemy_building_bounds)
                        else:
                            # Enemy is outside - use ground platforms
                            u.update_enemy_ai(player, city.platforms, None)

            # ---- PROJECTILES ----
            update_projectiles(PROJECTILES, player, city.units)

            # ---- COMBAT ----
            if city.player_inside_building:
                # Only combat with enemies on current floor
                floor_enemies = city.get_current_floor_enemies()
                for u in floor_enemies:
                    if not u.is_dead() and not u.is_npc:  # Don't fight NPCs
                        handle_combat_between(player, u)
                        # NPCs don't attack player, but companions attack enemies
                        if not u.is_npc:
                            handle_combat_between(u, player)
            else:
                # Combat with all units
                for u in city.units:
                    if not u.is_dead() and not u.is_npc:  # Don't fight NPCs
                        handle_combat_between(player, u)
                        if not u.is_npc:
                            handle_combat_between(u, player)

            # ---- LOOT / CLEANUP ----
            for u in city.units:
                if u.is_dead():
                    if u.money > 0:
                        player.money += u.money
                        u.money = 0
                    # Chance to drop potion (for all enemies including merchants)
                    if random.random() < 0.15:  # 15% chance
                        settings = STAGE_SETTINGS.get(city.stage, STAGE_SETTINGS[4])
                        potion = city.generate_potion_for_stage(settings)
                        # Add potion to player inventory (stack if already have potions)
                        city.add_potion_to_inventory(player, potion)
            # Remove dead enemies, but keep dead merchants (they stay on ground)
            city.units = [u for u in city.units if not (u.is_dead() and not u.is_merchant)]

            # ---- CAMERA ----
            camera_x = max(0, min(int(player.x) - WIDTH // 2, WORLD_WIDTH - WIDTH))
            
            # Vertical camera when inside building
            if city.player_inside_building:
                building = city.player_inside_building
                floor = building.floors[city.player_current_floor]
                # Center camera on the floor
                floor_center_y = floor['y'] - building.floor_height // 2
                camera_y = floor_center_y - HEIGHT // 2
            else:
                camera_y = 0  # No vertical offset when outside

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
        city.draw_background(SCREEN, camera_x, camera_y)
        city.draw_static_level(SCREEN, camera_x, camera_y, player)

        # Draw enemies and NPCs
        if city.player_inside_building:
            # Draw enemies on current floor (always visible when inside)
            floor_enemies = city.get_current_floor_enemies()
            for u in floor_enemies:
                if not u.is_dead():
                    u.draw(SCREEN, camera_x, camera_y, debug=DEBUG_HITBOXES)
        else:
            # Draw units - only show enemies inside buildings if they're visible through windows
            for u in city.units:
                if not u.is_dead():
                    # If enemy is in a building, only draw if visible through window
                    if u.inside_building:
                        if city.is_enemy_visible_through_window(u, camera_x):
                            u.draw(SCREEN, camera_x, 0, debug=DEBUG_HITBOXES)
                    else:
                        # Enemy is outside, always visible
                        u.draw(SCREEN, camera_x, 0, debug=DEBUG_HITBOXES)
        
        # Draw NPC dialogue/quest text above NPCs when player is close
        for u in city.units:
            if u.is_npc and not u.is_dead():
                # Check distance to player
                dx = u.x - player.x
                dy = u.y - player.y
                dist_sq = dx*dx + dy*dy
                if dist_sq < 10000:  # Within 100 pixels
                    # Draw dialogue text above NPC
                    dialogue_text = getattr(u, 'dialogue', '')
                    if dialogue_text:
                        # Find quest for this NPC
                        quest_text = ""
                        for quest in city.quests:
                            if quest.npc == u:
                                if quest.status == "offered":
                                    quest_text = " [Press E to accept]"
                                elif quest.status == "active":
                                    quest_text = " [Quest Active]"
                                elif quest.status == "completed":
                                    quest_text = " [Completed]"
                                break
                        
                        # Draw text above NPC
                        text_y_offset = -40
                        if city.player_inside_building:
                            npc_screen_x = int(u.x - camera_x)
                            npc_screen_y = int(u.y - camera_y)
                        else:
                            npc_screen_x = int(u.x - camera_x)
                            npc_screen_y = int(u.y)
                        
                        # Draw dialogue
                        dialogue_surf = FONT_SMALL.render(dialogue_text, True, (255, 255, 200))
                        text_width = dialogue_surf.get_width()
                        # Background for text
                        bg_rect = pygame.Rect(npc_screen_x - text_width // 2 - 5, npc_screen_y + text_y_offset - 2, text_width + 10, 16)
                        pygame.draw.rect(SCREEN, (0, 0, 0, 180), bg_rect)
                        SCREEN.blit(dialogue_surf, (npc_screen_x - text_width // 2, npc_screen_y + text_y_offset))
                        
                        # Draw quest status if available
                        if quest_text:
                            quest_surf = FONT_SMALL.render(quest_text, True, (200, 255, 200))
                            quest_width = quest_surf.get_width()
                            quest_bg_rect = pygame.Rect(npc_screen_x - quest_width // 2 - 5, npc_screen_y + text_y_offset + 14, quest_width + 10, 16)
                            pygame.draw.rect(SCREEN, (0, 0, 0, 180), quest_bg_rect)
                            SCREEN.blit(quest_surf, (npc_screen_x - quest_width // 2, npc_screen_y + text_y_offset + 16))

        # Draw dogs
        for dog in city.dogs:
            if city.player_inside_building:
                # Only draw dog if on current floor
                if dog.inside_building == city.player_inside_building and dog.building_floor_num == city.player_current_floor:
                    dog.draw(SCREEN, camera_x, camera_y)
            else:
                # Draw dog if outside
                if not dog.inside_building:
                    dog.draw(SCREEN, camera_x, 0)
        
        # Draw projectiles after units so they appear above the level but below UI
        for proj in PROJECTILES:
            proj.draw(SCREEN, camera_x, camera_y)

        if not player.is_dead():
            player.draw(SCREEN, camera_x, camera_y, debug=DEBUG_HITBOXES)

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
        # Show Q potion slot
        if player.potion_slot:
            potion_text = f"Q: {player.potion_slot.name} (x{player.potion_slot.count})"
            SCREEN.blit(
                FONT_SMALL.render(potion_text, True, (200, 100, 255)),
                (10, hud_y + 60)
            )
        else:
            SCREEN.blit(
                FONT_SMALL.render("Q: No Potion", True, (150, 150, 150)),
                (10, hud_y + 60)
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
        
        # Draw pickup notifications at bottom
        notification_y = HEIGHT - 40
        for notif in city.pickup_notifications[:]:
            notif.timer -= 1
            if notif.timer <= 0:
                city.pickup_notifications.remove(notif)
                continue
            
            # Fade out in last 60 frames
            if notif.timer < 60:
                notif.alpha = int(255 * (notif.timer / 60))
            
            # Draw notification text
            text_surface = FONT_SMALL.render(notif.text, True, (255, 255, 200))
            text_surface.set_alpha(notif.alpha)
            text_x = WIDTH // 2 - text_surface.get_width() // 2
            SCREEN.blit(text_surface, (text_x, notification_y))
            notification_y -= 25  # Stack multiple notifications

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
