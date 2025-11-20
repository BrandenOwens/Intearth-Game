# constants.py

import pygame

# --- window / world ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 720
FPS = 60

WORLD_WIDTH = 4800  # long scrolling city

GROUND_HEIGHT = 40
GROUND_Y = WINDOW_HEIGHT - GROUND_HEIGHT

# --- colours ---
BG_COLOR = (10, 10, 20)
PLATFORM_COLOR = (70, 70, 70)

BUILDING_FACADE_COLOR = (70, 70, 70)
BUILDING_INTERIOR_COLOR = (40, 40, 40)
WINDOW_COLOR = (150, 200, 255)
DOOR_COLOR = (140, 90, 50)
STAIRS_COLOR = (180, 180, 80)

PLAYER_COLOR = (0, 0, 0)

# --- player movement ---
MOVE_SPEED = 4
JUMP_SPEED = -11
GRAVITY = 0.6
MAX_FALL_SPEED = 14

# --- building layout (large buildings, tall floors) ---
BUILDING_WIDTH = 450          # wider buildings
BUILDING_NUM_FLOORS = 5       # more floors
BUILDING_FLOOR_HEIGHT = 140   # tall floors

# keys
KEY_LEFT = pygame.K_a
KEY_RIGHT = pygame.K_d
KEY_JUMP = pygame.K_w
KEY_INTERACT = pygame.K_e
