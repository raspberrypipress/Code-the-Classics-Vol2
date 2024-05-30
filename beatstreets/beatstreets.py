# Beat Streets - Code the Classics Volume 2
# Code by Andrew Gillett and Eben Upton
# Graphics by Dan Malone
# Music and sound effects by Allister Brimble
# https://github.com/raspberrypipress/Code-the-Classics-Vol2.git
# TODO BOOK URL

# If the game window doesn't fit on the screen, you may need to turn off or reduce display scaling in the Windows/macOS settings
# On Windows, you can uncomment the following two lines to fix the issue. It sets the program as "DPI aware"
# meaning that display scaling won't be applied to it.
#import ctypes
#ctypes.windll.user32.SetProcessDPIAware()

import pgzero, pgzrun, pygame, sys, json, time
from abc import ABC, abstractmethod
from enum import Enum
from random import randint, choice
from pygame import Vector2, mixer

HEALTH_STAMINA_BAR_WIDTH = 235
HEALTH_STAMINA_BAR_HEIGHT = 26

INTRO_ENABLED = True

FLYING_KICK_VEL_X = 3
FLYING_KICK_VEL_Y = -8

JUMP_GRAVITY = 0.4
THROWN_GRAVITY = 0.025
WEAPON_GRAVITY = 0.5

BARREL_THROW_VEL_X = 4
BARREL_THROW_VEL_Y = 0

# For when player is thrown by boss
PLAYER_THROW_VEL_X = 5
PLAYER_THROW_VEL_Y = 0.5

# By default, the effect of an attack on the opponent's stamina is damage * 100
# Some attacks have an additional stamina damage multiplier
BASE_STAMINA_DAMAGE_MULTIPLIER = 100

# If stamina goes below zero, player can be knocked over more easily and minimum interval between attacks
# is longer
MIN_STAMINA = -100

DEBUG_LOGGING_ENABLED = False
DEBUG_SHOW_SCROLL_POS = False
DEBUG_SHOW_BOUNDARY = False
DEBUG_SHOW_ATTACKS = False
DEBUG_SHOW_TARGET_POS = False
DEBUG_SHOW_ANCHOR_POINTS = False
DEBUG_SHOW_HIT_AREA_WIDTH = False
DEBUG_SHOW_LOGS = False
DEBUG_SHOW_HEALTH_AND_STAMINA = False
DEBUG_PROFILING = False

# These symbols substitute for the controller button images when displaying text.
# The symbols representing these images must be ones that aren't actually used themselves, e.g. we don't use the
# percent sign in text
SPECIAL_FONT_SYMBOLS = {'xb_a':'%'}

# Create a version of SPECIAL_FONT_SYMBOLS where the keys and values are swapped
SPECIAL_FONT_SYMBOLS_INVERSE = dict((v,k) for k,v in SPECIAL_FONT_SYMBOLS.items())

debug_drawcalls = []

# Class for measuring how long code takes to run
class Profiler:
    def __init__(self, name=""):
        self.start_time = time.perf_counter()
        self.name = name

    def get_ms(self):
        endTime = time.perf_counter()
        diff = endTime - self.start_time
        return diff * 1000

    def __str__(self):
        return f"{self.name}: {self.get_ms()}ms"

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

WIDTH = 800
HEIGHT = 480
TITLE = "Beat Streets"

MIN_WALK_Y = 310

ENEMY_APPROACH_PLAYER_DISTANCE = 85
ENEMY_APPROACH_PLAYER_DISTANCE_SCOOTERBOY = 140
ENEMY_APPROACH_PLAYER_DISTANCE_BARREL = 180

ANCHOR_CENTRE = ("center", "center")
ANCHOR_CENTRE_BOTTOM = ("center", "bottom")

BACKGROUND_TILE_SPACING = 290

# 1st row of TILE_DEMO+_3.png
BACKGROUND_TILES = ["wall_end1", "wall_fill1", "wall_fill5", "wall_fill2", "alley1", "wall_end6", "wall_fill7",
                    "wall_fill5", "alley2", "wall_end3", "wall_fill3", "wall_fill4", "wall_fill8", "alley5",
                    "wall_end2", "alley3", "wall_end4", "wall_fill6",
#row 2
                    "alley6", "wall_end8", "wall_fill4", "alley7", "wall_end5", "alley8", "set_pc_a1", "set_pc_a2",
                    "alley9", "set_pc_b1", "set_pc_b2", "set_pc_b3", "wall_end3", "wall_fill3", "alley8", "set_pc_a1",
                    "set_pc_a2", "wall_fill2",
#3
                    "con_start2", "con_end1a", "con_end2", "con_start2", "con_end1", "con_fill1", "con_end2a",
                    "con_start2", "con_end1a", "con_fill1a", "con_end2", "set_pc_c1", "set_pc_c2", "set_pc_c3",
                    "con_start1", "con_end1", "con_fill1", "con_fill2", "con_fill1a", "con_fill2a",
#4
                    "wall_end1", "alley10", "steps_end1a", "steps_fill1a", "steps_fill2a", "steps_end2a",
                    "flats_alley1", "steps_end1", "steps_end2", "flats_alley1",  "flats_end1a", "steps_fill2",
                    "steps_fill1", "flats_end2a", "flats_alley2", "set_pc_d1", "set_pc_d2", "set_pc_d3", "steps_end2a"]

fullscreen_black_bmp = pygame.Surface((WIDTH, HEIGHT))
fullscreen_black_bmp.fill((0, 0, 0))


# Utility functions

def clamp(value, min_val, max_val):
    # Clamp a value within a given range
    return min(max(value, min_val), max_val)

def remap(old_val, old_min, old_max, new_min, new_max):
    # todo explain
    return (new_max - new_min)*(old_val - old_min) / (old_max - old_min) + new_min

def remap_clamp(old_val, old_min, old_max, new_min, new_max):
    # todo explain
    # These first two lines are in case new_min and new_max are inverted
    lower_limit = min(new_min, new_max)
    upper_limit = max(new_min, new_max)
    return min(upper_limit, max(lower_limit, remap(old_val, old_min, old_max, new_min, new_max)))

def sign(x):
    # Returns 1, 0 or -1 depending on whether number is positive, zero or negative
    if x == 0:
        return 0
    else:
        return -1 if x < 0 else 1

def move_towards(n, target, speed):
    # Returns new value, and the direction of travel (-1, 0 or 1)
    if n < target:
        return min(n + speed, target), 1
    elif n > target:
        return max(n - speed, target), -1
    else:
        return n, 0

# ABC = abstract base class - a class which is only there to serve as a base class, not to be instantiated directly
class Controls(ABC):
    NUM_BUTTONS = 4

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
            return keyboard.space or keyboard.z or keyboard.lctrl   # punch
        elif button == 1:
            return keyboard.x or keyboard.lalt      # kick
        elif button == 2:
            return keyboard.c or keyboard.lshift    # elbow
        elif button == 3:
            return keyboard.a   # flying kick

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
            print("Warning: main controller does not have enough buttons!")
            return False
        return self.joystick.get_button(button) != 0

class Attack:
    def __init__(self, sprite=None, strength=None, anim_time=None, frame_time=5, frames=0, hit_frames=(),
                 recovery_time=0, reach=80, throw=False, grab=False, combo_next=None, flyingkick=False,
                 stamina_cost=10, rear_attack=False, stamina_damage_multiplier=1, stun_time_multiplier=1, initial_sound=None, hit_sound=None):
        # Some data for attacks loaded from attacks.json must be modified to be in the format the game expects
        # For example, the keys in combo_next should be integers, but are strings in the json file as JSON only allows
        # string keys.
        if combo_next is not None:
            combo_next = {int(key):value for (key,value) in combo_next.items()}

        self.sprite = sprite
        self.strength = strength
        self.recovery_time = recovery_time  # Can't attack for this many frames after attack animation finishes
        self.anim_time = anim_time      # Frames for which animation plays, this allows us to stay on the last frame longer than previous frames
        self.frame_time = frame_time    # Frames for which each animation frame plays
        self.frames = frames            # Number of frames in animation
        self.hit_frames = hit_frames    # frames on which an opponent can be hit by this attack
        self.reach = reach              # Opponent must be closer than this for attack to hit
        self.throw = throw              # Is this an attack where we throw something, such as a barrel or the player?
        self.grab = grab                # Is this the attack where the boss grabs the player and throws him?
        self.combo_next = combo_next
        self.flying_kick = flyingkick
        self.stamina_cost = stamina_cost
        self.rear_attack = rear_attack
        self.stamina_damage_multiplier = stamina_damage_multiplier  # Does this attack do additional damage to the opponent's stamina?
        self.stun_time_multiplier = stun_time_multiplier
        self.initial_sound = initial_sound
        self.hit_sound = hit_sound

# Load attack data from file
with open("attacks.json") as attacks_file:
    ATTACKS = json.load(attacks_file)
    for key, value in ATTACKS.items():
        # Turn values in the dictionary into constructor parameters of the Attack class
        ATTACKS[key] = Attack(**value)

# The ScrollHeightActor class extends Pygame Zero's Actor class by providing the attribute 'vpos', which stores the object's
# current position using Pygame's Vector2 class. All code should change or read the position via vpos, as opposed to
# Actor's x/y or pos attributes. When the object is drawn, we set self.pos (equivalent to setting both self.x and
# self.y) based on vpos, but taking scrolling into account.
# It also includes the attribute height_above_ground which allows an actor to be considered to be in the air. This
# should be taken into account when determining draw order, as a fighter who is jumping will be further up the screen
# on the Y axis than if they were on the ground, but it's their Y position in relation to the ground which should
# determine whether they're drawn behind or in front of other actors. todo reword
class ScrollHeightActor(Actor):
    def __init__(self, img, pos, anchor=None, separate_shadow=False):
        super().__init__(img, pos, anchor=anchor)
        self.vpos = Vector2(pos)
        self.height_above_ground = 0
        if separate_shadow:
            self.shadow_actor = Actor("blank", pos, anchor=anchor)
        else:
            self.shadow_actor = None

    # We draw with the supplied Vector2 offset to enable scrolling
    def draw(self, offset):
        # Draw shadow first, if we are using a separate shadow sprite (most have the shadow as part of the sprite
        # but for player it is separate)
        if self.shadow_actor is not None:
            self.shadow_actor.pos = (self.vpos.x - offset.x, self.vpos.y - offset.y)
            self.shadow_actor.image = "blank" if self.image == "blank" else self.image + "_shadow"
            self.shadow_actor.draw()

        # Set Actor's screen pos
        self.pos = (self.vpos.x - offset.x, self.vpos.y - offset.y - self.height_above_ground)
        super().draw()
        if DEBUG_SHOW_ANCHOR_POINTS:
            screen.draw.circle(self.pos, 5, (255,255,255))

    def on_screen(self):
        # Use self.x rather than self.vpos.x to get actual screen position rather than world position
        # Note that self.x only updates when the actor is drawn, so if vpos.x is updated during update causing the
        # actor to move off-screen, the value returned by this method will not update until the following frame
        return 0 < self.x < WIDTH

    def get_draw_order_offset(self):
        # See Player and Stick classes for explanation
        return 0

