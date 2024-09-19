# Eggzy - Code the Classics Volume 2
# Code by Andrew Gillett and Eben Upton
# Graphics by Dan Malone
# Music and sound effects by Allister Brimble
# https://github.com/raspberrypipress/Code-the-Classics-Vol2.git
# TODO BOOK URL

# Celeste - designing the dash | Rock Paper Shotgun https://www.rockpapershotgun.com/celeste-dash
# https://www.neoseeker.com/celeste/Celeste_Basic_Controls

import pygame, pgzero, pgzrun, sys, os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from enum import Enum
from random import randint

# On Windows, if the window is too big for the screen and you are using display scaling, you can uncomment
# the following two lines to fix the issue
# import ctypes
# ctypes.windll.user32.SetProcessDPIAware()

# Check Python version number. sys.version_info gives version as a tuple, e.g. if (3,7,2,'final',0) for version 3.7.2.
# Unlike many languages, Python can compare two tuples in the same way that you can compare numbers.
if sys.version_info < (3,6):
    print("This game requires at least version 3.6 of Python. Please download it from www.python.org")
    sys.exit()

# Check Pygame Zero version. This is a bit trickier because Pygame Zero only lets us get its version number as a string.
# So we have to split the string into a list, using '.' as the character to split on. We convert each element of the
# version number into an integer - but only if the string contains numbers and nothing else, because it's possible for
# a component of the version to contain letters as well as numbers (e.g. '2.0.dev0')
# This uses a Python feature called list comprehension
pgzero_version = [int(s) if s.isnumeric() else s for s in pgzero.__version__.split('.')]
if pgzero_version < [1,2]:
    print(f"This game requires at least version 1.2 of Pygame Zero. You have version {pgzero.__version__}. Please upgrade using the command 'pip3 install --upgrade pgzero'")
    sys.exit()

# Set up constants
WIDTH = 825
HEIGHT = 550
TITLE = "Eggzy"

LEVEL_SEQUENCE = ("starter1.tmx", "starter2.tmx", "starter3.tmx", "starter4.tmx",
                  "forest1.tmx", "forest2.tmx", "forest3.tmx", "forest4.tmx", "forest9.tmx",
                  "castle1.tmx", "castle2.tmx", "castle3.tmx", "castle4.tmx",
                  "castle5.tmx", "castle6.tmx", "castle7.tmx", "castle8.tmx",
                  "forest5.tmx", "forest6.tmx", "forest7.tmx", "forest8.tmx")

GRID_BLOCK_SIZE = 25
LEVEL_Y_BOUNDARY = -100

# Change to 1, 2 or 3 to start with enemies/more enemies and less bonus time for gems
INITIAL_LEVEL_CYCLE = 0

INITIAL_TIME_REMAINING = 15
INITIAL_PICKUP_TIME_BONUS = 2
STOMP_ENEMY_TIME_BONUS = 3

# Constants affecting player movement
COYOTE_TIME = 6
JUMP_VEL_Y = -10
WALL_JUMP_X_VEL = 8
WALL_JUMP_COYOTE_TIME = 15
CACHE_JUMP_INPUT_TIME = 5
PLAYER_WIDTH = 20   # Width of player for the purpose of collisions - slightly smaller than the bounds of the sprite
PLAYER_HEIGHT = 40  # For player head collision with ceilings

ANCHOR_CENTRE = ("center", "center")
ANCHOR_CENTRE_BOTTOM = ("center", "bottom")
ANCHOR_PLAYER = ("center", 60)                # Feet of player sprite are not at the bottom
ANCHOR_FLAME = ("center", 78)
ANCHOR_FLAME_DASH = ("center", 130)

class Biome(Enum):
    FOREST = 0
    CASTLE = 1

# There are eight types of enemy - four per biome. Some properties are the same between the forest/castle equivalents,
# some are different

ENEMY_SPRITE_NAMES = {Biome.CASTLE: ["robot0", "robot1", "robot2", "robot3"],
                      Biome.FOREST: ["fly", "mghost", "triffid", "bigbloom"]}

ENEMY_TYPES_FLYING = {Biome.CASTLE: [True, True, False, False], Biome.FOREST: [True, True, False, True]}

ENEMY_TYPES_WIDTH_OVERRIDES = {Biome.CASTLE: [30, 50, 48, 50], Biome.FOREST: [30, 50, 50, 50]}
ENEMY_TYPES_HEIGHT_OVERRIDES = {Biome.CASTLE: [40, 40, 60, 120], Biome.FOREST: [30, 65, 70, 90]}

ENEMY_TYPES_ANCHOR_POINTS = {Biome.CASTLE: [("center", 40),("center", 40),("center", 95),("center", "bottom")],
                             Biome.FOREST: [("center", 60),("center", "bottom"),("center", "bottom"),("center", "bottom")]}

ENEMY_TYPES_HEALTH = [1, 3, 1, 3]
ENEMY_TYPES_SPEED = [2, 1, 2, 1]

REPLAY_FILENAME = "eggzy-replays"
MAX_REPLAYS = 10

DEBUG_SHOW_PLAYER_COLLISION_RECT = False
DEBUG_SHOW_ENEMY_COLLISION_RECTS = False
DEBUG_SHOW_BLOCK_COLLISION_RECTS = False
DEBUG_SHOW_FRAME_NUMBER = False
DEBUG_MOVEMENT = False
DEBUG_SLOWMO = 1        # Set to 2 or higher to run in slow motion, useful for testing animations

# These symbols substitute for the controller button images when displaying text.
# The symbols representing these images must be ones that aren't actually used themselves, e.g. we don't use the
# percent sign in text
SPECIAL_FONT_SYMBOLS = {'xb_a':'%', 'xb_b':'#'}

# Create a version of SPECIAL_FONT_SYMBOLS where the keys and values are swapped
SPECIAL_FONT_SYMBOLS_INVERSE = dict((v,k) for k,v in SPECIAL_FONT_SYMBOLS.items())

def move_towards(n, target, speed):
    if n < target:
        return min(n + speed, target)
    else:
        return max(n - speed, target)

def sign(x):
    # Returns 1, 0 or -1 depending on whether number is positive, zero or negative
    if x == 0:
        return 0
    else:
        return -1 if x < 0 else 1

# ABC = abstract base class - a class which is only there to serve as a base class, not to be instantiated directly
class Controls(ABC):
    NUM_BUTTONS = 2

    def __init__(self):
        self.button_previously_down = [False for i in range(Controls.NUM_BUTTONS)]
        self.is_button_pressed = [False for i in range(Controls.NUM_BUTTONS)]

    def update(self):
        # Call each frame to update button status
        for button in range(Controls.NUM_BUTTONS):
            button_down = self.button_down(button)
            self.is_button_pressed[button] = button_down and not self.button_previously_down[button]
            self.button_previously_down[button] = button_down

    @abstractmethod
    def get_x(self):
        # Overridden by subclasses
        pass

    @abstractmethod
    def get_y(self):
        # Overridden by subclasses
        pass

    @abstractmethod
    def button_down(self, button):
        # Overridden by subclasses
        pass

    def button_pressed(self, button):
        return self.is_button_pressed[button]

    @abstractmethod
    def button_name(self, button):
        return "?"

class KeyboardControls(Controls):
    def get_x(self):
        if keyboard.left:
            return -1
        elif keyboard.right:
            return 1
        else:
            return 0

    def get_y(self):
        if keyboard.up:
            return -1
        elif keyboard.down:
            return 1
        else:
            return 0

    def button_down(self, button):
        if button == 0:
            return keyboard.space
        else:
            return keyboard.z

    def button_name(self, button):
        if button == "dash":
            return "Z"
        elif button == "jump":
            return "SPACE"
        else:
            return "?"

class JoystickControls(Controls):
    def __init__(self, joystick):
        super().__init__()
        self.joystick = joystick
        joystick.init() # Not necessary in Pygame 2.0.0 onwards

    def get_axis(self, axis_num):
        if self.joystick.get_numhats() > 0 and self.joystick.get_hat(0)[axis_num] != 0:
            # For some reason, dpad up/down are inverted when getting inputs from
            # an Xbox controller, so need to negate the value if axis_num is 1
            return self.joystick.get_hat(0)[axis_num] * (-1 if axis_num == 1 else 1)

        axis_value = self.joystick.get_axis(axis_num)
        if abs(axis_value) < 0.6:
            # Dead-zone
            return 0
        else:
            # digital movement
            return 1 if axis_value > 0 else -1

    def get_x(self):
        return self.get_axis(0)

    def get_y(self):
        return self.get_axis(1)

    def button_down(self, button):
        # Before checking button, check to make sure that the controller actually has enough buttons
        # There are some weird devices out there which could cause a crash if this check were not present
        if self.joystick.get_numbuttons() <= button:
            print("Warning: controller does not have enough buttons!")
            return False
        return self.joystick.get_button(button) != 0

    def button_name(self, button):
        if button == "dash":
            return SPECIAL_FONT_SYMBOLS["xb_b"]
        elif button == "jump":
            return SPECIAL_FONT_SYMBOLS["xb_a"]
        else:
            return "?"