# Inherits from both ScrollActor and ABC (abstract base class)
class Fighter(ScrollHeightActor, ABC):
    WEAPON_HOLD_HEIGHT = 100

    class FallingState(Enum):
        STANDING = 0
        FALLING = 1
        GETTING_UP = 2
        GRABBED = 3
        THROWN = 4

    def log(self, str):
        if DEBUG_LOGGING_ENABLED:
            l = f"{game.timer} {str} {self.vpos}"
            print(self, l)
            self.logs.append(l)

    def __init__(self, pos, anchor, speed, sprite, health, anim_update_rate=8, stamina=500, half_hit_area=Vector2(25, 20), lives=1, colour_variant=None, separate_shadow=False, hit_sound=None):
        super().__init__("blank", pos, anchor, separate_shadow=separate_shadow)

        # Speed is a Vector2 containing x and y speed
        self.speed = speed

        # e.g. "hero" or "enemy"
        self.sprite = sprite

        self.anim_update_rate = anim_update_rate

        self.facing_x = 1

        # Updates each game frame, then is translated into an animation frame number depending on the animation
        # being played
        self.frame = 0

        # Last attack is current attack if attack_timer is above zero
        self.last_attack = None

        # Above zero = currently attacking, zero or below = time since last attack
        self.attack_timer = 0

        # Are we knocked down or in the process of being knocked down?
        self.falling_state = Fighter.FallingState.STANDING

        # Are we currently walking? Used to determine whether to use standing or walking animation
        self.walking = False

        self.vel = Vector2(0, 0)  # Velocity X used when falling or being pushed backwards or for flying kick, velocity Y for jumping

        self.pickup_animation = None

        self.hit_timer = 0      # if above 0, we've just been hit and are doing the animation where we recoil from that
        self.hit_frame = 0

        self.stamina = stamina
        self.max_stamina = stamina

        # Determines whether an opponent's attack will hit us, based on the distance between us and the attack's reach
        # Larger number for the portal, because the portal is physically bigger
        self.half_hit_area = half_hit_area

        self.health = health
        self.start_health = health
        self.lives = lives

        # Used for enemies with multiple colour variants - appended to sprite name
        self.colour_variant = colour_variant

        self.hit_sound = hit_sound

        self.weapon = None

        # Used for animation where Scooterboy enemy is knocked off his scooter
        self.just_knocked_off_scooter = False

        self.use_die_animation = False

        self.logs = []

    def update(self):
        self.attack_timer -= 1

        # Apply gravity and velocity if in air
        if self.height_above_ground > 0 or self.vel.y != 0:
            self.vpos.x += self.vel.x
            self.vel.y += THROWN_GRAVITY if self.falling_state == Fighter.FallingState.THROWN else JUMP_GRAVITY
            self.height_above_ground -= self.vel.y
            self.apply_movement_boundaries(self.vel.x, 0)
            if self.height_above_ground < 0:
                self.height_above_ground = 0
                self.vel.x = 0
                self.vel.y = 0

                # Don't do the been hit animation after landing (from flying kick or from being thrown)
                self.hit_timer = 0

        # Update logic and animation based on current situation - falling, getting up, hit, pickup animation, or normal
        # walking/standing/attacking

        # Check for falling and dying
        # Portals don't fall when they die, so the logic for them dying is within their class
        if self.falling_state == Fighter.FallingState.FALLING:
            # Get pushed backwards
            self.vpos.x += self.vel.x
            self.vel.x, _ = move_towards(self.vel.x, 0, 0.5)

            self.apply_movement_boundaries(self.vel.x, 0)

            self.frame += 1

            if self.frame > 120:
                # If we're not yet out of health, get up and reset stamina
                if self.health > 0:
                    self.falling_state = Fighter.FallingState.GETTING_UP
                    self.frame = 0
                    self.stamina = self.max_stamina
                else:
                    # If we're out of health, flash on and off for a short while, then lose a life
                    if self.frame > 240:
                        self.lives -= 1

                        # If we still have lives left, get up
                        if self.lives > 0:
                            self.health = self.start_health
                            self.falling_state = Fighter.FallingState.GETTING_UP
                            self.frame = 0
                            self.stamina = self.max_stamina
                            self.use_die_animation = False
                        else:
                            self.died()

        elif self.falling_state == Fighter.FallingState.GETTING_UP:
            self.frame += 1
            self.vpos.x += 0.1 * self.facing_x     # Move forward slightly as we get up
            if self.frame > 20:
                self.falling_state = Fighter.FallingState.STANDING
                self.frame = 0

        elif self.falling_state == Fighter.FallingState.THROWN:
            self.frame += 1
            if self.height_above_ground <= 0:
                self.falling_state = Fighter.FallingState.FALLING
                self.frame = 80

        elif self.hit_timer > 0:
            # Playing the 'hit' animation, briefly stunned
            self.hit_timer -= 1

        elif self.pickup_animation is not None:
            # Doing animation for picking up a weapon
            self.frame += 1
            if self.frame > 30:
                self.pickup_animation = None

        elif self.override_walking():
            # If this is the case, we're in some kind of special state, managed by a subclass, which means we shouldn't
            # do the usual walking/attacking behaviour below - e.g. Scooterboy riding scooter
            pass

        elif self.falling_state == Fighter.FallingState.STANDING:
            # Standing, walking or attacking

            # Recover stamina over time
            if self.stamina < self.max_stamina:
                self.stamina += 1

            # Update position of held weapon
            # The weapon actor is invisible while being held as we switch to a different fighter sprite using the
            # weapon, but we update weapon pos so that if we drop the weapon, it reappears as a distinct sprite in the
            # correct location
            if self.weapon is not None:
                self.weapon.vpos = self.vpos + Vector2(self.facing_x * 20, 0)

            # Are we ready to attack or pick up/drop a weapon?
            # If we're out of stamina, recovery time will be longer
            last_attack_recovery_time = 0 if not self.last_attack else self.last_attack.recovery_time
            if self.stamina <= 0:
                last_attack_recovery_time *= 3
            if self.attack_timer <= -last_attack_recovery_time:
                # Not currently attacking, do we want to start attacking?

                # Before deciding if we want to attack - do we instead want to pick up or drop a weapon?
                if self.weapon is None:
                    # Find weapons within reach
                    nearby_weapons = [weapon for weapon in game.weapons if (weapon.vpos - self.vpos).length() < 50]
                    if len(nearby_weapons) > 0:
                        if self.determine_pick_up_weapon():
                            # Sort nearby weapons by distance. length_squared is used to order them instead of
                            # length as it is more efficient
                            nearby_weapons.sort(key=lambda weapon: (weapon.vpos - self.vpos).length_squared())
                            for weapon in nearby_weapons:
                                if weapon.can_be_picked_up():
                                    self.pickup_animation = weapon.name
                                    self.frame = 0
                                    self.weapon = weapon
                                    weapon.pick_up(Fighter.WEAPON_HOLD_HEIGHT)
                                    break
                else:
                    # Drop weapon?
                    if self.determine_drop_weapon():
                        self.drop_weapon()

                # Attack? Only allow if we didn't just start picking up a weapon!
                if self.pickup_animation is None:
                    attack = self.determine_attack()
                    if attack is not None:
                        self.log("Attack " + attack.sprite)
                        self.last_attack = attack
                        self.attack_timer = attack.anim_time
                        self.stamina -= attack.stamina_cost
                        self.stamina = max(self.stamina, MIN_STAMINA)
                        self.frame = 0

                        if attack.initial_sound is not None:
                            # * = unpack the elements of the tuple (sound to play, and number of variations) into
                            # arguments to pass to play_sound
                            game.play_sound(*attack.initial_sound)

                        # Is this a flying kick?
                        if attack.flying_kick:
                            self.vel.x = FLYING_KICK_VEL_X * self.facing_x
                            self.vel.y = FLYING_KICK_VEL_Y

                        # Grab player?
                        if attack.grab:
                            game.player.grabbed()

            # Update movement and animation, and pick up a weapon if desired
            # Must check attack_timer again as an attack may only just have started during the previous block of code
            if self.attack_timer <= 0:
                # Not attacking
                # Update facing_x. If get_desired_facing returns None, leave facing_x as it is
                desired_facing = self.get_desired_facing()
                if desired_facing is not None:
                    self.facing_x = desired_facing

                target = self.get_move_target()
                if target != self.vpos:
                    self.walking = True

                    self.vpos.x, dx = move_towards(self.vpos.x, target.x, self.speed.x)
                    self.vpos.y, dy = move_towards(self.vpos.y, target.y, self.speed.y)

                    self.apply_movement_boundaries(dx, dy)

                    self.frame += 1

                else:
                    # No movement, reset frame to standing
                    self.walking = False
                    self.frame = 7  # Resetting frame to 7 rather than zero fixes an issue where it looks weird if you only walk for a fraction of a second
            else:
                # Currently attacking
                self.frame += 1

                frame = self.get_attack_frame()

                # If current frame of attack is a hit frame, inflict damage to enemies
                if frame in self.last_attack.hit_frames:
                    # Is this a throw attack?
                    if self.last_attack.throw:
                        # If the current attack is a grab attack, that means we're the boss throwing the player
                        if self.last_attack.grab:
                            # Throw the player, if we haven't already done that on a previous frame
                            if game.player.falling_state == Fighter.FallingState.GRABBED:
                                game.player.hit(self, self.last_attack)
                                game.player.thrown(self.facing_x)

                        # Otherwise it's a normal throw of a barrel - make sure we still have the weapon, might have
                        # released it on a previous frame!
                        elif self.weapon is not None:
                            self.weapon.throw(self.facing_x, self)
                            self.weapon = None

                    # Call attack regardless of whether this is a throw attack, this fixes an issue where the barrel
                    # doesn't hit opponents because the position it's in when it's released is already past them
                    self.attack(self.last_attack)

    def attack(self, attack):
        # See if there is an opponent directly in front of us who we can hit (or behind us if it's a rear attack
        # such as elbow)
        if attack.strength > 0:
            # Loop through all opponents to see which (if any) this attack should hit
            for opponent in self.get_opponents():
                vec = opponent.vpos - self.vpos
                facing_correct = sign(self.facing_x) == sign(vec.x)
                if attack.rear_attack:
                    facing_correct = not facing_correct

                if DEBUG_SHOW_ATTACKS:
                    debug_rect = Rect(self.x - (attack.reach if self.facing_x == -1 else 0), self.y - 5, attack.reach, 10)
                    debug_drawcalls.append(lambda: screen.draw.filled_rect(debug_rect, (255, 0, 0)))

                # Should attack hit this opponent?
                if abs(vec.y) < opponent.half_hit_area.y and facing_correct and abs(vec.x) < attack.reach + opponent.half_hit_area.x:
                    opponent.hit(self, attack)

                    # If we're using a weapon, it may have broken as a result of being used
                    if self.weapon is not None and self.weapon.is_broken():
                        self.drop_weapon()

    def hit(self, hitter, attack):
        # Hitter can be another fighter, or a weapon such as a barrel
        # Can't be hit if we're falling/getting up
        if self.falling_state == Fighter.FallingState.STANDING or self.falling_state == Fighter.FallingState.GRABBED:
            # Can't be hit if we're already in the hit animation
            if self.hit_timer <= 0:
                self.stamina -= attack.strength * BASE_STAMINA_DAMAGE_MULTIPLIER * attack.stamina_damage_multiplier
                self.stamina = max(self.stamina, MIN_STAMINA)
                self.health -= attack.strength

                # Hit timer ensures we can't receive damage again until it's counted down, and stuns the fighter
                # Stronger attacks stun for longer
                self.hit_timer = attack.strength * 8 * attack.stun_time_multiplier
                self.hit_frame = randint(0, 1)

                # Stop our attack if we're in the middle of one - unless it's a flying kick, in which case continue.
                # Code elsewhere will ensure we don't do the 'been hit' animation at the end of a flying kick
                if self.attack_timer > 0 and (self.last_attack is not None and not self.last_attack.flying_kick):
                    self.attack_timer = 0

                # Drop weapon
                if self.weapon is not None:
                    self.drop_weapon()

                if attack.hit_sound is not None:
                    # * = unpack the elements of the tuple (sound to play, and number of variations) into
                    # arguments to pass to play_sound
                    game.play_sound(*attack.hit_sound)

                if self.hit_sound is not None:
                    # Sound for me being hit (only used by portal)
                    game.play_sound(self.hit_sound)

                # Check for being knocked down due to being out of health or stamina
                # Portals can't fall
                if (self.stamina <= 0 or self.health <= 0) and not isinstance(self, EnemyPortal):
                    self.falling_state = Fighter.FallingState.FALLING
                    self.frame = 0
                    self.hit_timer = 0

                    # If we're knocked down due to being out of stamina, and we're close to death, just die already
                    if self.health < 3:
                        self.health = 0
                        self.use_die_animation = (randint(0,1) == 0)    # Use die animation 50% of the time

                # If the attacker was using a weapon, tell the weapon that it was used
                # Must check that hitter is a Fighter, as it might be a barrel!
                if isinstance(hitter, Fighter) and hitter.weapon is not None:
                    hitter.weapon.used()

            # Always face towards hitter
            # First check to make sure that hitter and I aren't at the same X position
            if hitter.vpos.x != self.vpos.x:
                self.facing_x = sign(hitter.vpos.x - self.vpos.x)

                if self.falling_state == Fighter.FallingState.FALLING and not self.use_die_animation:
                    # Get knocked backwards
                    self.vel.x += -self.facing_x * 10

    def died(self):
        # Called when out of lives, can be overridden in cases where subclasses need to know that - e.g.
        # EnemyHoodie may drop stick on death
        pass

    def draw(self, offset):
        # Determine sprite to use based on our current action
        self.image = self.determine_sprite()

        super().draw(offset)

        if DEBUG_SHOW_HEALTH_AND_STAMINA:
            text = f"HP: {self.health}\nSTM: {self.stamina}"
            screen.draw.text(text, fontsize=24, center=(self.x, self.y - 200), color="#FFFFFF", align="center")

        if DEBUG_SHOW_HIT_AREA_WIDTH:
            screen.draw.rect(Rect(self.x - self.half_hit_area.x, self.y - self.half_hit_area.y, self.half_hit_area.x * 2, self.half_hit_area.y * 2), (255,255,255))

        if DEBUG_SHOW_LOGS:
            y = self.y
            for l in reversed(self.logs):
                screen.draw.text(l, fontsize=14, center=(self.x, y), color="#FFFFFF", align="center")
                y += 10

    def determine_sprite(self):
        show = True

        if self.falling_state == Fighter.FallingState.FALLING:
            if self.frame > 60 and self.health <= 0 and (self.frame // 10) % 2 == 0:
                # If we're out of health, flash on and off for a short while
                show = False

            if show:
                # When we fall down, we stay on the last frame (2) for an extended period
                # If we've only just fallen off a scooter, play knocked_off frame 0 before
                # continuing from knockdown frame 1
                if self.just_knocked_off_scooter:
                    # Check if we need to transition to the knockdown stage of the animation
                    if self.frame > 10:
                        self.just_knocked_off_scooter = False

                        # Create the scooter as an independent object
                        game.scooters.append(Scooter(self.vpos, self.facing_x, self.colour_variant))

                # Now choose the sprite to use this frame
                if self.just_knocked_off_scooter:
                    anim_type = "knocked_off"
                    frame = 0
                elif self.use_die_animation:
                    anim_type = "die"
                    frame = min(self.frame // 20, 2)
                else:
                    last_frame = 3 if isinstance(self, EnemyScooterboy) else 2
                    anim_type = "knockdown"
                    frame = min(self.frame // 10, last_frame)

        elif self.falling_state == Fighter.FallingState.GETTING_UP:
            anim_type = "getup"
            frame = min(self.frame // 10, 1)

        elif self.falling_state == Fighter.FallingState.GRABBED:
            show = False

        elif self.falling_state == Fighter.FallingState.THROWN:
            anim_type = "thrown"
            frame = min(self.frame // 12, 3)

        elif self.hit_timer > 0:
            frame = self.hit_frame
            anim_type = "hit"

        elif self.pickup_animation is not None:
            # Doing animation for picking up a weapon
            frame = min(self.frame // 12, self.weapon.end_pickup_frame)
            anim_type = f"pickup_{self.pickup_animation}"

        elif self.attack_timer > 0:
            # Currently attacking
            anim_type = self.last_attack.sprite
            frame = self.get_attack_frame()

        else:
            # Walking or standing
            if self.walking:
                # There are four walk animation frames, we take self.frame (an unbounded number incrementing by 1 each
                # game frame) and divide it by self.anim_update_rate (giving that many frames of delay between
                # switching animation frames), the result of that is MODded 4 to reduce it to the actual animation
                # frame to use in the range 0-3
                anim_type = "walk"
                frame = (self.frame // self.anim_update_rate) % 4  # 4 frames of walking animation
            else:
                # Standing
                frame = 0
                # Use anim_type stand or walk depending on whether we have a weapon - we only have 'walk' sprites
                # for weapons
                anim_type = "walk" if self.weapon is not None else "stand"

            # Add the weapon name to the walking/standing animation
            # This isn't done for weapon attack animations, because barrel is released during the throw animation
            anim_type += ("_" + self.weapon.name) if self.weapon is not None else ""

        if show:
            # In sprite filenames, 0 = facing left, 1 = right
            facing_id = 1 if self.facing_x == 1 else 0
            image = f"{self.sprite}_{anim_type}_{facing_id}_{frame}"
            if self.colour_variant is not None:
                image += "_" + str(self.colour_variant)
        else:
            image = "blank"

        return image

    def get_attack_frame(self):
        # return value of this function is an animation frame, e.g. we are on the third frame of the punch animation
        # self.frame is a game frame, increasing by 1 every 1/60th of a second
        # We use self.last_attack to get the current attack that we're doing, i.e. it's the last attack we started
        # doing, and we're still doing it
        frame = (self.frame // self.last_attack.frame_time)
        frame = min(frame, self.last_attack.frames - 1)
        return frame

    def override_walking(self):
        # Used by subclasses to prevent the usual walking/attacking behaviour
        return False

    def drop_weapon(self):
        self.pickup_animation = None    # Stop pickup animation if we're in the middle of one
        self.weapon.dropped()
        self.weapon = None

    def grabbed(self):
        self.log("Grabbed")
        self.falling_state = Fighter.FallingState.GRABBED
        if self.weapon is not None:
            self.drop_weapon()

    def thrown(self, dir_x):
        self.log("Thrown")
        self.falling_state = Fighter.FallingState.THROWN
        self.vel.x = dir_x * PLAYER_THROW_VEL_X
        self.vel.y = PLAYER_THROW_VEL_Y
        self.facing_x = -dir_x

        # Shift position for throw animation
        self.vpos.x += dir_x * 50
        self.height_above_ground = 45

    def apply_movement_boundaries(self, dx, dy):
        # A fighter outside the boundary can walk in a direction which will help them get inside the boundary, but not
        # in the direction that will take them further out of it
        if dx < 0 and self.vpos.x < game.boundary.left:
            self.vpos.x = game.boundary.left
        elif dx > 0 and self.vpos.x > game.boundary.right:
            self.vpos.x = game.boundary.right
        if dy < 0 and self.vpos.y < game.boundary.top:
            self.vpos.y = game.boundary.top
        elif dy > 0 and self.vpos.y > game.boundary.bottom:
            self.vpos.y = game.boundary.bottom

    # Every class that inherits from Fighter must implement each of the following abstract methods

    @abstractmethod
    def determine_attack(self):
        pass

    @abstractmethod
    def determine_pick_up_weapon(self):
        pass

    @abstractmethod
    def determine_drop_weapon(self):
        pass

    @abstractmethod
    def get_opponents(self):
        pass

    @abstractmethod
    def get_move_target(self):
        pass

    @abstractmethod
    def get_desired_facing(self):
        pass

class Player(Fighter):
    def __init__(self, controls):
        # Anchor point just above bottom of sprite
        super().__init__(pos=(400, 400), anchor=("center",256), speed=Vector2(3,2), sprite="hero", health=30, lives=3, separate_shadow=True)
        self.controls = controls
        self.extra_life_timer = 0

    def update(self):
        super().update()

        self.extra_life_timer -= 1

        # Check for collecting powerups
        for powerup in game.powerups:
            if (powerup.vpos - self.vpos).length() < 30:
                powerup.collect(self)

    def draw(self, offset):
        super().draw(offset)
        # screen.draw.text(f"{self.vpos}", (0,0))
        # screen.draw.text(f"{self.vpos}", self.pos)

    def determine_attack(self):
        # Do we have a weapon?
        if self.weapon is not None:
            # Ensure we cannot attack during the pickup animation
            if self.pickup_animation is None and self.controls.button_pressed(0):
                return ATTACKS[self.weapon.name]

        elif self.controls.button_pressed(0):
            # in combo?
            if self.last_attack is not None and self.last_attack.combo_next is not None and self.attack_timer >= -30:
                # Get next attack in combo
                # 0 here represents button 0, ideally this code should be made more general, but in practice
                # the only combo we actually have is where you press button 0 three times to do a sequence of punches
                # ending in an uppercut
                if 0 in self.last_attack.combo_next:
                    return ATTACKS[self.last_attack.combo_next[0]]

            # Not in combo, just return default attack
            return ATTACKS["punch"]

        elif self.controls.button_pressed(1):
            return choice((ATTACKS["kick"], ATTACKS["highkick"]))

        elif self.controls.button_pressed(2):
            return ATTACKS["elbow"]

        elif self.controls.button_pressed(3):
            return ATTACKS["flyingkick"]

        return None

    def determine_pick_up_weapon(self):
        return self.controls.button_pressed(0)

    def determine_drop_weapon(self):
        return self.weapon is not None and self.controls.button_pressed(1)

    def get_opponents(self):
        return game.enemies

    def get_move_target(self):
        # Our target position is our current position offset based on control inputs and speed
        return self.vpos + Vector2(self.controls.get_x() * self.speed.x, self.controls.get_y() * self.speed.y)

    def get_desired_facing(self):
        dx = self.controls.get_x()
        if dx != 0:
            self.facing_x = sign(dx)
        else:
            # Keep facing same direction as before if no X input
            return self.facing_x

    def get_draw_order_offset(self):
        # Consider player to be in front of another object with the same Y pos
        return 1

    def gain_extra_life(self):
        self.lives += 1
        self.extra_life_timer = 30

class Enemy(Fighter, ABC):
    # State is an inner class - a class within a class, so its name doesn't clash with the global class State
    class State(Enum):
        APPROACH_PLAYER = 0
        GO_TO_POS = 1
        GO_TO_WEAPON = 2
        PAUSE = 3
        KNOCKED_DOWN = 4
        RIDING_SCOOTER = 5
        PORTAL = 6
        PORTAL_EXPLODE = 7

    def __init__(self, pos, name, attacks, start_timer,
                 speed=Vector2(1, 1),
                 health=15,
                 stamina=500,
                 approach_player_distance=ENEMY_APPROACH_PLAYER_DISTANCE,
                 anchor_y=256,
                 half_hit_area=Vector2(25, 20),
                 colour_variant=None,
                 hit_sound=None,
                 score=10):
        # Slower animation speed than Hero
        super().__init__(pos, ("center",anchor_y), speed=speed, sprite=name, health=health, stamina=stamina,
                         anim_update_rate=14, half_hit_area=half_hit_area, colour_variant=colour_variant, hit_sound=hit_sound)

        # Target is a Vector2 instance
        # Must make a copy of the value, not a copy of the reference
        self.target = Vector2(self.vpos)

        self.target_weapon = None

        # Enemies don't try to target player until their start timer drops to zero
        # e.g. on starting a new stage we might not want them to start targeting the player until they have
        # scrolled onto the screen
        self.state = Enemy.State.PAUSE
        self.state_timer = start_timer

        self.attacks = attacks
        self.approach_player_distance = approach_player_distance
        self.score = score

    def spawned(self):
        # Called when the enemy is added into the game (when its stage is reached)
        pass

    def update(self):
        if self.state == Enemy.State.APPROACH_PLAYER:
            player = game.player

            # If player is attacking and we are quite close, chance (each frame) of backing up a little
            if player.attack_timer > 0 \
              and abs(self.vpos.y - player.vpos.y) < 20 \
              and abs(self.vpos.x - player.vpos.x) < 200 \
              and randint(0, 500) == 0:
                self.log("Back away from attack")
                self.target.x = self.vpos.x - self.facing_x * 90
                self.state = Enemy.State.GO_TO_POS
            else:
                # Head towards player
                # If we are holding a barrel, use a larger X offset so we throw from a distance
                if isinstance(self.weapon, Barrel):
                    x_offset = ENEMY_APPROACH_PLAYER_DISTANCE_BARREL
                else:
                    x_offset = self.approach_player_distance
                self.target.x = player.vpos.x + (x_offset * sign(self.vpos.x - player.vpos.x))
                self.target.y = player.vpos.y

        elif self.state == Enemy.State.GO_TO_POS:
            # In this state we just check to see if we've reached the target position, if so we make a new decision
            if self.target == self.vpos:
                self.make_decision()

        elif self.state == Enemy.State.GO_TO_WEAPON:
            if not self.target_weapon.can_be_picked_up() or not self.target_weapon.on_screen():
                # Weapon no longer available, make a new decision
                self.target_weapon = None
                self.make_decision()
            else:
                self.target = Vector2(self.target_weapon.vpos)
                if self.target == self.vpos:
                    # Arrived - pick up weapon and make new decision
                    self.log("Pick up weapon")
                    self.pickup_animation = self.target_weapon.name
                    self.frame = 0
                    self.target_weapon.pick_up(Fighter.WEAPON_HOLD_HEIGHT)
                    self.weapon = self.target_weapon
                    self.target_weapon = None
                    self.make_decision()

        elif self.state == Enemy.State.PAUSE:
            self.state_timer -= 1
            if self.state_timer < 0:
                self.make_decision()

        elif self.state == Enemy.State.KNOCKED_DOWN:
            # Check to see if we've got up again, if so switch state
            if self.falling_state == Fighter.FallingState.STANDING:
                self.make_decision()

        # Update of RIDING_SCOOTER state is in EnemyScooterboy class

        if self.state == Enemy.State.APPROACH_PLAYER \
                or self.state == Enemy.State.GO_TO_POS \
                or self.state == Enemy.State.GO_TO_WEAPON:
            # Ensure that target position is within the level boundary
            self.target.x = max(self.target.x, game.boundary.left)
            self.target.x = min(self.target.x, game.boundary.right)
            self.target.y = max(self.target.y, game.boundary.top)
            self.target.y = min(self.target.y, game.boundary.bottom)

            # Check to see if another enemy is already heading for the new target pos, or one very close to it.
            # If so, make a new decision
            other_enemies_same_target = [enemy for enemy in game.enemies if enemy is not self and
                                         (enemy.target - self.target).length() < 20]
            if len(other_enemies_same_target) > 0:
                self.log("Same target")
                self.make_decision()

        # Call through to Fighter class update
        super().update()

    def draw(self, offset):
        super().draw(offset)

        if DEBUG_SHOW_TARGET_POS:
            screen.draw.line(self.vpos - offset, self.target - offset, (255,255,255))

    def determine_attack(self):
        # Allow attacking if we're in APPROACH_PLAYER state, aligned with player on Y axis, both I and player are
        # standing up, and we're within the right range of distances on the X axis, finally a must pass a random chance
        # check of 1 in 20
        # If we're holding a barrel, can be within any distance on the X axis

        # Unpack player pos into more convenient variables
        px, py = game.player.vpos

        holding_barrel = isinstance(self.weapon, Barrel)

        if self.state == Enemy.State.APPROACH_PLAYER \
               and game.player.falling_state == Fighter.FallingState.STANDING \
               and self.vpos.y == py \
               and (self.approach_player_distance * 0.9 < abs(self.vpos.x - px) <= self.approach_player_distance * 1.1 or
                    holding_barrel) \
               and randint(0,19) == 0:
            if self.weapon is not None:
                return ATTACKS[self.weapon.name]
            else:
                chosen_attack = ATTACKS[choice(self.attacks)]

                # If the chosen attack is a grab, don't allow it if the player is currently doing a flying kick
                if chosen_attack.grab and game.player.last_attack is not None and game.player.last_attack.flying_kick:
                    return None

                return chosen_attack

    def determine_pick_up_weapon(self):
        return False

    def determine_drop_weapon(self):
        return False

    def get_opponents(self):
        return [game.player]

    def get_move_target(self):
        # Move towards player
        # Choose a location to walk to, depending on which side of the player we're on
        # We aim for a position 1 pixel above the player on the Y axis, so that we draw behind them
        # offset_x = 80 if self.vpos.x > game.player.vpos.x else -80
        # return game.player.vpos + Vector2(offset_x, -1)
        if self.target is None:
            # If no target, just return our current position
            return self.vpos
        else:
            #return self.target.get_pos()
            return self.target

    def get_desired_facing(self):
        # Always face towards player, unless we're on a scooter
        if self.state == Enemy.State.RIDING_SCOOTER:
            return self.facing_x
        else:
            return 1 if self.vpos.x < game.player.vpos.x else -1

    def hit(self, hitter, attack):
        if self.state == Enemy.State.KNOCKED_DOWN:
            # Already knocked down
            return

        super().hit(hitter, attack)

        # If we're riding a scooter, then getting hit will always cause us to fall, regardless of stamina
        if self.state == Enemy.State.RIDING_SCOOTER:
            self.falling_state = Fighter.FallingState.FALLING
            self.frame = 0
            self.hit_timer = 0
            self.just_knocked_off_scooter = True

        if self.falling_state == Fighter.FallingState.FALLING:
            # Set state as knocked down
            self.state = Enemy.State.KNOCKED_DOWN
            self.log("Knocked down")

    def make_decision(self):
        player = game.player

        # If we're not going for a weapon:
        # If we're the only enemy, always move in to attack
        if len(game.enemies) == 1:
            self.log("Only enemy, go to player")
            self.state = Enemy.State.APPROACH_PLAYER
        else:
            # 7/10 chance of going directly to a point where we can attack the player, unless there's another enemy
            # already heading there in which case flank
            # 3/10 chance of going to a random point slightly further from the player
            # 1/10 chance of pausing for a short time

            r = randint(0, 9)
            if r < 7:
                # Check to see if another enemy on the same X side of the player is already heading to attack them
                # If so, flank instead
                other_enemies_on_same_side_attacking = [enemy for enemy in game.enemies if enemy is not self
                                                        and enemy.state == Enemy.State.APPROACH_PLAYER
                                                        and sign(enemy.vpos.x - player.vpos.x) == sign(self.vpos.x - player.vpos.x)]
                if len(other_enemies_on_same_side_attacking) > 0:
                    # Go to opposite side of player, at a Y position offset from them but on the same Y side that
                    # we're on now (e.g. if we're below, stay below). If Y pos is same, choose Y side randomly.
                    self.log("Begin flanking (same target)")
                    self.state = Enemy.State.GO_TO_POS
                    self.target.x = player.vpos.x - sign(self.vpos.x - player.vpos.x) * 50
                    self.target.y = player.vpos.y + sign(self.vpos.y - player.vpos.y) * 50
                    if self.target.y == player.vpos.y:
                        self.target.y = player.vpos.y + choice((-1,1)) * 50
                else:
                    # Go to player
                    self.log("Go to player")
                    self.state = Enemy.State.APPROACH_PLAYER

            elif r < 9:
                # Go to a random point at a moderate distance from the player
                # Stick to same half of screen on X axis
                self.log("Go to distance from player")
                x_side = sign(self.vpos.x - player.vpos.x)
                if x_side == 0:
                    x_side = choice((1,-1))
                x1 = int(player.vpos.x + (150 * x_side))
                x2 = int(player.vpos.x + (400 * x_side))
                x = randint(min(x1,x2), max(x1,x2))
                y = randint(game.boundary.top, game.boundary.bottom)
                self.target = Vector2(x, y)
                self.state = Enemy.State.GO_TO_POS

            else:
                # Pause
                self.log("Pause")
                self.state_timer = randint(50, 100)
                self.state = Enemy.State.PAUSE

class EnemyVax(Enemy):
    def __init__(self, pos, start_timer=20):
        super().__init__(pos, "vax", ("vax_lpunch", "vax_rpunch", "vax_pound"), start_timer=start_timer, colour_variant=randint(0,2), score=20)

class EnemyHoodie(Enemy):
    def __init__(self, pos, start_timer=20):
        super().__init__(pos, "hoodie", ("hoodie_lpunch", "hoodie_rpunch", "hoodie_special"), health=12, speed=Vector2(1.2, 1), start_timer=start_timer, colour_variant=randint(0,2), score=20)

    def died(self):
        super().died()

        # Chance of dropping a stick
        if randint(0, 2) == 0:
            game.weapons.append(Stick(self.vpos))

class EnemyScooterboy(Enemy):
    SCOOTER_SPEED_SLOW = 4
    SCOOTER_SPEED_FAST = 12
    SCOOTER_ACCELERATION = 0.2

    def __init__(self, pos, start_timer=20):
        super().__init__(pos, "scooterboy", ("scooterboy_attack1",), start_timer=start_timer, approach_player_distance=ENEMY_APPROACH_PLAYER_DISTANCE_SCOOTERBOY, colour_variant=randint(0,2), score=30)
        self.state = Enemy.State.RIDING_SCOOTER
        self.scooter_speed = EnemyScooterboy.SCOOTER_SPEED_SLOW
        self.scooter_target_speed = self.scooter_speed
        self.scooter_sound_channel = None

    def spawned(self):
        super().spawned()
        try:
            self.scooter_sound_channel = pygame.mixer.find_channel()
            if self.scooter_sound_channel is not None:
                self.scooter_sound_channel.play(game.get_sound("scooter_slow"), loops=-1, fade_ms=200)
        except Exception as e:
            # Don't crash if no sound hardware
            pass

    def make_decision(self):
        # Scooterboy stays on scooter until knocked off
        if self.state != Enemy.State.RIDING_SCOOTER:
            super().make_decision()

    def determine_sprite(self):
        # Riding scooter is a state unique to Scooterboy, so it is dealt with here
        if self.state == Enemy.State.RIDING_SCOOTER:
            facing_id = 1 if self.facing_x == 1 else 0
            frame = 0
            if self.scooter_speed < self.scooter_target_speed:
                # Currently speeding up
                frame = min(self.frame // 5, 2)
            return f"{self.sprite}_ride_{facing_id}_{frame}_{self.colour_variant}"
        else:
            return super().determine_sprite()

    def update(self):
        if self.state == Enemy.State.RIDING_SCOOTER:
            player = game.player

            # Change volume independently on left and right speakers
            if self.scooter_sound_channel is not None:
                left_volume = remap_clamp(abs(self.vpos.x - player.vpos.x + 500), 0, 1000, 1, 0)
                right_volume = remap_clamp(abs(self.vpos.x - player.vpos.x - 500), 0, 1000, 1, 0)
                self.scooter_sound_channel.set_volume(left_volume, right_volume)

            # Currently accelerating/decelerating?
            if self.scooter_speed != self.scooter_target_speed:
                self.scooter_speed, _ = move_towards(self.scooter_speed, self.scooter_target_speed, EnemyScooterboy.SCOOTER_ACCELERATION)
                self.frame += 1
            elif self.on_screen() and randint(0,30) == 0:
                # If on screen, random chance of accelerating
                self.scooter_target_speed = EnemyScooterboy.SCOOTER_SPEED_FAST
                if self.scooter_sound_channel is not None:
                    self.scooter_sound_channel.play(game.get_sound("scooter_accelerate", 6), loops=0, fade_ms=200)
                self.frame = 0

            # Move forward
            self.target.x = self.vpos.x + self.facing_x * self.scooter_speed
            self.vpos.x = self.target.x

            # Turn around if we've gone off the edge of the screen
            # We check self.x which is the actual screen position as opposed to the position in the scrolling level
            if (self.facing_x > 0 and self.x > WIDTH + 200) or (self.facing_x < 0 and self.x < -200):
                self.facing_x = -self.facing_x
                self.target.y = player.vpos.y

                # If player is standing, move to the same Y position as player, otherwise choose a random Y position
                # which is not close to the player Y position (to avoid player getting stunlocked)
                if game.player.falling_state == Fighter.FallingState.STANDING:
                    self.vpos.y = self.target.y
                else:
                    while abs(self.vpos.y - self.target.y) < 40:
                        self.vpos.y = randint(MIN_WALK_Y, HEIGHT-1)

                # Also slow down if at high speed
                self.scooter_target_speed = EnemyScooterboy.SCOOTER_SPEED_SLOW
                self.scooter_speed = self.scooter_target_speed

                # Go back to slow sound
                if self.scooter_sound_channel is not None:
                    self.scooter_sound_channel.play(game.get_sound("scooter_slow"), loops=-1, fade_ms=200)

            # Check to see if we hit the player
            if player.falling_state == Fighter.FallingState.STANDING \
              and abs(player.vpos.y - self.vpos.y) < 30 \
              and abs(self.vpos.x - player.vpos.x) < 60 \
              and player.height_above_ground < 20:
                player.hit(self, ATTACKS["scooter_hit"])

        elif self.just_knocked_off_scooter and self.scooter_sound_channel is not None and self.scooter_sound_channel.get_busy():
            self.scooter_sound_channel.stop()

        super().update()

    def override_walking(self):
        return self.state == Enemy.State.RIDING_SCOOTER

    def died(self):
        super().died()

        # Low chance of dropping a chain
        if randint(0, 19) == 0:
            game.weapons.append(Chain(self.vpos))

        # Stop scooter sound - only needed for when we're skipping stages in debug mode
        if self.scooter_sound_channel is not None and self.scooter_sound_channel.get_busy():
            self.scooter_sound_channel.stop()

class EnemyBoss(Enemy):
    def __init__(self, pos, start_timer=20):
        super().__init__(pos, "boss", ("boss_lpunch", "boss_rpunch", "boss_kick", "boss_grab_player",),
                         speed=Vector2(0.9,0.8), health=25, stamina=1000, start_timer=start_timer, anchor_y=280,
                         half_hit_area=Vector2(30, 20), colour_variant=randint(0,2), score=75)

    def make_decision(self):
        # Boss can pick up a barrel, if they're not currently holding one
        # Look for a barrel we can walk to. Barrel must not be held by anyone else and must be on the screen
        if self.weapon is None:
            available_barrels = [weapon for weapon in game.weapons if isinstance(weapon, Barrel) and weapon.can_be_picked_up() and weapon.on_screen()]
            if len(available_barrels) > 0:
                # Find a weapon to go to
                for weapon in available_barrels:
                    # Don't go to a barrel if another enemy is already going to it
                    other_enemies_same_target = [enemy for enemy in game.enemies if enemy is not self and
                                                 enemy.target_weapon is weapon]
                    if len(other_enemies_same_target) == 0:
                        # This weapon is OK to go for
                        self.log("Go to weapon")
                        self.state = Enemy.State.GO_TO_WEAPON
                        self.target_weapon = weapon
                        return

        # If we didn't enter the GO_TO_WEAPON state, call the parent method
        super().make_decision()

class EnemyPortal(Enemy):
    GENERATE_ANIMATION_FRAMES = 6
    GENERATE_ANIMATION_DIVISOR = 16
    GENERATE_ANIMATION_TIME = GENERATE_ANIMATION_FRAMES * GENERATE_ANIMATION_DIVISOR

    def __init__(self, pos, enemies, spawn_interval, spawn_interval_change=0, max_spawn_interval=600, max_enemies=5, start_timer=90):
        # Hittable area is larger for portals
        super().__init__(pos, "portal", (), start_timer=start_timer, anchor_y=340, half_hit_area=Vector2(50, 50), hit_sound="portal_hit")
        self.enemies = enemies
        self.spawn_interval = spawn_interval
        self.spawn_timer = spawn_interval
        self.spawn_interval_change = spawn_interval_change
        self.max_spawn_interval = max_spawn_interval
        self.max_enemies = max_enemies
        self.spawning_enemy = None
        self.spawn_facing = 0

    def spawned(self):
        super().spawned()
        game.play_sound("portal_appear")

    def make_decision(self):
        # Like all enemies, portals start in the PAUSE state until their start_timer expires
        self.state = Enemy.State.PORTAL

    def determine_sprite(self):
        if self.state == Enemy.State.PAUSE and self.frame // 8 < 4:
            return "portal_grow_" + str(min(self.frame // 8, 3))
        elif self.state == Enemy.State.PORTAL_EXPLODE:
            return "portal_destroyed_" + str(min(self.frame // 6, 7))
        elif self.spawning_enemy is not None:
            # 3 frames of neutral generate animation, then 3 frames of animation for generating specific enemy
            frame = self.frame // EnemyPortal.GENERATE_ANIMATION_DIVISOR
            if frame < 3:
                return "portal_generate_" + str(frame)
            else:
                frame = min(frame - 3, 2)
                return f"portal_generate_{self.spawning_enemy.sprite}_{self.spawn_facing}_{frame}_{self.spawning_enemy.colour_variant}"

        elif self.hit_timer > 0:
            return "portal_hit_0"
        else:
            return "portal_idle_" + str((self.frame // 8) % 8)

    def update(self):
        self.frame += 1

        if self.state == Enemy.State.PORTAL:
            if self.health <= 0:
                self.state = Enemy.State.PORTAL_EXPLODE
                self.frame = 0
                game.play_sound("portal_destroyed")

            else:
                self.spawn_timer -= 1
                if self.spawn_timer <= 0 and self.spawning_enemy is not None:
                    # Animation complete, actually put the enemy in the level
                    game.spawn_enemy(self.spawning_enemy)

                    self.spawning_enemy = None

                    # Reset spawn timer, depending on spawn_interval_change we may spawn less frequently as time goes on
                    self.spawn_interval += self.spawn_interval_change
                    self.spawn_interval = min(self.spawn_interval, self.max_spawn_interval)
                    self.spawn_timer = self.spawn_interval

                elif self.spawning_enemy is None and self.spawn_timer <= EnemyPortal.GENERATE_ANIMATION_TIME:
                    if len(game.enemies) >= self.max_enemies:
                        # Too many enemies to spawn at the moment, try again in one second
                        self.spawn_timer = 60
                    else:
                        # Randomly choose an enemy to spawn from our enemies list
                        chosen_enemy = choice(self.enemies)

                        # Choose direction for spawned enemy to face (0/1 = left/right)
                        self.spawn_facing = 0 if self.vpos.x > game.player.vpos.x else 1

                        # Instantiate the enemy, but it won't appear in the level until the animation is complete
                        self.spawning_enemy = chosen_enemy(self.vpos)

                        # Reset frame for spawning animation
                        self.frame = 0

                        game.play_sound("portal_enemy_spawn")

        elif self.state == Enemy.State.PORTAL_EXPLODE:
            if self.frame > 50:
                self.lives -= 1
                self.died()

        super().update()

    def override_walking(self):
        # A portal never walks
        return True

# This is the scooter on its own, with the rider having been knocked off
class Scooter(ScrollHeightActor):
    def __init__(self, pos, facing_x, colour_variant):
        super().__init__("blank", pos, ("center",256))
        self.facing_x = facing_x
        self.colour_variant = colour_variant
        self.vel_x = -facing_x * 8
        self.frame = 0
        game.play_sound("scooter_fall")

    def update(self):
        self.frame += 1
        self.vpos.x += self.vel_x
        self.vel_x *= 0.94
        facing_id = 1 if self.facing_x > 0 else 0
        self.image = f"scooterboy_bike_{facing_id}_{min(self.frame // 30, 2)}_{self.colour_variant}"

    def get_draw_order_offset(self):
        return -1

class Weapon(ScrollHeightActor):
    def __init__(self, name, sprite, pos, end_pickup_frame, anchor=ANCHOR_CENTRE, bounciness=0, ground_friction=0.5, air_friction=0.996, separate_shadow=False):
        super().__init__(sprite, pos, anchor=anchor, separate_shadow=separate_shadow)
        self.name = name
        self.end_pickup_frame = end_pickup_frame
        self.held = False
        self.vel = Vector2(0,0)
        self.bounciness = bounciness
        self.ground_friction = ground_friction
        self.air_friction = air_friction

    def update(self):
        if not self.held:
            # If not held, check whether we're above the ground, or if we're moving
            if self.height_above_ground > 0 or self.vel.y != 0:
                # Fall to ground
                self.vel.y += WEAPON_GRAVITY
                if self.vel.y > self.height_above_ground:
                    # Bounce if we have bounciness, but stop bouncing if Y velocity is low
                    if self.bounciness > 0 and self.vel.y > 1:
                        # eg bounciness 1, height_above_ground 10, vel y 15, bounce amount should be 5
                        self.height_above_ground = abs(self.height_above_ground - self.vel.y) * self.bounciness
                        self.vel.y = -self.vel.y * self.bounciness
                        #print(f"{self.vel.y=}, {self.height_above_ground=}")
                    else:
                        self.height_above_ground = 0
                        self.vel.y = 0
                else:
                    # Didn't bounce - apply velocity to Y pos
                    self.height_above_ground -= self.vel.y

                assert(self.height_above_ground >= 0)

            self.vpos.x += self.vel.x

            # Friction on X axis, varies depending on whether we're on the ground or in the air
            friction = self.ground_friction if self.height_above_ground == 0 else self.air_friction
            self.vel.x *= friction
            if abs(self.vel.x) < 0.05:
                self.vel.x = 0

    def can_be_picked_up(self):
        return not self.held and self.height_above_ground == 0

    def pick_up(self, hold_height):
        assert(not self.held)
        self.held = True
        self.height_above_ground = hold_height   # for when we are dropped
        self.vel = Vector2(0, 0)
        self.image = "blank"

    def dropped(self):
        # Subclass has the responsibility of setting image to the correct sprite
        assert(self.held)
        self.held = False

    def used(self):
        pass

    def is_broken(self):
        return False

class Barrel(Weapon):
    def __init__(self, pos):
        super().__init__("barrel", "barrel_upright", pos, end_pickup_frame=2, anchor=("center", 190), bounciness=0.75, ground_friction=0.96, separate_shadow=True)
        self.last_thrower = None
        self.frame = 0

    def update(self):
        # Call parent update
        super().update()

        # If moving, look for people to bash into
        # Won't collide if it can be picked up (if it is moving slowly enough)
        if not self.held and not self.can_be_picked_up() and self.vel.x != 0:
            for fighter in [game.player] + game.enemies:
                # Won't collide with the person who threw it
                # Won't collide with a fighter who is falling (incl. lying on the ground)
                # Must be within 30 pixels on X axis
                # Must be within 30 pixels on Y axis (vpos.y doesn't take height above ground into account, so this
                # is effectively the character's 'depth' in the level)
                # Must hit within the height of the character, taking into account height_above_ground for both the
                # barrel and fighter. The fighter may be able to jump over the barrel. The Y anchor of fighter sprites
                # is at the feet and the Y anchor of the barrel is at its centre.
                # The barrel isn't able to bounce above the head of a fighter (unless we added a really short fighter),
                # so we don't need to check that
                BARREL_HEIGHT = 40
                fighter_bottom_height = fighter.height_above_ground
                barrel_bottom_height = self.height_above_ground - (BARREL_HEIGHT // 2)
                barrel_top_height = barrel_bottom_height + BARREL_HEIGHT

                if fighter is not self.last_thrower \
                  and fighter.falling_state == Fighter.FallingState.STANDING \
                  and abs(fighter.vpos.y - self.vpos.y) < 30 \
                  and abs(self.vpos.x - fighter.vpos.x) < 30 \
                  and fighter_bottom_height < barrel_top_height:
                    fighter.hit(self, ATTACKS["barrel"])

            # Update rolling animation
            facing_id = 1 if self.vel.x > 0 else 0
            self.frame += 1
            self.image = f"barrel_roll_{facing_id}_{(self.frame // 14) % 4}"

    def throw(self, dir_x, thrower):
        self.dropped()
        self.vel.x = dir_x * BARREL_THROW_VEL_X
        self.vel.y = BARREL_THROW_VEL_Y
        self.last_thrower = thrower

        # Shift position for throw animation
        self.vpos.x += dir_x * 104
        #self.height_above_ground += 54

    def dropped(self):
        super().dropped()
        self.image = "barrel_roll_0_0"

    def can_be_picked_up(self):
        return super().can_be_picked_up() and self.vel.length() < 1

    def get_draw_order_offset(self):
        # Consider barrel to be in front of another object with the same Y pos
        # (including player which has draw offset of 1)
        return 2

class BreakableWeapon(Weapon):
    def __init__(self, pos, name, durability):
        super().__init__(name, name, pos, end_pickup_frame=1, anchor=("center", "center"))
        self.break_counter = durability

    def dropped(self):
        super().dropped()
        self.image = self.name

    def get_draw_order_offset(self):
        # Used for stick/chain on ground. Default draw order means it is sometimes drawn on top of a character standing on
        # it, but changing Y anchor point also has some undesirable effects
        return -50

    def used(self):
        self.break_counter -= 1
        if self.break_counter == 0:
            self.on_break()

    def is_broken(self):
        return self.break_counter <= 0

    @abstractmethod
    def on_break(self):
        # Can't call this break as that's a keyword in Python!
        pass

class Stick(BreakableWeapon):
    def __init__(self, pos):
        super().__init__(pos, "stick", durability=randint(12, 16))

    def on_break(self):
        game.play_sound("stick_break")

class Chain(BreakableWeapon):
    def __init__(self, pos):
        super().__init__(pos, "chain", durability=randint(18, 25))

    def on_break(self):
        game.play_sound("chain_break")

class Powerup(ScrollHeightActor):
    def __init__(self, image, pos):
        super().__init__(pos, image)
        self.collected = False

    def update(self):
        pass

    @abstractmethod
    def collect(self, collector):
        self.collected = True

class HealthPowerup(Powerup):
    def __init__(self, pos):
        super().__init__(pos, "health_pickup")

    def collect(self, collector):
        super().collect(collector)

        # Add 20 health to the player who collected us, but don't go over their max health
        collector.health = min(collector.health + 20, collector.start_health)

        game.play_sound("health", 1)

class ExtraLifePowerup(Powerup):
    def __init__(self, pos):
        super().__init__(pos, "ingame_life9")
        self.timer = 0

    def update(self):
        super().update()
        self.timer += 1
        self.image = "ingame_life" + str((self.timer // 2) % 10)

    def collect(self, collector):
        super().collect(collector)

        collector.gain_extra_life()

        game.play_sound("health", 1)

# A stage consists of a group of enemies and a level X boundary. When the enemies are
# defeated, the next stage begins
class Stage:
    def __init__(self, enemies, max_scroll_x, weapons=[], powerups=[]):
        self.enemies = enemies
        self.powerups = powerups
        self.max_scroll_x = max_scroll_x
        self.weapons = weapons

def setup_stages():
    global STAGES
    STAGES = (
            # Stage(max_scroll_x=0, enemies=[]),

            # Stage(max_scroll_x=200,
            #       enemies=[],
            #       #enemies=[EnemyScooterboy(pos=(200, 400))],
            #       #enemies=[EnemyPortal(pos=(600, 400), enemies=(EnemyVax, EnemyHoodie), spawn_interval=60, spawn_interval_change=30)],
            #       #enemies=[EnemyScooterboy(pos=(200, 400)),EnemyScooterboy(pos=(100, 300)),EnemyScooterboy(pos=(300, 600)),EnemyScooterboy(pos=(200, 500)),],
            #       #enemies=[EnemyVax(pos=(200, 400)),EnemyVax(pos=(100, 300)),EnemyVax(pos=(300, 600)),EnemyVax(pos=(200, 500)),],
            #       #enemies=[EnemyBoss(pos=(500, 380))],
            #       weapons=[Barrel((300, 400))]
            #       ),

            # Stage(max_scroll_x=250,
            #       #enemies=[EnemyScooterboy(pos=(200, 400))],
            #       enemies=[EnemyPortal(pos=(600, 400), enemies=(EnemyVax, EnemyHoodie), spawn_interval=120, spawn_interval_change=30, start_timer=300)],
            #       #enemies=[EnemyScooterboy(pos=(200, 400)),EnemyScooterboy(pos=(100, 300)),EnemyScooterboy(pos=(300, 600)),EnemyScooterboy(pos=(200, 500)),],
            #       #enemies=[EnemyBoss(pos=(500, 380))],
            #       weapons=[Barrel((300, 400))]
            #       ),

            Stage(max_scroll_x=300,
                  enemies=[EnemyVax(pos=(1000,400))],
                  #weapons=[Barrel((300, 400))],
                  #powerups=[HealthPowerup(pos=(1100, MIN_WALK_Y)), ExtraLifePowerup(pos=(1000, MIN_WALK_Y))]
                  ),

            Stage(max_scroll_x=600,
                  enemies=[EnemyVax(pos=(1400,400)),
                           EnemyHoodie(pos=(1500,500))],
                  weapons=[Barrel((1600, 400))]),

            Stage(max_scroll_x=600,
                  enemies=[EnemyScooterboy(pos=(200,400))]),

            Stage(max_scroll_x=900,
                  enemies=[EnemyBoss(pos=(1800,400)),
                           EnemyVax(pos=(400,400))]),

            Stage(max_scroll_x=1400,
                  enemies=[EnemyHoodie(pos=(2100,380)),
                           EnemyHoodie(pos=(2100,480)),
                           EnemyHoodie(pos=(800,420))],
                  powerups=[HealthPowerup(pos=(2300, MIN_WALK_Y))]
                  ),

            Stage(max_scroll_x=1900,
                  enemies=[EnemyVax(pos=(2400,380)),
                           EnemyHoodie(pos=(2500,480)),
                           EnemyScooterboy(pos=(2800,400))]),

            Stage(max_scroll_x=2500,
                  enemies=[EnemyScooterboy(pos=(3800,380)),
                           EnemyScooterboy(pos=(3300,480)),
                           EnemyScooterboy(pos=(1200,400))]),

            Stage(max_scroll_x=3000,
                  enemies=[EnemyVax(pos=(4000,380)),
                           EnemyVax(pos=(3900,480)),
                           EnemyVax(pos=(4200,460)),
                           EnemyVax(pos=(4200,450)),
                           EnemyHoodie(pos=(3900,300)),
                           EnemyHoodie(pos=(3950,320))]),

            Stage(max_scroll_x=3600,
                  enemies=[EnemyVax(pos=(4600,380)),
                           EnemyScooterboy(pos=(1200,350)),
                           EnemyScooterboy(pos=(1400,350)),
                           EnemyScooterboy(pos=(1600,350)),
                           EnemyScooterboy(pos=(1800,350)),
                           EnemyScooterboy(pos=(2000,350))],
                  powerups=[HealthPowerup(pos=(5100, MIN_WALK_Y))]
                  ),

            Stage(max_scroll_x=4600,
                  enemies=[EnemyHoodie(pos=(4800,380)),
                           EnemyHoodie(pos=(4800,350)),
                           EnemyScooterboy(pos=(1200,350)),
                           EnemyScooterboy(pos=(1400,350)),
                           EnemyScooterboy(pos=(4800,350)),
                           EnemyScooterboy(pos=(4800,400)),
                           EnemyScooterboy(pos=(4900,450))]),

            Stage(max_scroll_x=5500,
                  enemies=[EnemyBoss(pos=(6500,380)),
                           EnemyBoss(pos=(6500,360))],
                  weapons=[Barrel(pos=(6000, 400)),
                           Barrel(pos=(5900, 370))]),

            Stage(max_scroll_x=6400,
                  enemies=[EnemyBoss(pos=(7000,380)),
                           EnemyBoss(pos=(7000,360)),
                           EnemyBoss(pos=(7000,390))],
                  weapons=[Barrel(pos=(7000, 380))]),

            Stage(max_scroll_x=6900,
                  enemies=[EnemyVax(pos=(7500,380)),
                           EnemyScooterboy(pos=(7500,350)),
                           EnemyScooterboy(pos=(7500,360))]),

            Stage(max_scroll_x=7550,
                  enemies=[EnemyHoodie(pos=(8000,380), start_timer=50),
                           EnemyVax(pos=(8200,340), start_timer=100),
                           EnemyHoodie(pos=(8200,340), start_timer=150),
                           EnemyHoodie(pos=(7900,360), start_timer=200),
                           EnemyHoodie(pos=(8300,390), start_timer=250),
                           EnemyVax(pos=(8700,400), start_timer=300),
                           EnemyHoodie(pos=(8800,400), start_timer=400),
                           EnemyHoodie(pos=(8900,400), start_timer=500),
                           EnemyVax(pos=(9000,320), start_timer=600),
                           EnemyVax(pos=(9100,400), start_timer=700),
                           EnemyHoodie(pos=(9100,450), start_timer=800),
                           EnemyVax(pos=(9100,420), start_timer=900),
                           EnemyBoss(pos=(9100,450), start_timer=1000),
                           ],
                  powerups=[HealthPowerup(pos=(8000, MIN_WALK_Y)),
                            ExtraLifePowerup(pos=(8200, MIN_WALK_Y))]
                  ),

            Stage(max_scroll_x=8400,
                  enemies=[EnemyPortal(pos=(8900, 400), enemies=(EnemyVax, EnemyHoodie), spawn_interval=120, spawn_interval_change=30, max_spawn_interval=250, max_enemies=2),],
                  # weapons=[Barrel(pos=(9000,380)),
                  #          Barrel(pos=(8900,360))
                  ),

            Stage(max_scroll_x=8900,
                  enemies=[EnemyPortal(pos=(9500, 400), enemies=(EnemyVax, EnemyHoodie), spawn_interval=120, spawn_interval_change=50, max_spawn_interval=250, max_enemies=5),
                           EnemyPortal(pos=(9500, 400), enemies=(EnemyScooterboy,), spawn_interval=160, spawn_interval_change=50, max_spawn_interval=250, max_enemies=5),],
                  # weapons=[Barrel(pos=(9000,380)),
                  #          Barrel(pos=(8900,360))
                  ),

            Stage(max_scroll_x=9600,
                  enemies=[EnemyPortal(pos=(10000, 420), enemies=(EnemyVax, EnemyHoodie), spawn_interval=120, spawn_interval_change=50, max_spawn_interval=250, max_enemies=5),
                           EnemyScooterboy(pos=(10500,320)),
                           EnemyScooterboy(pos=(10500,350)),
                           EnemyScooterboy(pos=(10500,380)),
                           ],
                  # weapons=[Barrel(pos=(9000,380)),
                  #          Barrel(pos=(8900,360))
                  ),

            Stage(max_scroll_x=10800,
                  enemies=[EnemyPortal(pos=(11200, 420), enemies=(EnemyHoodie,), spawn_interval=40, spawn_interval_change=10, max_spawn_interval=250, max_enemies=8),
                           ],
                  # weapons=[Barrel(pos=(9000,380)),
                  #          Barrel(pos=(8900,360))
                  ),

            Stage(max_scroll_x=11400,
                  enemies=[EnemyPortal(pos=(12100, 340), enemies=(EnemyScooterboy,), spawn_interval=40, spawn_interval_change=20, max_spawn_interval=250, max_enemies=8),
                           EnemyPortal(pos=(11900, 400), enemies=(EnemyScooterboy,), spawn_interval=50, spawn_interval_change=25, max_spawn_interval=250, max_enemies=8),
                           ],
                  weapons=[Barrel(pos=(11800,380))],
                  powerups=[HealthPowerup(pos=(12000, MIN_WALK_Y)),
                            HealthPowerup(pos=(12500, MIN_WALK_Y))]
                  ),

            Stage(max_scroll_x=12600,
                  enemies=[EnemyPortal(pos=(12900, 340), enemies=(EnemyBoss,), spawn_interval=240, spawn_interval_change=20, max_spawn_interval=300, max_enemies=4),
                           EnemyHoodie(pos=(13200,320)),
                           EnemyHoodie(pos=(13200,330)),
                           EnemyVax(pos=(13400,360)),
                           ],
                  ),

            Stage(max_scroll_x=13400,
                  enemies=[EnemyPortal(pos=(13600, 320), enemies=(EnemyVax,), spawn_interval=230, spawn_interval_change=20, max_spawn_interval=300, max_enemies=10),
                           EnemyPortal(pos=(13600, 435), enemies=(EnemyHoodie,), spawn_interval=240, spawn_interval_change=20, max_spawn_interval=300, max_enemies=10),
                           EnemyPortal(pos=(14000, 320), enemies=(EnemyScooterboy,), spawn_interval=250, spawn_interval_change=30, max_spawn_interval=300, max_enemies=10),
                           EnemyPortal(pos=(14000, 435), enemies=(EnemyBoss,), spawn_interval=260, spawn_interval_change=30, max_spawn_interval=300, max_enemies=10),
                          ],
                  ),

            Stage(max_scroll_x=14700,
                  enemies=[EnemyPortal(pos=(14900, 320), enemies=(EnemyVax,), spawn_interval=220, spawn_interval_change=20, max_spawn_interval=300, max_enemies=8),
                           EnemyPortal(pos=(14900, 435), enemies=(EnemyHoodie,), spawn_interval=230, spawn_interval_change=20, max_spawn_interval=300, max_enemies=8),
                           EnemyPortal(pos=(15300, 320), enemies=(EnemyScooterboy,), spawn_interval=240, spawn_interval_change=20, max_spawn_interval=300, max_enemies=8),
                           EnemyPortal(pos=(15300, 435), enemies=(EnemyBoss,), spawn_interval=250, spawn_interval_change=20, max_spawn_interval=300, max_enemies=8),
                          ],
                  powerups=[HealthPowerup(pos=(14650, 350)),]
                  ),

            Stage(max_scroll_x=15400,
                  enemies=[EnemyPortal(pos=(15800, 350), enemies=(EnemyVax,EnemyHoodie,EnemyScooterboy), spawn_interval=60, spawn_interval_change=20, max_spawn_interval=300, max_enemies=8),
                          ],
                  powerups=[HealthPowerup(pos=(16000, MIN_WALK_Y)),]
                  ),

            Stage(max_scroll_x=16600,
                  enemies=[EnemyVax(pos=(17600,300)),
                           EnemyVax(pos=(17900,320)),
                           EnemyVax(pos=(17600,340)),
                           EnemyVax(pos=(17900,360)),
                           EnemyVax(pos=(17600,380)),
                           EnemyVax(pos=(17900,400)),
                           EnemyVax(pos=(17600,420)),
                          ],
                  powerups=[HealthPowerup(pos=(17000, MIN_WALK_Y)),],
                  weapons=[Barrel(pos=(17000,380))],
                  ),

            Stage(max_scroll_x=17400,
                  enemies=[EnemyBoss(pos=(17800,MIN_WALK_Y)),
                           EnemyScooterboy(pos=(18500,380)),
                           EnemyScooterboy(pos=(18600,380)),
                           EnemyScooterboy(pos=(18700,380)),
                           EnemyScooterboy(pos=(18800,380)),
                           EnemyScooterboy(pos=(19000,380)),
                          ],
                  weapons=[Stick(pos=(18000,340))],
                  ),

            Stage(max_scroll_x=18500,
                  enemies=[EnemyBoss(pos=(18800, 320)),
                           EnemyPortal(pos=(18900, 390), enemies=(EnemyVax, EnemyHoodie),
                                       start_timer=400, spawn_interval=30, spawn_interval_change=5, max_enemies=10),
                           ],
             ),

            Stage(max_scroll_x=19300,
                  enemies=[EnemyScooterboy(pos=(19900, 340))],
                  weapons=[Barrel(pos=(19400,340))],
                  powerups=[HealthPowerup(pos=(19600, MIN_WALK_Y)),],
             ),

            # Final battles

            Stage(max_scroll_x=20500,
                  enemies=[EnemyHoodie(pos=(20900, 380), start_timer=500),
                           EnemyBoss(pos=(21500,330)),
                           EnemyBoss(pos=(21500,350)),
                           EnemyBoss(pos=(21500,370)),
                           EnemyBoss(pos=(21500,390)),
                           EnemyBoss(pos=(18200,320)),
                           EnemyBoss(pos=(17800,390)),
                           ],
                  powerups=[ExtraLifePowerup(pos=(20900, MIN_WALK_Y))]),

            Stage(max_scroll_x=20500,
                  enemies=[EnemyPortal(pos=(20700, 315), enemies=(EnemyVax,), start_timer=600, spawn_interval=60, spawn_interval_change=5, max_enemies=20),
                           EnemyPortal(pos=(20700, 440), enemies=(EnemyHoodie,), start_timer=600, spawn_interval=60, spawn_interval_change=10, max_enemies=20),
                           EnemyPortal(pos=(21100, 315), enemies=(EnemyScooterboy,), start_timer=600, spawn_interval=60, spawn_interval_change=15, max_enemies=20),
                           EnemyPortal(pos=(21100, 440), enemies=(EnemyBoss,), start_timer=600, spawn_interval=60, spawn_interval_change=20, max_enemies=20),
                           ]),

    )

class Game:
    def __init__(self, controls=None):
        self.player = Player(controls)

        self.enemies = []
        self.weapons = []
        self.scooters = []
        self.powerups = []

        self.stage_index = -1
        self.timer = 0
        self.score = 0

        self.scroll_offset = Vector2(0,0)
        self.max_scroll_offset_x = 0
        self.scrolling = False

        self.boundary = Rect(0, MIN_WALK_Y, WIDTH-1, HEIGHT-MIN_WALK_Y)

        setup_stages()

        # Set up intro text, selecting randomly from one of several stolen items
        stolen_items = ("A SHIPMENT OF RASPBERRY\nPIS",
                        "YOUR COPY OF CODE THE\nCLASSICS VOL 2",
                        "THE COMPLETE WORKS OF\nSHAKESPEARE",
                        "THE BLOCKCHAIN",
                        "THE WORLD'S ENTIRE SUPPLY\nOF COVID VACCINES",
                        "ALL OF YOUR SAVED GAME\nFILES",
                        "YOUR DOG'S FLEA MEDICINE")

        self.text_active = INTRO_ENABLED
        self.intro_text = "THE NOTORIOUS CRIME BOSS\nEBEN UPTON HAS STOLEN\n" \
                          + choice(stolen_items) \
                          + "\n\n\nFIGHT TO RECLAIM WHAT\nHAS BEEN TAKEN!"
        self.outro_text = "FOLLOWING THE DEFEAT OF\n" \
                          + "THE EVIL GANG, HUMANITY\n" \
                          + "ENTERED A NEW GOLDEN AGE\n" \
                          + "IN WHICH CRIME BECAME A\n" \
                          + "THING OF THE PAST. THE\n" \
                          + "WORD ITSELF WAS SOON\n" \
                          + "FORGOTTEN AND EVERYONE\n" \
                          + "HAD A BIG PARTY IN YOUR\n" \
                          + "HONOUR.\n" \
                          + "\nNICE JOB!"
        self.current_text = self.intro_text
        self.displayed_text = ""

    def next_stage(self):
        # A stage is over when we've scrolled to its max_scroll_x and there are no enemies left
        # Enemies are created when we start scrolling (or here, if no scrolling is to take place or is already taking place)
        self.stage_index += 1
        if self.stage_index < len(STAGES):
            stage = STAGES[self.stage_index]
            self.max_scroll_offset_x = stage.max_scroll_x
            if self.scrolling or self.max_scroll_offset_x <= self.scroll_offset.x:
                print("No scrolling or already scrolling - create stage objects")
                self.create_stage_objects(stage)
        else:
            # If stage_index has reached len(STAGES), we go into the outro state (like intro text, but with different text)
            # After that, check_won() will return True and the game state code will pick up on this and end the game
            if not self.text_active:
                self.text_active = True
                self.current_text = self.outro_text
                self.displayed_text = ""
                self.timer = 0

    def check_won(self):
        # Have we been through all stages, and has the outro text finished?
        return self.stage_index >= len(STAGES) and not self.text_active

    def create_stage_objects(self, stage):
        # Copy the enemies list from the stage, and tell them that they've been spawned
        self.enemies = stage.enemies.copy()
        for enemy in self.enemies:
            enemy.spawned()

        # Add the weapons and powerups from the stage to the game
        self.weapons.extend(stage.weapons)
        self.powerups.extend(stage.powerups)

    def spawn_enemy(self, enemy):
        # Called by Portal
        self.enemies.append(enemy)
        enemy.spawned()

    def update(self):
        if DEBUG_PROFILING:
            p = Profiler()

        self.timer += 1

        if self.text_active:
            # Every 6 frames, update the displayed text to display an extra character, and make a sound if the
            # new character is visible (as opposed to a space or new line)
            if self.timer % 6 == 0 and len(self.displayed_text) < len(self.current_text):
                length_to_display = min(self.timer // 6, len(self.current_text))
                self.displayed_text = self.current_text[:length_to_display]
                if not self.displayed_text[-1].isspace():
                    self.play_sound("teletype")

            # Allow player to skip/leave text
            for button in range(4):
                if self.player.controls.button_pressed(button):
                    self.text_active = False
                    self.timer = 0

            return

        if DEBUG_SHOW_ATTACKS:
            debug_drawcalls.clear()

        # Update all objects
        for obj in [self.player] + self.enemies + self.weapons + self.scooters + self.powerups:
            obj.update()

        if self.scrolling:
            if self.scroll_offset.x < self.max_scroll_offset_x:
                # How far are we from reaching the new max scroll offset?
                diff = self.max_scroll_offset_x - self.scroll_offset.x
                # Scroll at 1-4px per frame depending on player's distance from right edge
                scroll_speed = self.player.x / (WIDTH/4)
                scroll_speed = min(diff, scroll_speed)
                self.scroll_offset.x += scroll_speed
                self.boundary.left = self.scroll_offset.x  # as boundary is a rectangle, moving boundary.left moves the entire rectangle
            else:
                # Scrolling is complete
                self.scrolling = False
        else:
            # Start scrolling if player is near right hand edge of screen and max_scroll_offset_x allows to to scroll
            begin_scroll_boundary = WIDTH - 300
            if self.player.vpos.x - self.scroll_offset.x > begin_scroll_boundary and self.scroll_offset.x < self.max_scroll_offset_x:
                self.scrolling = True

                # When we start scrolling, create enemies for the current stage
                if self.stage_index < len(STAGES):
                    print("Started scrolling - create stage objects")
                    stage = STAGES[self.stage_index]
                    self.create_stage_objects(stage)

        # Remove expired enemies and gain score
        self.score += sum([enemy.score for enemy in self.enemies if enemy.lives <= 0])
        self.enemies = [enemy for enemy in self.enemies if enemy.lives > 0]

        # Remove expired scooters
        self.scooters = [scooter for scooter in self.scooters if scooter.frame < 200]

        # Remove broken weapons and ones which are off the left of the screen
        self.weapons = [weapon for weapon in self.weapons if not weapon.is_broken() and weapon.x > -200]

        # Remove collected powerups, and ones off the left of the screen
        self.powerups = [powerup for powerup in self.powerups if not powerup.collected and powerup.x > -200]

        # If no enemies and we've fully scrolled to the current stage's max_scroll_x, start the next stage
        if len(self.enemies) == 0 and self.scroll_offset.x == self.max_scroll_offset_x:
            self.next_stage()

        if DEBUG_PROFILING:
            print(f"update: {p.get_ms()}")

    def draw(self):
        # Draw background
        self.draw_background()

        # Draw all objects, lowest on screen first
        # Y pos used is modified by result of get_draw_order_offset, for certain cases where we need more nuance than
        # just "lowest on screen first"
        p = Profiler()
        all_objs = [self.player] + self.enemies + self.weapons + self.scooters + self.powerups
        all_objs.sort(key=lambda obj: obj.vpos.y + obj.get_draw_order_offset())
        for obj in all_objs:
            if obj:
                obj.draw(self.scroll_offset)
        if DEBUG_PROFILING:
            print("objs: {0}".format(p.get_ms()))

        p = Profiler()

        # If player can scroll the level, show flashing arrow
        if self.scroll_offset.x < self.max_scroll_offset_x and (self.timer // 30) % 2 == 0:
            screen.blit("arrow", (WIDTH-450, 120))

        self.draw_ui()

        if DEBUG_PROFILING:
            print("icons: {0}".format(p.get_ms()))
            p = Profiler()

        # During the intro we show a black background, immediately after the intro we fade it away
        # Draw a black image with gradually decreasing opacity
        # An alpha value of 255 is fully opaque, 0 is fully transparent
        if self.text_active or self.timer < 255:
            if self.text_active:
                alpha = 255
            else:
                alpha = max(0, 255 - self.timer)
            fullscreen_black_bmp.set_alpha(alpha)
            screen.blit(fullscreen_black_bmp, (0, 0))

        # Show intro text
        if self.text_active:
            draw_text(self.displayed_text, 50, 50)

        # Debug
        if DEBUG_SHOW_SCROLL_POS:
            screen.draw.text(f"{self.scroll_offset} {self.max_scroll_offset_x}", (0, 25))
            screen.draw.text(str(self.boundary.left), (0, 45))

        if DEBUG_SHOW_BOUNDARY:
            screen.draw.rect(Rect(self.boundary.left - self.scroll_offset.x, self.boundary.top, self.boundary.width, self.boundary.height), (255,255,255))

        for func in debug_drawcalls:
            if DEBUG_PROFILING:
                print(p.get_ms())
            func()

        if DEBUG_PROFILING:
            print("rest: {0}".format(p.get_ms()))

    def draw_ui(self):
        # Show status bar and player health, stamina and lives
        # Have to use the actual Pygame blit rather than Pygame Zero version so that we can specify which area of the
        # source image to copy
        health_bar_w = int((game.player.health / game.player.start_health) * HEALTH_STAMINA_BAR_WIDTH)
        screen.surface.blit(getattr(images, "health"), (48, 11), Rect(0, 0, health_bar_w, HEALTH_STAMINA_BAR_HEIGHT))
        stamina_bar_w = int((game.player.stamina / game.player.max_stamina) * HEALTH_STAMINA_BAR_WIDTH)
        screen.surface.blit(getattr(images, "stamina"), (517, 11), Rect(0, 0, stamina_bar_w, HEALTH_STAMINA_BAR_HEIGHT))

        screen.blit("status", (0, 0))

        for i in range(game.player.lives):
            if game.player.extra_life_timer <= 0 or i < game.player.lives - 1:
                sprite_idx = 9
            else:
                sprite_idx = min(9, (30 - game.player.extra_life_timer) // 3)

            screen.blit("status_life" + str(sprite_idx), (i * 46 - 55, -35))

        # Show score
        draw_text(f"{self.score:04}", WIDTH // 2, 0, True)

    def draw_background(self):
        # Draw two copies of road background
        p = Profiler()
        road1_x = -(self.scroll_offset.x % WIDTH)
        road2_x = road1_x + WIDTH
        screen.blit("road", (road1_x, 0))
        screen.blit("road", (road2_x, 0))
        if DEBUG_PROFILING:
            print("road " + str(p.get_ms()))

        # Set initial position for background tiles
        # Due to isometric nature of background, each background tile includes a transparent part - the second line
        # skips that part for the first tile
        pos = -self.scroll_offset
        pos.x -= BACKGROUND_TILE_SPACING

        # Draw background tiles
        p = Profiler()
        for tile in BACKGROUND_TILES:
            # Don't bother drawing tile if it's off the left of the screen
            if pos.x + 417 >= 0:
                screen.blit(tile, pos)
                pos.x += BACKGROUND_TILE_SPACING
                if pos.x >= WIDTH:
                    # Stop once we've reached or gone past the right edge of the screen
                    break
            else:
                pos.x += BACKGROUND_TILE_SPACING
        if DEBUG_PROFILING:
            print("bg " + str(p.get_ms()))

    def shutdown(self):
        # When game is over, we need to tell enemies to die, since that's how the scooter engine sound effect gets
        # turned off
        for enemy in self.enemies:
            enemy.died()

    def get_sound(self, name, count=1):
        if self.player:
            return getattr(sounds, name + str(randint(0, count - 1)))

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
                sound = self.get_sound(name, count)
                sound.play()
            except Exception as e:
                # If no sound file of that name was found, print the error that Pygame Zero provides, which
                # includes the filename.
                # Also occurs if sound fails to play for another reason (e.g. if this machine has no sound hardware)
                print(e)

# From Eggzy
def get_char_image_and_width(char):
    # Return width of given character. ord() gives the ASCII/Unicode code for the given character.
    if char == " ":
        return None, 22
    else:
        if char in SPECIAL_FONT_SYMBOLS_INVERSE:
            image = getattr(images, SPECIAL_FONT_SYMBOLS_INVERSE[char])
        else:
            image = getattr(images, "font0"+str(ord(char)))
        return image, image.get_width()

def text_width(text):
    return sum([get_char_image_and_width(c)[1] for c in text])

def draw_text(text, x, y, centre=False):
    # Note that the centre option does not work correctly for text with line breaks
    if centre:
        x -= text_width(text) // 2

    start_x = x

    for char in text:
        if char == "\n":
            # New line
            y += 35
            x = start_x
        else:
            image, width = get_char_image_and_width(char)
            if image is not None:
                screen.blit(image, (x, y))
            x += width

# Set up controls
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

class State(Enum):
    TITLE = 1
    CONTROLS = 2
    PLAY = 3
    GAME_OVER = 4


# Pygame Zero calls the update and draw functions each frame

def update():
    global state, game, total_frames

    total_frames += 1

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
        # Check for start game
        if button_pressed_controls(0) is not None:
            state = State.CONTROLS

    elif state == State.CONTROLS:
        # Check for player starting game with either keyboard or controller
        controls = button_pressed_controls(0)
        if controls is not None:
            # Switch to play state, and create a new Game object, passing it the controls object which was used to start the game
            state = State.PLAY
            game = Game(controls)

    elif state == State.PLAY:
        game.update()
        if game.player.lives <= 0 or game.check_won():
            # Need to call game.shutdown to turn off scooter engine sound
            game.shutdown()
            state = State.GAME_OVER

    elif state == State.GAME_OVER:
        if button_pressed_controls(0) is not None:
            # Go back into title screen mode
            state = State.TITLE
            game = None

def draw():
    if state == State.TITLE:
        # Draw logo
        logo_img = images.title0 if total_frames // 20 % 2 == 0 else images.title1
        screen.blit(logo_img, (WIDTH//2 - logo_img.get_width() // 2, HEIGHT//2 - logo_img.get_height() // 2))

        draw_text(f"PRESS {SPECIAL_FONT_SYMBOLS['xb_a']} OR Z",  WIDTH//2, HEIGHT - 50, True)

    elif state == State.CONTROLS:
        screen.fill((0,0,0))
        screen.blit("menu_controls", (0,0))

    elif state == State.PLAY:
        game.draw()

    elif state == State.GAME_OVER:
        # Draw game over screen
        # Did player win or lose?
        if game.check_won():
            img = images.status_win
        else:
            img = images.status_lose
        screen.blit(img, (WIDTH//2 - img.get_width() // 2, HEIGHT//2 - img.get_height() // 2))

##############################################################################

# Set up sound system and start music
try:
    # Restart the Pygame audio mixer which Pygame Zero sets up by default. We find that the default settings
    # cause issues with delayed or non-playing sounds on some devices
    mixer.quit()
    mixer.init(44100, -16, 2, 1024)

    music.play("theme")
    music.set_volume(0.3)
except Exception as e:
    # If an error occurs (e.g. no sound hardware), ignore it
    pass

total_frames = 0

# Set up controls
keyboard_controls = KeyboardControls()
setup_joystick_controls()

# Set the initial game state
state = State.TITLE
game = None

# Tell Pygame Zero to take over
pgzrun.go()