# Class for gem pickups
class Gem(Actor):
    # This is a class variable, equivalent to what is known in other languages as a static variable
    # The variable belongs to the class as a whole rather than any one particular instance (object) of the class
    next_type = 1

    def __init__(self, pos):
        super().__init__("blank", pos, ANCHOR_CENTRE_BOTTOM)

        # Choose which type of gem we're going to be.
        self.type = Gem.next_type

        # Set the type of the next gem
        Gem.next_type += 1
        if Gem.next_type >= 5:
            Gem.next_type = 1

        self.collected = False

    def update(self):
        # Does the player exist, and are they colliding with us?
        if game.player is not None and game.player.collidepoint(self.center):
            game.gain_time(game.time_pickup_bonus, self.centerx, self.centery)
            game.play_sound("collect")
            self.collected = True  # Disappear

        anim_frame = str((game.timer // 6) % 4)
        self.image = f"gem{self.type}_{anim_frame}"

    @staticmethod
    def new_game():
        Gem.next_type = 1

# The door prevents the player from leaving a level until all gems have been collected
class Door(Actor):
    def __init__(self, pos, biome="castle", variant=0, already_open=False):
        self.biome = biome
        self.variant = variant
        self.opening = already_open
        self.last_frame = 15 if biome == "castle" else 13
        self.frame = self.last_frame if already_open else 0
        super().__init__(f"door_{biome}_{variant}_{self.frame}", pos, anchor=(0,0))

    def update(self):
        if self.opening and self.frame < self.last_frame and game.timer % 3 == 0:
            self.frame += 1
            self.image = f"door_{self.biome}_{self.variant}_{self.frame}"

    def open(self):
        self.opening = True

    def is_fully_open(self):
        return self.frame == self.last_frame

# Used for animations such as those that appear when you pick up a gem or lose a life
class Animation(Actor):
    def __init__(self, pos, image_format_str, num_frames, frame_interval, anchor=ANCHOR_CENTRE, initial_delay=0, rise_time=-1):
        super().__init__("blank", pos, anchor)
        self.image_format_str = image_format_str
        self.num_frames = num_frames
        self.frame_interval = frame_interval
        self.timer = -initial_delay
        self.rise_time = rise_time
        self.update_image()

    def update(self):
        self.timer += 1
        self.update_image()

        # Some animations start rising up after a certain time
        if self.rise_time > -1 and self.timer > self.rise_time:
            self.y -= 1

    def update_image(self):
        if self.timer < 0:
            self.image = "blank"
        else:
            frame = min(self.timer // self.frame_interval, self.num_frames - 1)
            self.image = self.image_format_str.format(frame)

    def finished(self):
        return self.timer // self.frame_interval >= self.num_frames

class DashTrail(Animation):
    def __init__(self, pos, image):
        # Receive's the player's current sprite, uses the trail version of that sprite
        super().__init__(pos, image + "_trail_{0}", 6, 5, ANCHOR_PLAYER)

# Base class for objects which move around the level and collide with walls, such as the player and enemies
class CollideActor(Actor):
    def __init__(self, pos, anchor=ANCHOR_CENTRE):
        super().__init__("blank", pos, anchor)

    def move(self, dx, dy, speed):
        # Returns true if move was blocked
        # One of dx or dy will be 0

        new_x, new_y = self.x, self.y

        # Movement is done 1 pixel at a time, which ensures we don't get embedded into a wall we're moving towards
        for i in range(speed):
            new_x, new_y = new_x + dx, new_y + dy

            # Get the player rectangle as it would be if the position were changed to new_x, new_y
            rect = self.get_rect(new_x, new_y)

            # Does this proposed new position overlap with any of the collidable tiles, or the exit door?
            if game.position_blocked(rect):
                #print(" blocked")
                return True

            # We only update the object's position if there wasn't a block there.
            self.pos = new_x, new_y
            #print(" moved")

        # Didn't collide with anything
        return False

    def get_rect(self, centre_x=None, bottom_y=None):
        # Returns a rectangle representing this actor, assuming it were positioned at the specified x and y coordinates
        # (If None, we default to the actual X/Y pos of the actor)
        # We don't use the standard Pygame Zero practice of just using the sprite bounds as the rectangle, as for the
        # player enemies we want the collidable size to be a bit smaller than the sprite
        if centre_x is None:
            centre_x = self.x
        if bottom_y is None:
            bottom_y = self.y
        w, h = self.get_collidable_width(), self.get_collidable_height()
        return Rect(centre_x - (w // 2), bottom_y - h, w, h)

    def get_collidable_width(self):
        # Overridden for Player and Enemy
        image_surface = getattr(images, self.image)
        return image_surface.get_width()

    def get_collidable_height(self):
        # Overridden for Player and Enemy
        image_surface = getattr(images, self.image)
        return image_surface.get_height()


# An actor who is subject to gravity, this includes the player and non-flying enemies
# The flying enemies do actually use this too, but disable it by setting gravity_enabled to false,
# demonstrating a drawback of inheritance in object-oriented programming! In a component-based
# system such as Unity, objects which want gravity could instead have a gravity component.
class GravityActor(CollideActor):
    MAX_FALL_SPEED = 7

    class FallState(Enum):
        LANDED = 0
        FALLING = 1
        JUMPING = 2
        WALL_JUMPING = 3

    def __init__(self, pos, gravity_enabled=True, anchor=ANCHOR_CENTRE_BOTTOM):
        super().__init__(pos, anchor)

        self.gravity_enabled = gravity_enabled
        self.vel_y = 0
        self.fall_state = GravityActor.FallState.FALLING
        self.lower_gravity_timer = 0

    def update(self, detect=True):
        if not self.gravity_enabled:
            return

        self.lower_gravity_timer -= 1

        # Apply change to Y velocity
        if game.timer % (3 if self.lower_gravity_timer > 0 else 2) == 0:
            self.vel_y = min(self.vel_y + 1, GravityActor.MAX_FALL_SPEED)

        # Apply gravity, without going over the maximum fall speed
        # The detect parameter indicates whether we should check for collisions with blocks as we fall. Normally we
        # want this to be the case - hence why this parameter is optional, and is True by default. If the player is
        # in the process of losing a life, however, we want them to just fall out of the level, so False is passed
        # in this case.
        if detect and self.vel_y != 0:
            # Move vertically in the appropriate direction, at the appropriate speed
            # Set landed to false, if we're on the floor it'll be set to true again below, otherwise it will remain
            # false
            if DEBUG_MOVEMENT:
                print("{0} detect: landed false, {1}".format(game.timer, self.vel_y))
            if self.fall_state == GravityActor.FallState.LANDED:
                self.fall_state = GravityActor.FallState.FALLING
            if self.move(0, sign(self.vel_y), abs(self.vel_y)):
                if DEBUG_MOVEMENT:
                    print("move returned true")
                # If move returned True, we must have either landed or hit our head on the ceiling
                if self.vel_y > 0:
                    self.vel_y = 0
                    self.fall_state = GravityActor.FallState.LANDED
                    if DEBUG_MOVEMENT:
                        print("detect: landed true")

        else:
            # Collision detection disabled - just update the Y coordinate without any further checks
            self.y += self.vel_y

    def landed(self):
        return self.fall_state == GravityActor.FallState.LANDED


class Player(GravityActor):
    DASH_TIME = 18
    DASH_SPEED = 10
    DASH_PAUSE_TIME = 5
    DASH_TRAIL_INTERVAL = 3
    DASH_TIMER_TRAIL_CUTOFF = -10
    MAX_X_RUN_SPEED = 5

    def __init__(self, controls):
        # Call constructor of parent class. Initial pos is 0,0 but Game.next_level will set the actual starting position
        super().__init__((0, 0), anchor=ANCHOR_PLAYER)

        self.controls = controls

        # Actor for the flame on the character's head
        self.flame = Actor("flame_stand_0", self.pos, anchor=ANCHOR_FLAME)

        self.vel_x = 0
        self.facing_x = 1
        self.hurt = False
        self.dash_timer = Player.DASH_TIMER_TRAIL_CUTOFF    # Counts down
        self.dash_animation_timer = 0                       # Counts up
        self.dash_allowed = False
        self.grabbed_wall = 0
        self.coyote_time = 0
        self.fall_timer = 0                 # Number of frames since we started falling or jumping
        self.wall_jump_coyote_time = 0
        self.cached_jump_input_timer = 0
        self.enemy_stomped_timer = 0
        self.change_direction_timer = 0
        self.last_dash_sprite = "dash_horizontal_0_0"   # Used for dash trails

        self.replay_data = []

    def new_level(self, start_pos):
        self.start_pos = start_pos
        self.reset()

    def reset(self):
        self.pos = self.start_pos
        self.vel_x = 0
        self.vel_y = 0
        self.facing_x = 1            # -1 = left, 1 = right
        self.hurt = False
        self.dash_timer = Player.DASH_TIMER_TRAIL_CUTOFF
        self.gravity_enabled = True
        self.grabbed_wall = 0
        self.coyote_time = 0
        self.wall_jump_coyote_time = 0
        self.cached_jump_input_timer = 0
        self.enemy_stomped_timer = 0

        # Ensure that when we spawn or respawn, there are no enemies at or near that position - treat it
        # as if we'd stomped on their heads
        # Need to check for game being None because player is constructed during Game construction, and the
        # game global won't be set until construction is complete
        if game is not None:
            for enemy in game.enemies:
                if self.distance_to(enemy) < 150:  # 150 pixel radius, to be safe
                    enemy.destroy()
                    game.play_sound("enemy_death", 5)

    def hit_test(self, other):
        # Check for collision between player and enemy - called from Player.update
        return self.get_rect(self.x, self.y).colliderect(other.get_rect()) and not self.hurt

    def get_colliding_enemies(self):
        return [enemy for enemy in game.enemies if not enemy.dying and self.hit_test(enemy)]

    def update(self):
        # Call GravityActor.update - parameter is whether we want to perform collision detection as we fall
        was_landed = self.landed()
        super().update(not self.hurt)

        if was_landed and not self.landed():
            # We must have walked off a platform. Set coyote time timer
            self.coyote_time = COYOTE_TIME
            self.fall_timer = 0

        if self.top >= HEIGHT:
            self.reset()

        # Check for collisions with enemies, including landing on their heads
        stomped_any = False
        for enemy in self.get_colliding_enemies():
            # Die or stomp? Are we within the top 20% of the enemy collision rectangle?
            # If we're moving downward, increase the threshold to the top 50% of the collision rectangle
            # We're fairly forgiving about this - otherwise some of the deaths seem unfair
            enemy_rect = enemy.get_rect()
            threshold = enemy_rect.top + (enemy_rect.bottom - enemy_rect.top) * (0.5 if self.vel_y > 0 else 0.2)
            # If the player stomps an enemy due to downward motion they'll now be moving up, so unless they're within
            # the top 20% of the sprite, they'll get hit by it on the next frame. Prevent this using stomped_last_frame
            if self.y < threshold or self.stomped_last_frame:
                enemy.stomped()
                stomped_any = True
                self.vel_y = -6
                self.enemy_stomped_timer = 3
                self.dash_allowed = True
                if DEBUG_MOVEMENT:
                    print(game.timer, "stomp", self.y, threshold)
            else:
                # Die and respawn
                self.hurt = True
                self.vel_y = -12
                self.fall_state = GravityActor.FallState.FALLING
                self.fall_timer = 0
                self.dash_timer = Player.DASH_TIMER_TRAIL_CUTOFF
                game.play_sound("player_death")
                game.animations.append(Animation(self.pos, "loselife_{0}", 8, 4))
                if DEBUG_MOVEMENT:
                    print(game.timer, "DIE", self.y, threshold)
                break

        self.stomped_last_frame = stomped_any

        if self.landed():
            self.dash_allowed = True

        self.dash_timer -= 1
        self.dash_animation_timer += 1
        self.cached_jump_input_timer -= 1
        self.coyote_time -= 1
        self.wall_jump_coyote_time -= 1

        if self.dash_timer > Player.DASH_TIMER_TRAIL_CUTOFF:
            if self.dash_timer % Player.DASH_TRAIL_INTERVAL == 0:
                game.animations.append(DashTrail(self.pos, self.last_dash_sprite))

        dx = 0  # X direction we tried to move this frame, zero if we are standing still

        jump_pressed = self.controls.button_pressed(0)

        if jump_pressed and DEBUG_MOVEMENT:
            print(game.timer, "jump pressed")

        #print(game.timer, self.cached_jump_input_timer, self.wall_jump_coyote_time)

        if self.hurt:
            # We've just been hurt. We're dropping out of the level, so check for our sprite reaching a certain Y
            # coordinate before setting hurt to False. Code further down will make the player respawn.
            self.gravity_enabled = True
            if self.top >= HEIGHT:
                self.hurt = False

        elif self.dash_timer > 0:
            # Update dash
            # For first few frames of dash, equating to dash_timer being above DASH_TIME, player doesn't move
            if self.dash_timer < Player.DASH_TIME:
                if self.dash_timer % Player.DASH_TRAIL_INTERVAL == 0:
                    game.animations.append(DashTrail(self.pos, self.last_dash_sprite))

                # A dash may be vertical, horizontal or diagonal
                # The horizontal and vertical components of the velocity are applied separately, to improve how
                # collision detection works

                # Apply vertical component of dash
                self.move(0, sign(self.vel_y), abs(self.vel_y))

                # Apply horizontal component of dash
                if self.move(sign(self.vel_x), 0, abs(self.vel_x)) and self.vel_y >= 0:
                    # If we hit a wall, and are not travelling up, end the dash
                    self.dash_timer = 0
                    self.grabbed_wall = self.facing_x

        else:
            # We're not hurt or dashing
            # We're either on a wall, jumping/falling or walking

            # Get keyboard input. dx represents the direction the player is facing
            dx = self.controls.get_x()

            def jump():
                if DEBUG_MOVEMENT:
                    print(game.timer, "JUMP")
                self.vel_y = JUMP_VEL_Y
                self.fall_state = GravityActor.FallState.JUMPING
                self.coyote_time = 0
                self.cached_jump_input_timer = 0
                self.lower_gravity_timer = 5
                self.fall_timer = 0
                game.play_sound("jump")

            def wall_jump(wall_direction):
                if DEBUG_MOVEMENT:
                    print(game.timer, "WALL JUMP", wall_direction)
                self.vel_y = JUMP_VEL_Y
                self.fall_state = GravityActor.FallState.WALL_JUMPING
                self.vel_x = -wall_direction * WALL_JUMP_X_VEL
                self.facing_x = -wall_direction
                self.grabbed_wall = 0
                self.previous_grabbed_wall = 0
                self.wall_jump_coyote_time = 0
                self.cached_jump_input_timer = 0
                self.fall_timer = 0
                game.play_sound("jump")

            # Non-zero means we're grabbing a wall
            if self.grabbed_wall != 0:
                # Wall slide
                self.gravity_enabled = False

                # Check for wall jump
                if jump_pressed or self.cached_jump_input_timer > 0:
                    if DEBUG_MOVEMENT:
                        print(game.timer, "wall jump", self.vel_x)
                    wall_jump(self.grabbed_wall)

                # Check if player is pushing away from the wall
                elif dx == -self.grabbed_wall:
                    if DEBUG_MOVEMENT:
                        print(game.timer, "ungrab wall", self.grabbed_wall)
                    self.previous_grabbed_wall = self.grabbed_wall
                    self.wall_jump_coyote_time = WALL_JUMP_COYOTE_TIME
                    self.grabbed_wall = 0

                else:
                    # Slowly slide down wall, stop grabbing if we hit the floor or the wall is no longer there (because
                    # we slid off the bottom of it)
                    if DEBUG_MOVEMENT:
                        print(game.timer, "slide", self.grabbed_wall)

                    rect = self.get_rect(self.x + self.grabbed_wall, self.y)

                    if self.move(0, 1, 1) or not game.position_blocked(rect):
                        self.grabbed_wall = 0
                        if DEBUG_MOVEMENT:
                            print(game.timer, "slide landed or wall gone")

            else:
                # Not grabbing a wall
                # Check for coyote time wall jump, i.e. a wall jump just after we let go of the wall

                # debug
                if DEBUG_MOVEMENT and self.wall_jump_coyote_time > 0:
                    print(game.timer, "remaining wall_jump_coyote_time", self.wall_jump_coyote_time)

                if jump_pressed and self.wall_jump_coyote_time > 0:
                    if DEBUG_MOVEMENT:
                        print(game.timer, "coyote wall jump")
                    wall_jump(self.previous_grabbed_wall)

                else:
                    # Normal movement
                    self.gravity_enabled = True
                    if dx == 0:
                        # No horizontal input - come to a halt over several frames
                        self.vel_x = move_towards(self.vel_x, 0, 1)
                    else:
                        # Horizontal input - apply to x velocity
                        self.facing_x = dx
                        self.vel_x = move_towards(self.vel_x, Player.MAX_X_RUN_SPEED * dx, 1)

                    # Apply x velocity
                    # Start grabbing wall if we hit a wall and our y velocity is downwards
                    # Note: order of checks matters, self.move may cause us to move so must come before vel_y check
                    if self.vel_x != 0 and self.move(sign(self.vel_x), 0, abs(self.vel_x)) and self.vel_y > 0:
                        if DEBUG_MOVEMENT:
                            print(game.timer, "grab")
                        self.grabbed_wall = sign(self.vel_x)

                        # Cancel horizontal velocity on hitting wall
                        self.vel_x = 0

                    if (jump_pressed or self.cached_jump_input_timer > 0) and (self.landed() or self.coyote_time > 0):
                        # Jump
                        if DEBUG_MOVEMENT:
                            if not jump_pressed:
                                print(game.timer, "cached jump")
                            if not self.landed():
                                print(game.timer, f"coyote time jump {self.coyote_time}")
                        jump()

                    elif jump_pressed and not self.landed():
                        # Cache jump input for a few frames, so that if the player lands just after pressing jump,
                        # a jump will be initiated
                        self.cached_jump_input_timer = CACHE_JUMP_INPUT_TIME

                    elif not self.landed() and self.vel_y < 0 and not self.controls.button_down(0) and self.dash_timer < -10 and self.enemy_stomped_timer <= 0:
                        # In the air and moving up, haven't finished dashing in last few frames
                        # Upward velocity drops off faster if player has let go of the jump button (unless they just
                        # stomped an enemy)
                        self.vel_y = min(self.vel_y + 1, 0)

                    if self.dash_allowed and self.controls.button_pressed(1):
                        # Dash
                        dy = self.controls.get_y()
                        if dx != 0 or dy != 0:
                            if DEBUG_MOVEMENT:
                                print(game.timer, "dash")
                            v = pygame.math.Vector2(dx, dy).normalize() * Player.DASH_SPEED
                            self.vel_x = int(v.x)
                            self.vel_y = int(v.y)
                            self.gravity_enabled = False
                            self.dash_allowed = False
                            self.dash_timer = Player.DASH_TIME + Player.DASH_PAUSE_TIME
                            self.dash_animation_timer = 0
                            self.fall_state = GravityActor.FallState.FALLING
                            self.wall_jump_coyote_time = 0
                            game.play_sound("jump_long", 5)

        # When we change direction, our X velocity will be different from our facing direction (dx)
        # We set a change direction timer which then counts down, while it's above zero we play the change
        # direction animation
        if sign(dx) != sign(self.vel_x) and self.dash_timer <= 0:
            self.change_direction_timer = 5
        else:
            self.change_direction_timer -= 1

        # Update sprite
        self.determine_sprite(dx)

        # Update fall timer after choosing sprite so that we don't just skip frame 0
        # Don't increase fall timer if we're dashing
        if not self.landed() and self.dash_timer <= 0:
            self.fall_timer += 1

        # Update replay data
        self.replay_data.append( (self.pos, game.level_index, self.image) )

    def determine_sprite(self, dx):
        # Set sprite image. If we're currently hurt, the sprite will flash on and off on alternate frames.
        # dx is X direction we tried to move this frame, zero if there was no control input
        self.image = self.flame.image = "blank"
        # Flame has different anchor point depending on whether we're dashing
        self.flame.anchor = ANCHOR_FLAME
        if not self.hurt or game.timer % 2 == 1:
            # Example sprite name: "run_0_3" - first number is direction (0 right, 1 left), second is the frame number
            dir_index = "1" if self.facing_x < 0 else "0"
            if self.hurt:
                # no flame for this animatoin
                frame = min(self.fall_timer // 8, 5)
                self.image = f"die_{frame}"
                self.flame_image = "blank"

            elif self.grabbed_wall != 0 and self.vel_y >= 0:
                # We don't do wall slide animation if we're moving upward
                self.image = f"climb_{dir_index}_1"
                self.flame.image = f"flame_climb_{dir_index}_1"

            elif not self.landed():
                # In air
                if self.fall_state == GravityActor.FallState.JUMPING:
                    frame = min(self.fall_timer // 3, 5)
                    flame_frame = min(self.fall_timer // 3, 5) + 1
                    self.image = f"jump_{dir_index}_{frame}"
                    self.flame.image = f"flame_jump_{dir_index}_{flame_frame}"
                elif self.fall_state == GravityActor.FallState.WALL_JUMPING:
                    frame = min(self.fall_timer // 8, 2)
                    flame_frame = min(self.fall_timer // 4, 6)
                    self.image = f"wall_jump_{dir_index}_{frame}"
                    self.flame.image = f"flame_wall_jump_{dir_index}_{flame_frame}"
                elif self.dash_timer > 0:
                    # Choose a dash sprite and update self.last_dash_image
                    # Initially all dash directions use dash_start_0/1 (depending on facing direction), before
                    # switching to specific frames for different dash directions
                    if self.dash_animation_timer < 4:
                        flame_frame = self.dash_animation_timer // 2
                        self.image = self.last_dash_sprite = "dash_start_" + dir_index
                        self.flame.image = f"flame_dash_start_{dir_index}_{flame_frame}"
                        self.flame.anchor = ANCHOR_FLAME
                    else:
                        timer = self.dash_animation_timer - 4
                        frame = min(timer // 3, 2)
                        flame_frame = min(timer // 3, 7)
                        sprite = "dash_"
                        if self.vel_y < 0:
                            sprite += "up_"
                        elif self.vel_y > 0:
                            sprite += "down_"
                        if self.vel_x != 0:
                            sprite += "horizontal_"
                        self.image = self.last_dash_sprite = f"{sprite}{dir_index}_{frame}"
                        self.flame.image = f"flame_{sprite}{dir_index}_{flame_frame}"
                        self.flame.anchor = ANCHOR_FLAME_DASH
                else:
                    # For flame, use frames 4 and 5 of wall jump
                    frame = min(self.fall_timer // 8, 1)
                    flame_frame = min(self.fall_timer // 8, 1) + 4
                    self.image = f"fall_{dir_index}_{frame}"
                    self.flame.image = f"flame_wall_jump_{dir_index}_{flame_frame}"

            elif dx == 0:
                self.image = "stand_front"
                self.flame.image = f"flame_stand_{(game.timer // 4) % 8}"

            elif self.change_direction_timer > 0:
                # If change_direction_timer is positive, use change direction frame
                self.image = f"change_dir_{dir_index}_0"
                self.flame.image = f"flame_change_dir_{dir_index}_{(game.timer // 4) % 3}"
            else:
                # 8 frames of the run animation, switch animation frame every 4 game frames
                frame = (game.timer // 4) % 8
                self.image = f"run_{dir_index}_{frame}"
                self.flame.image = f"flame_run_{dir_index}_{(game.timer // 4) % 8}"

    def draw(self):
        super().draw()

        self.flame.pos = self.pos
        self.flame.draw()

        if DEBUG_SHOW_PLAYER_COLLISION_RECT:
            # Show collision rectangle
            screen.draw.rect(self.get_rect(), (255,255,255))

    def get_collidable_width(self):
        return PLAYER_WIDTH

    def get_collidable_height(self):
        return PLAYER_HEIGHT

class GhostPlayer(Actor):
    def __init__(self, replay_data):
        super().__init__("blank", replay_data[0][0], ANCHOR_PLAYER)
        self.replay_data = replay_data
        self.replay_frame = 0
        self.level = 0

    def update(self):
        self.replay_frame += 1
        if self.replay_frame < len(self.replay_data):
            self.pos, self.level, sprite = self.replay_data[self.replay_frame]
            if sprite == "blank":
                self.image = "blank"
            else:
                self.image = "ghost_" + sprite

    def draw(self):
        # Only draw if we're on the same level as the actual player
        if self.level == game.level_index:
            super().draw()

class Enemy(GravityActor):
    def __init__(self, pos, type, biome, direction_x=1, appearance_count=1):
        # Type must be a number from 0 to 3. 0 and 1 are both flying robots which don't have different frames for facing
        # left or right. 2 and 3 are non-flying robots which do have left/right facing frames.

        super().__init__(pos, gravity_enabled=not ENEMY_TYPES_FLYING[biome][type], anchor=ENEMY_TYPES_ANCHOR_POINTS[biome][type])

        self.direction_x = direction_x
        self.type = type
        self.biome = biome

        self.health = ENEMY_TYPES_HEALTH[type]
        self.speed = ENEMY_TYPES_SPEED[type]

        # Flying enemies which are on their third appearance will move diagonally
        self.direction_y = 1 if appearance_count >= 3 and not self.gravity_enabled else 0

        # Robot types 2 and 3, and fly/ghost have different sprites for facing left/right
        self.use_directional_sprites = (self.biome == Biome.CASTLE and self.type >= 2) or (self.biome == Biome.FOREST and self.type < 2)

        self.dying = False
        self.stomped_timer = 0

    def update(self):
        super().update(detect=not self.dying)

        if not self.dying:
            self.stomped_timer -= 1

            # Don't move on x axis if falling. Flying enemies are always counted as falling by GravityActor, they
            # should move regardless.
            if not self.gravity_enabled or self.fall_state != GravityActor.FallState.FALLING:
                # Move in current direction - turn around if we hit a wall
                if self.move(self.direction_x, 0, self.speed):
                    self.direction_x = -self.direction_x
                if self.direction_y != 0 and self.move(0, self.direction_y, self.speed):
                    self.direction_y = -self.direction_y

        # Choose and set sprite image
        image = ENEMY_SPRITE_NAMES[self.biome][self.type]
        if self.use_directional_sprites:
            direction_idx = "1" if self.direction_x > 0 else "0"
            image += "_" + str(direction_idx)
        image += "_" + str((game.timer // 4) % 8) # 8 frames of animation
        if self.stomped_timer > 0 or self.dying:
            image += "_hit"
        self.image = image

    def stomped(self):
        # Don't lose health or play sound effect if we're being stomped multiple frames in a row
        if self.stomped_timer <= 0:
            self.health -= 1
            if self.health <= 0:
                self.destroy()
                game.play_sound("enemy_death", 5)
            else:
                game.play_sound("enemy_take_damage", 5)
        self.stomped_timer = 2

    def destroy(self):
        self.dying = True
        self.gravity_enabled = True

        # Create explosion animation. Do this before gain_time so it appears underneath gain time animation
        explosion_sprite = "explosion" if self.type > 1 else "air_explosion"
        game.animations.append(Animation(self.pos, explosion_sprite + "_{0}", 12, 4, ANCHOR_CENTRE_BOTTOM))

        # Destroying an enemy always gains 3 seconds of time
        game.gain_time(STOMP_ENEMY_TIME_BONUS, self.centerx, self.centery)

    def get_collidable_width(self):
        return ENEMY_TYPES_WIDTH_OVERRIDES[self.biome][self.type]

    def get_collidable_height(self):
        return ENEMY_TYPES_HEIGHT_OVERRIDES[self.biome][self.type]

    def draw(self):
        super().draw()

        if DEBUG_SHOW_ENEMY_COLLISION_RECTS:
            # Show collision rectangle
            screen.draw.rect(self.get_rect(), (255,255,255))

class Game:
    def __init__(self, player=None, replays=None):
        self.player = player

        # Gem class is told via a static method that a new game has started, so it can reset the next gem type variable
        Gem.new_game()

        self.ghost_players = []
        if replays is not None:
            for replay in replays:
                self.ghost_players.append(GhostPlayer(replay))

        self.timer = 0
        self.time_remaining = INITIAL_TIME_REMAINING * 60
        self.time_pickup_bonus = INITIAL_PICKUP_TIME_BONUS
        self.gained_time_timer = 0

        self.level_index = (INITIAL_LEVEL_CYCLE * len(LEVEL_SEQUENCE)) - 1

        self.level_text = ""

        # These are set during load_level
        self.grid = None
        self.tileset_image = None
        self.background_image = None
        self.background_y_offset = 0

        self.next_level()

    def next_level(self):
        self.level_index += 1

        # If the new level is a repeat of the first level, reduce self.time_pickup_bonus by 1 (to a minimum of 0.5)
        if self.level_index != 0 and self.level_index % len(LEVEL_SEQUENCE) == 0:
            if self.time_pickup_bonus > 1:
                self.time_pickup_bonus -= 1
            elif self.time_pickup_bonus == 1:
                self.time_pickup_bonus = 0.5

        self.block_rects = []
        self.doors = []
        self.gems = []
        self.enemies = []
        self.animations = []
        self.level_text = ""

        # Set up level
        level_filename = LEVEL_SEQUENCE[self.level_index % len(LEVEL_SEQUENCE)]
        player_start_pos = self.load_level(level_filename)

        self.exit_open = False

        if self.player is not None:
            self.player.new_level(player_start_pos)

        # Generate collidable areas
        self.generate_block_rects()

        if self.player:
            self.player.reset()

        self.play_sound("new_wave")

    def load_level(self, filename):
        # Returns player start pos, or (0,0) if none is found
        player_start_pos = (0, 0)

        # 0 for first time through the levels, 1 for second, etc
        level_cycle = self.level_index // len(LEVEL_SEQUENCE)

        # sys.path[0] gets the folder containing the Python file we're running
        # This is necessary because we could be running in an IDE where the default working folders is not the script
        # folder but is instead the parent folder, or we could be running preinstalled on a Raspberry Pi in which case
        # the current working folder is the user's home folder
        path = os.path.join(sys.path[0], "tilemaps")

        # The map and tileset files are XML files. We're using Python's built in ElementTree module (aliased here as ET)
        # to access the tags/nodes within the XML files.
        map_tree = ET.parse(os.path.join(path, filename))
        map_root = map_tree.getroot()

        # Load background
        properties_node = map_root.find("properties")
        self.background_image = properties_node.find("./property[@name='Background']").attrib["value"]
        bg_offset_node = properties_node.find("./property[@name='Background Offset Y']")
        self.background_y_offset = int(bg_offset_node.attrib["value"]) if bg_offset_node is not None else 0

        # Load biome (used for determining which types of enemies and doors to generate)
        biome_node = properties_node.find("./property[@name='biome']")
        biome_name = biome_node.attrib["value"] if biome_node is not None else ""
        biome = Biome[biome_name.upper()]

        # Default level name text - may be replaced by tutorial text below
        self.level_text = "LEVEL " + str(self.level_index + 1)

        # Set up level tutorial text - only the first time we go round the levels.
        # Some text will have parts which we need to substitute
        # Use blank level text if there is no player object (i.e. we're on the main menu)
        tutorial_text_node = properties_node.find("./property[@name='TutorialText']")
        if self.player is not None and tutorial_text_node is not None:
            tutorial_text = tutorial_text_node.attrib["value"]
            if level_cycle == 0 and len(tutorial_text) > 0:
                dash_button_name = self.player.controls.button_name("dash")
                jump_button_name = self.player.controls.button_name("jump")
                self.level_text = tutorial_text.replace("{DASH}", dash_button_name).replace("{JUMP}", jump_button_name)

        # The map data consists of a comma-separated list of integers specifying tile IDs
        # The XML path is map/layer/data
        layer_node = map_root.find("layer")
        map_width = int(layer_node.attrib.get("width"))
        map_height = int(layer_node.attrib.get("height"))
        map_data = layer_node.find("data").text.split(",")

        # Convert map data from CSV into a 2D list of ints
        # We subtract 1 from each tile ID because we want the tile IDs to start from 0 (signifying the top left of the
        # tileset image) rather than 1. This means that empty tile will now have an ID of -1
        self.grid = []
        for row in range(map_height):
            # Extract each row from the map data
            row_start_index = row * map_width
            current_row = [int(tile) - 1 for tile in map_data[row_start_index:row_start_index+map_width]]
            self.grid.append(current_row)

        # Read object layer, which specifies things like the player start position, gems and enemies
        object_group_node = map_root.find("objectgroup")
        if object_group_node is not None:
            for object_node in object_group_node.findall("object"):
                object_name = object_node.attrib["name"]

                # Extract the object position. Why do we write 'int(float(...))'? Because the number is read from the
                # file as a string, and we'd like it as an int, but we also want to ignore anything after the
                # decimal point, which we don't care about. We can't convert directly from string to int because
                # that would fail when it encountered a number with a decimal point.
                object_pos = (int(float(object_node.attrib["x"])), int(float(object_node.attrib["y"])))
                if object_name == "PlayerStart":
                    player_start_pos = object_pos

                elif object_name == "Gem":
                    self.gems.append(Gem(object_pos))

                elif "Enemy" in object_name:
                    # Enemies have names such as "EnemyR00" where L/R indicate their initial facing direction, the
                    # first number indicates the enemy type (0 to 3), and the final number indicates the level cycle
                    # during which they first show up. Some enemies only show up on the second or third cycle through
                    # the levels
                    enemy_level_cycle = int(object_name[-1])
                    appearance_count = (level_cycle - enemy_level_cycle) + 1
                    if appearance_count >= 1:
                        facing = 1 if object_name[-3] == "R" else -1
                        enemy_type = int(object_name[-2])
                        self.enemies.append(Enemy(object_pos, enemy_type, biome, facing, appearance_count))

                elif "Door" in object_name:
                    variant_node = object_node.find("./properties/property[@name='Variant']")
                    biome_node = object_node.find("./properties/property[@name='Biome']")
                    variant = variant_node.attrib["value"] if variant_node is not None else 0
                    door_biome_name = biome_node.attrib["value"] if biome_node is not None else biome_name
                    entrance = "Entrance" in object_name
                    self.doors.append(Door(object_pos, door_biome_name, variant, entrance))

        # For the purpose of simplicity we assume that each map file only uses one tileset, which will be either the
        # forest or castle tileset. The tileset filename is specified in the 'tileset' tag within the root node
        tileset_filename = map_root.find("tileset").attrib.get("source")

        # Read tileset file, which specifies which tiles are collidable
        self.collision_tiles = set()
        tileset_xml = ET.parse(os.path.join(path, tileset_filename))
        for tile_node in tileset_xml.getroot().findall("tile"):
            # For now we'll just assume that any tile which has a node, has collision
            self.collision_tiles.add(int(tile_node.attrib["id"]))

        # Load tileset image (if we haven't loaded it already)
        tileset_image_filename = tileset_xml.getroot().find("image").attrib["source"]
        if tileset_image_filename not in tileset_images:
            tileset_images[tileset_image_filename] = pygame.image.load(os.path.join(path, tileset_image_filename))
        self.tileset_image = tileset_images[tileset_image_filename]

        return player_start_pos

    def generate_block_rects(self):
        self.block_rects = []
        current_rect = None

        def add():
            nonlocal current_rect
            self.block_rects.append(current_rect)
            current_rect = None

        # Horizontal rows
        for gy in range(len(self.grid)):
            row = self.grid[gy]
            for gx in range(len(row)):
                if row[gx] in self.collision_tiles:
                    pos_x = gx * GRID_BLOCK_SIZE
                    pos_y = gy * GRID_BLOCK_SIZE
                    # Is this the start of a new block rect?
                    if current_rect is None:
                        current_rect = Rect(pos_x, pos_y, GRID_BLOCK_SIZE, GRID_BLOCK_SIZE)
                    else:
                        # Continue existing rect
                        current_rect.w += GRID_BLOCK_SIZE

                elif current_rect is not None:
                    add()
            if current_rect is not None:
                add()

        # Now consolidate vertically
        # Keep joining rectangles with rectangles of equal width directly below, until there are no more such
        # matches

        def find_equal_width_block_below(current):
            # Returns a block with the same X coordinate and width, which is immediately below the current block,
            # or None if no such block exists
            result = [rect for rect in self.block_rects if rect.x == current.x and rect.w == current.w and rect.y == current.y + current.h]
            return result[0] if len(result) > 0 else None

        any_found = True
        while any_found:
            any_found = False
            for current in self.block_rects:
                equal_below = find_equal_width_block_below(current)
                if equal_below is not None:
                    # Extend the height of the current block and remove the one below
                    current.h += equal_below.h
                    self.block_rects.remove(equal_below)
                    any_found = True
                    break

        # Final step: any block rects aligning with the top of the level have their height increased so it extends
        # above the level, to prevent standing on top of the trees off the top of the screen
        for rect in self.block_rects:
            if rect.top == 0:
                height = rect.height
                rect.top = LEVEL_Y_BOUNDARY
                rect.height = height + -LEVEL_Y_BOUNDARY

    def update(self):
        self.timer += 1
        self.gained_time_timer -= 1

        if self.time_remaining > 0:
            self.time_remaining -= 1

        # Update all objects
        for obj in [self.player] + self.doors + self.animations + self.gems + self.enemies + self.ghost_players:
            if obj:
                obj.update()

        # Remove expired enemies, dash trails, gems and animations
        self.enemies = [enemy for enemy in self.enemies if enemy.top < HEIGHT]
        self.animations = [anim for anim in self.animations if not anim.finished()]
        self.gems = [gem for gem in self.gems if not gem.collected]

        # Check stuff to do with opening exit door and exiting level (but not if we're on the main menu)
        if self.player is not None:
            if self.exit_open:
                # Check for the player leaving the level
                if self.player.centerx >= WIDTH:
                    self.next_level()

            elif len(self.gems) == 0:
                # All gems collected, open the exit door
                self.exit_open = True
                for door in self.doors:
                    door.open()

    def draw(self):
        # Draw appropriate background for this level
        screen.blit(self.background_image, (0, self.background_y_offset))

        # Draw level tiles
        tileset_w = self.tileset_image.get_width()
        tileset_grid_w = tileset_w // GRID_BLOCK_SIZE
        for row_y in range(len(self.grid)):
            row = self.grid[row_y]
            x = 0
            for tile in row:
                if tile >= 0:
                    # Get sprite from tileset based on ID
                    tileset_grid_y = tile // tileset_grid_w
                    tileset_grid_x = tile % tileset_grid_w
                    # Have to use screen.surface.blit instead of screen.blit as the latter is a Pygame Zero method which
                    # passes through to the Pygame version but doesn't support the optional area parameter
                    tile_rect = Rect(tileset_grid_x * GRID_BLOCK_SIZE, tileset_grid_y * GRID_BLOCK_SIZE, GRID_BLOCK_SIZE, GRID_BLOCK_SIZE)
                    screen.surface.blit(self.tileset_image, (x, row_y * GRID_BLOCK_SIZE), area=tile_rect)
                x += GRID_BLOCK_SIZE

        # Draw all objects, in this order
        for obj in self.ghost_players + self.doors + self.animations + [self.player] + self.gems + self.enemies:
            if obj is not None:
                obj.draw()

        # DEBUG - draw block rects
        if DEBUG_SHOW_BLOCK_COLLISION_RECTS:
            for rect in self.block_rects:
                screen.draw.rect(rect, (255,255,255))

        self.draw_ui()

    def draw_ui(self):
        # Display level text and background
        pygame.draw.rect(screen.surface, (0,54,255), Rect(0,500,WIDTH, 50))
        screen.blit("text_area_frame", (0, 500))
        draw_text(self.level_text, WIDTH // 2, 508, align=TextAlign.CENTRE)

        # Show background sprite for time remaining
        screen.blit("status_back", (WIDTH // 2 - 297 // 2, 0))

        # Show time remaining
        # Use bright font if player has just gained time
        font = "font" if self.gained_time_timer < 0 else "fontbr"
        draw_text(f"{self.time_remaining / 60:.1f}", WIDTH // 2, 10, align=TextAlign.CENTRE, font=font)

        if DEBUG_SHOW_FRAME_NUMBER:
            draw_text(str(game.timer), WIDTH // 2, 0, align=TextAlign.CENTRE)

    def gain_time(self, time, x, y):
        game.time_remaining += time * 60
        time_added_id = "half" if time == 0.5 else str(time)
        format_str = "timer_plus_" + time_added_id + "_{0}"
        game.animations.append(Animation((x,y), format_str, 14, 4, initial_delay=5, rise_time=34))
        game.animations.append(Animation((x,y), "pickup_{0}", 8, 4))
        self.gained_time_timer = 20

    def position_blocked(self, rect):
        # Check collision with block tiles
        for block_rect in self.block_rects:
            if rect.colliderect(block_rect):
                # print(" blocked")
                return True

        # Check collision with door
        for door in self.doors:
            if not door.is_fully_open() and door.colliderect(rect):
                return True

        # Don't allow going off left side of screen, or above vertical boundary
        # We do need to allow player to go off right side of screen so they can go
        # through the exit door
        if rect.left <= 0 or rect.top < LEVEL_Y_BOUNDARY:
            return True

        return False

    def play_sound(self, name, count=1):
        # Some sounds have multiple varieties. If count > 1, we'll randomly choose one from those
        # We don't play any sounds if there is no player (e.g. if we're on the menu)
        if self.player:
            try:
                # Pygame Zero allows you to write things like 'sounds.explosion.play()'
                # This automatically loads and plays a file named 'explosion.wav' (or .ogg) from the sounds folder (if
                # such a file exists)
                # But what if you have files named 'explosion0.ogg' to 'explosion5.ogg' and want to randomly choose
                # one of them to play? You can generate a string such as 'explosion3', but to use such a string
                # to access an attribute of Pygame Zero's sounds object, we must use Python's built-in function getattr
                sound = getattr(sounds, name + str(randint(0, count - 1)))
                sound.play()
            except Exception as e:
                # If no sound file of that name was found, print the error that Pygame Zero provides, which
                # includes the filename.
                # Also occurs if sound fails to play for another reason (e.g. if this machine has no sound hardware)
                print(e)

def get_char_image_and_width(char, font):
    # Return width of given character. ord() gives the Unicode code for the given character.
    if char == " ":
        return None, 22
    else:
        if char in SPECIAL_FONT_SYMBOLS_INVERSE:
            image = getattr(images, SPECIAL_FONT_SYMBOLS_INVERSE[char])
        else:
            # Format character code to always be 3 digits, with zeroes on the left - e.g. 65 becomes 065
            image = getattr(images, f"{font}{ord(char):03d}")
        return image, image.get_width()

def text_width(text, font):
    return sum([get_char_image_and_width(c, font)[1] for c in text])

class TextAlign(Enum):
    LEFT = 0
    CENTRE = 1
    RIGHT = 2
    
def draw_text(text, x, y, align=TextAlign.LEFT, font="font"):
    if align == TextAlign.CENTRE:
        x -= text_width(text, font) // 2
    elif align == TextAlign.RIGHT:
        x -= text_width(text, font)

    for char in text:
        image, width = get_char_image_and_width(char, font)
        if image is not None:
            screen.blit(image, (x, y))
        x += width

class State(Enum):
    TITLE = 1
    CONTROLS = 2
    PLAY = 3
    GAME_OVER = 4

def get_joystick_if_exists():
    return pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None

def setup_joystick_controls():
    # We call this on startup, and keep calling it if no controller is present,
    # so a controller can be connected while the game is open
    global joystick_controls
    joystick = get_joystick_if_exists()
    joystick_controls = JoystickControls(joystick) if joystick is not None else None

def update_controls():
    keyboard_controls.update()
    # Allow a controller to be connected while the game is open
    if joystick_controls is None:
        setup_joystick_controls()
    if joystick_controls is not None:
        joystick_controls.update()

def get_save_folder():
    # By default, we save to the same folder as the Python file
    # But if the current working folder is the same as the user's home folder, write save data to a subfolder of that,
    # because the folder containing the Python file may not be writeable. This is relevant when the games are run from
    # the pre-installed versions which come with Raspberry Pi OS
    # On Windows, the home folder is C:\Users\<username>\
    current_working_folder = os.getcwd()
    home_folder = os.path.expanduser('~')
    if current_working_folder != home_folder:
        return sys.path[0]
    else:
        # Get a location within the user's home folder, then ensure the folder exists
        path = os.path.expanduser('~/.code-the-classics-vol-2')
        if not os.path.exists(path):
            os.makedirs(path)
        return path

def save_replays(replays):
    # We'll save one replay per line, with entries separated by commas
    try:
        with open(os.path.join(get_save_folder(), REPLAY_FILENAME), "w") as file:
            for replay in replays:
                line = ""
                for entry in replay:
                    # Each entry consists of a position (X and Y in a tuple), level number and sprite
                    # We'll separate the items using commas and the entries using semicolons. It doesn't matter what
                    # the symbols are as long as they don't occur within the data
                    # Open the replays file to see what it looks like!
                    line += f"{int(entry[0][0])},{int(entry[0][1])},{entry[1]},{entry[2]};"

                # Write the string for the current replay to the file, removing the trailing symbol from the end, and
                # adding a new line on the end
                file.write(line[0:-1] + "\n")
    except Exception as e:
        print(f"Error while saving replays: {e}")

def load_replays():
    # Returns list of replays and high score
    replays = []
    try:
        path = os.path.join(get_save_folder(), REPLAY_FILENAME)
        if os.path.exists(path):
            with open(path) as file:
                for line in file:
                    current_replay = []

                    # Remove the newline symbol from the end of the line
                    line = line.rstrip()

                    # Split the string on semicolon to get a list of all entries for this replay
                    entries = line.split(";")

                    for entry in entries:
                        # Within each entry, split on comma and convert each element to the correct type
                        elements = entry.split(",")

                        pos = (float(elements[0]), float(elements[1]))

                        current_replay.append( (pos, int(elements[2]), elements[3]) )

                    replays.append(current_replay)

    except Exception as e:
        # In case of error (eg missing file or formatting error), just return an empty list, and high score of zero
        print("Error while loading replays: '" + str(e) + "'. Replay data will be reset")
        return [], 0

    # The high score is stored as the total number of frames of data in the replay with the longest length
    high_score = 0 if len(replays) == 0 else len(max(replays, key=lambda replay: len(replay)))

    return replays, high_score

# Pygame Zero calls the update and draw functions each frame

def update():
    global state, game, high_score, game_over_state_timer, all_replays, total_frames

    # Run in slow motion if DEBUG_SLOWMO is higher than 1
    total_frames += 1
    if total_frames % DEBUG_SLOWMO != 0:
        return

    update_controls()

    def button_pressed_controls(button_num):
        # Local function for detecting button 0 being pressed on either keyboard or controller, returns the controls
        # object which was used to press it, or None if button was not pressed
        for controls in (keyboard_controls, joystick_controls):
            # Check for fire button being pressed on each controls object
            # joystick_controls will be None if there no controller was connected on game startup,
            # so must check for that
            if controls is not None and controls.button_pressed(button_num):
                return controls
        return None

    if state == State.TITLE:
        # Check for player starting game with either keyboard or controller
        if button_pressed_controls(0) is not None:
            state = State.CONTROLS

    elif state == State.CONTROLS:
        # Check for start game
        controls = button_pressed_controls(0)
        if controls is not None:
            # Switch to play state, and create a new Game object, passing it a new Player object to use
            state = State.PLAY
            game = Game(Player(controls), all_replays)
            play_music("ingame_theme", 0.2)

    elif state == State.PLAY:
        if game.time_remaining <= 0:
            game.play_sound("gameover")
            state = State.GAME_OVER
            game_over_state_timer = 0

            # Add the replay data for this game to all_replays
            all_replays.append(game.player.replay_data)

            # Ensure that all_replays never has more than 10 replays, otherwise there could be performance issues
            if len(all_replays) > MAX_REPLAYS:
                # Sort replays by length, longest first
                all_replays.sort(key=lambda replay: len(replay), reverse=True)

                # Recreate the list, consisting of only the first 10
                all_replays = all_replays[:MAX_REPLAYS]

            save_replays(all_replays)
        else:
            game.update()

    elif state == State.GAME_OVER:
        # Don't allow the player to press a button to go back to the main menu until one second has passed
        # This prevents the issue of accidentally skipping the game over screen because the player was just starting
        # to press the jump button as the time ran out
        game_over_state_timer += 1
        if game_over_state_timer > 60 and button_pressed_controls(0) is not None:
            # Update high score variable at this point
            if game.timer > high_score:
                high_score = game.timer

            # Switch to title screen state
            state = State.TITLE
            play_music("title_theme")

def draw():
    if state == State.TITLE:
        # Draw title screen
        screen.blit("title", (0, 0))
        screen.blit("press_to_start", (0, 0))

        # Draw "start" animation, which has 11 frames numbered 0 to 10
        anim_frame = (total_frames // 6) % 11
        screen.blit("start" + str(anim_frame), (WIDTH//2 - 150, 360))

    elif state == State.CONTROLS:
        screen.fill((0, 0, 0))
        screen.blit("controls", (0, 0))

    elif state == State.PLAY:
        game.draw()

    elif state == State.GAME_OVER:
        screen.fill((0,54,255))

        # Display "Game Over" images
        # 625 is the width of the game over images
        anim_frame = (total_frames // 5) % 14
        screen.blit(f"gameover{anim_frame}", (WIDTH//2 - 625//2, 100))

        seconds = int(game.timer / 60)
        if seconds >= 60:
            screen.blit("survived_for_mins_seconds", (0, 0))
            draw_text(f"{seconds // 60}", 180, 270, align=TextAlign.RIGHT, font="fontlrg")
            draw_text(f"{seconds % 60}", 470, 270, align=TextAlign.CENTRE, font="fontlrg")
        else:
            screen.blit("survived_for_seconds", (0, 0))
            draw_text(f"{seconds}", 300, 310, align=TextAlign.RIGHT, font="fontlrg")

        if game.timer > high_score:
            # Show "NEW RECORD!"
            # 575 is the width of the new record images
            anim_frame = (total_frames // 5) % 8
            screen.blit(f"newrecord{anim_frame}", (WIDTH // 2 - 575 // 2, 380))

def play_music(name, volume=0.3):
    try:
        music.play(name)
        music.set_volume(volume)
    except Exception:
        # If an error occurs (e.g. no sound hardware), ignore it
        pass

##############################################################################

# Set up sound system and start music
try:
    # Restart the Pygame audio mixer which Pygame Zero sets up by default. We find that the default settings
    # cause issues with delayed or non-playing sounds on some devices
    pygame.mixer.quit()
    pygame.mixer.init(48000, -16, 2, 1024)

    play_music("title_theme")
except Exception:
    # If an error occurs (e.g. no sound hardware), ignore it
    pass

# Dictionary mapping tileset image filename to the loaded images, will be filled in as we load levels
tileset_images = {}

# Set up controls
keyboard_controls = KeyboardControls()
setup_joystick_controls()

all_replays, high_score = load_replays()

# Set the initial game state
state = State.TITLE
game = None

# How long have we been in the game over state?
game_over_state_timer = 0

total_frames = 0

# Tell Pygame Zero to take over
pgzrun.go()
