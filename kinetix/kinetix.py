# Kinetix - Code the Classics Volume 2
# Code by Eben Upton and Andrew Gillett
# Graphics by Dan Malone
# Music and sound effects by Allister Brimble
# https://github.com/raspberrypipress/Code-the-Classics-Vol2.git
# https://store.rpipress.cc/products/code-the-classics-volume-ii

# If the game window doesn't fit on the screen, you may need to turn off or reduce display scaling in the Windows/macOS settings
# On Windows, you can uncomment the following two lines to fix the issue. It sets the program as "DPI aware"
# meaning that display scaling won't be applied to it.
#import ctypes
#ctypes.windll.user32.SetProcessDPIAware()

import pygame, pgzero, pgzrun, math, sys
from abc import ABC, abstractmethod
from enum import Enum, IntEnum
from random import random, randint, uniform, choice
from pygame import surface
from pygame.math import Vector2

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
WIDTH = 640
HEIGHT = 640
TITLE = "Kinetix"

BAT_SPEED = 8

BAT_MIN_X = 35
BAT_MAX_X = 605

TOP_EDGE = 50
RIGHT_EDGE = 617
LEFT_EDGE = 23

BAT_TOP_EDGE = 590

BALL_INITIAL_OFFSET = 10

BALL_START_SPEED = 5
BALL_MIN_SPEED = 4
BALL_MAX_SPEED = 11

BALL_SPEED_UP_INTERVAL = 10 * 60        # Normal ball speed up interval (10 seconds at 60 frames per second)
BALL_SPEED_UP_INTERVAL_FAST = 15 * 60   # Speed up interval for when the ball is above a speed threshold
BALL_FAST_SPEED_THRESHOLD = 7

BALL_RADIUS = 7

BULLET_SPEED = 8

BRICKS_X_START = 20
BRICKS_Y_START = 100

BRICK_WIDTH = 40
BRICK_HEIGHT = 20
SHADOW_OFFSET = 10

POWERUP_CHANCE = 0.2

FIRE_INTERVAL = 30

PORTAL_ANIMATION_SPEED = 5

LEVELS = [
        ["        ",
         "        ",
         "        ",
         "     a  ",
         "    a7a ",
         "     a  ",
         "     a55",
         "    444 ",
         "   333a ",
         "  222a  ",
         " 111a   ",
         "   11aa ",
         "    111 ",
         "    6   ",
         "     6  "],

        ["        ",
         "        ",
         "    3   ",
         "    3   ",
         "    3   ",
         "    3000",
         "    3000",
         "   53000",
         "   53000",
         "  35a555",
         " 3 5aa55",
         "3  5aaa5",
         "  355555",
         "  333333",
         "   333  ",
         "    33  ",
         "     3  "],

        ["   7    ",
         "  77    ",
         " 7777   ",
         " 7777   ",
         " 77777  ",
         " 77777  ",
         " 77 777 ",
         " 7  7777",
         " 7   717",
         "     777",
         "      77",
         "      7 ",
         "     c7 ",
         "      c ",
         "      c "],

        ["   03   ",
         "   30   ",
         "    03  ",
         "    30  ",
         "     0  ",
         " 8   0  ",
         " 88 8033",
         "  883333",
         "   8333d",
         "   33733",
         "  33373d",
         " 3333333",
         " 3c 333d",
         " cc 3333",
         " c   3 3",
         "     3 3",
         "    3 3 ",
         "    c 3 ",
         "    cc3c",
         "    cccc",
         "      d "],

        ["5   9  0",
         "0   4  3",
         "08  4  4",
         "53  47 2",
         " 39 92 1",
         " 84  2  ",
         "  47 26 ",
         "5 92 71 ",
         "08 26 1 ",
         "53971 1 ",
         " 8471c6 ",
         "  926acc",
         "   71aad",
         "039 6aac",
         "dc421ac ",
         "  dccc  ",
         "    d   "],

        ["  dccccd",
         "  c89765",
         "  c34210",
         "  c34210",
         "  c34210",
         "  c34210",
         "  c3421d",
         "  c34210",
         "  c34210",
         "  c34210",
         "  c34210",
         "  c89765",
         "  dccccd"]
]

def get_mirrored_level(level):
    # For each row, return a new row which includes the existing row plus
    # a mirrored version.
    # row[-2::-1] produces a mirorred version of the list, excluding the last element
    return [row + row[-2::-1] for row in level]

class Controls(ABC):
    def __init__(self):
        self.fire_previously_down = False
        self.is_fire_pressed = False

    def update(self):
        # Call each frame to update fire status
        fire_down = self.fire_down()
        self.is_fire_pressed = fire_down and not self.fire_previously_down
        self.fire_previously_down = fire_down

    @abstractmethod
    def get_x(self):
        # Overridden by subclasses
        pass

    @abstractmethod
    def fire_down(self):
        # Overridden by subclasses
        pass

    def fire_pressed(self):
        return self.is_fire_pressed

class KeyboardControls(Controls):
    def get_x(self):
        if keyboard.left:
            return -BAT_SPEED
        elif keyboard.right:
            return BAT_SPEED
        else:
            return 0

    def fire_down(self):
        return keyboard.space

class JoystickControls(Controls):
    def __init__(self, joystick):
        super().__init__()
        self.joystick = joystick
        joystick.init() # Not necessary in Pygame 2.0.0 onwards

    def get_x(self):
        # First check if there is an input on the dpad for the X axis. The dpad is classified here as a joystick 'hat'
        if self.joystick.get_numhats() > 0 and self.joystick.get_hat(0)[0] != 0:
            return self.joystick.get_hat(0)[0] * BAT_SPEED

        # If no input on the dpad, check for analogue left/right input
        axis_value = self.joystick.get_axis(0)
        if abs(axis_value) < 0.2:
            # Dead-zone, necessary because some devices may register a small amount of input even when the player isn't
            # moving the analogue stick
            return 0
        else:
            return axis_value * BAT_SPEED

    def fire_down(self):
        # Before checking button 0, check to make sure that the controller actually has any buttons
        # There are some weird devices out there which could cause a crash if this check were not present
        if self.joystick.get_numbuttons() <= 0:
            print("Warning: controller does not have any buttons!")
            return False
        return self.joystick.get_button(0) != 0

class AIControls(Controls):
    def __init__(self):
        super().__init__()
        self.offset = 0

    def get_x(self):
        if game.portal_active:
            # If the portal to the next level is open, just move right so that we go through it
            return BAT_SPEED
        else:
            # Randomly shift the bat AI offset over time, so the AI player doesn't constantly hit the ball perfectly
            # in the centre of the bat. Limit offset between -40 and 40
            self.offset += randint(-1, 1)
            self.offset = min(max(-40, self.offset), 40)

            # Follow position of the first ball (in case of multiball)
            return min(BAT_SPEED, max(-BAT_SPEED, game.balls[0].x - (game.bat.x + self.offset)))

    def fire_down(self):
        # Just have the AI mash the fire button
        return randint(0,5) == 0

class Powerup(IntEnum):
    # These numbers correspond to the sprite filenames
    # e.g. barrel06 is extend bat, frame 6
    EXTEND_BAT = 0
    GUN = 1
    SMALL_BAT = 2
    MAGNET = 3
    MULTI_BALL = 4
    FAST_BALLS = 5
    SLOW_BALLS = 6
    PORTAL = 7
    EXTRA_LIFE = 8

class BatType(IntEnum):
    NORMAL = 0
    MAGNET = 1
    GUN = 2
    EXTENDED = 3
    SMALL = 4

POWERUP_BAT_TYPES = {
    Powerup.EXTEND_BAT: BatType.EXTENDED,
    Powerup.GUN: BatType.GUN,
    Powerup.SMALL_BAT: BatType.SMALL,
    Powerup.MAGNET: BatType.MAGNET
}

POWERUP_SOUNDS = {
    Powerup.EXTEND_BAT: "bat_extend",
    Powerup.GUN: "bat_gun",
    Powerup.MAGNET: "magnet",
    Powerup.SMALL_BAT: "bat_small",
    Powerup.EXTRA_LIFE: "extra_life",
    Powerup.FAST_BALLS: "speed_up",
    Powerup.SLOW_BALLS: "powerup",
    Powerup.MULTI_BALL: "multiball"
}

class CollisionType(Enum):
    WALL = 0
    BAT = 1
    BAT_EDGE = 2
    BRICK = 3
    INDESTRUCTIBLE_BRICK = 4

class Bullet(Actor):
    def __init__(self, pos, side):
        super().__init__(f"bullet{side}", pos)

        self.alive = True

    def update(self):
        self.y -= BULLET_SPEED

        # returns tuple of (tuple 2: impact pos, bool: show impact, CollisionType), or None if no collision
        c = game.collide(self.x, self.y, Vector2(0, -1), 2)
        if c is not None:
            self.alive = False
            game.impacts.append(Impact(self.pos, 15))
            if c[2] == CollisionType.BRICK or c[2] == CollisionType.INDESTRUCTIBLE_BRICK:
                game.play_sound("bullet_hit", 4)

# The barrel class represents the collectable powerups that sometimes fall from destroyed bricks
class Barrel(Actor):
    def __init__(self, pos):
        super().__init__("blank", pos)

        # Decide powerup type, with each type able to have its own probability
        # First we create a dictionary of types to weights, where a higher weight means that powerup is more likely
        # to be chosen. For the PORTAL powerup, which opens a portal to the next level, it can't be generated unless
        # there are only a few bricks remaining, at which point it becomes very likely
        weights = {Powerup.EXTEND_BAT:6,
                   Powerup.GUN:6,
                   Powerup.SMALL_BAT:6,
                   Powerup.MAGNET:6,
                   Powerup.MULTI_BALL:6,
                   Powerup.FAST_BALLS:6,
                   Powerup.SLOW_BALLS:6,
                   Powerup.EXTRA_LIFE:2,
                   Powerup.PORTAL:0 if game.bricks_remaining > 20 or game.portal_active else 20}

        # Create a list of powerup types, with each type repeated a certain
        # number of times based on its weight
        types = [type for type, weight in weights.items() for i in range(weight)]

        # Randomly choose one of the types from the list. Types which
        # are repeated many times are more likely to be chosen
        self.type = choice(types)

        self.time = 0

        # Create separate actor for shadow sprite
        self.shadow = Actor("barrels", (self.x + SHADOW_OFFSET, self.y + SHADOW_OFFSET))

    def update(self):
        self.time += 1
        self.y += 1

        w = (game.bat.width // 2) + BALL_RADIUS

        # Check for barrel being collected by bat
        if self.y >= BAT_TOP_EDGE - 10 and self.y <= BAT_TOP_EDGE + 30 and abs(self.x - game.bat.x) < w:
            # Create barrel collection animation - sprites 'impacte0' to 'impacte4'
            # 14 is E in hexadecimal
            game.impacts.append(Impact((self.x, self.y - 11), 14))

            # Play sound effect (if this powerup has a sound effect)
            if self.type in POWERUP_SOUNDS:
                game.play_sound(POWERUP_SOUNDS[self.type])

            # Move barrel off the bottom of the screen, it will then be deleted
            self.y = HEIGHT + 100

            if self.type in POWERUP_BAT_TYPES:
                game.bat.change_type(POWERUP_BAT_TYPES[self.type])
            elif self.type == Powerup.MULTI_BALL:
                game.balls = [j for b in game.balls for j in b.generate_multiballs()]
            elif self.type == Powerup.FAST_BALLS:
                game.change_all_ball_speeds(3)
            elif self.type == Powerup.SLOW_BALLS:
                game.change_all_ball_speeds(-3)
            elif self.type == Powerup.PORTAL:
                game.activate_portal()
            elif self.type == Powerup.EXTRA_LIFE:
                game.lives += 1

        # The name of each powerup sprite has the format "barrel[powerup type][frame]",
        # where powerup type is a number from 0 to 8 and frame is a number from 0 to 9
        # We switch to a new animation frame every 10 game frames
        self.image = f"barrel{int(self.type)}{self.time // 10 % 10}"

        self.shadow.pos = (self.x + SHADOW_OFFSET, self.y + SHADOW_OFFSET)

# The Impact class is used for the animations played when the ball hits a wall or destroys a brick
class Impact(Actor):
    def __init__(self, pos, type):
        super().__init__("blank", pos)

        self.type = type
        self.time = 0

    def update(self):
        # The impact animation sprites have names like 'impact00' where the first digit is the type of impact and
        # the second is the animation frame. The type is converted into a hexadecimal number. The type can be between
        # 0 and 15, where values from 10 to 15 are represented by the hexadecimal digits a to f. The Python hex
        # function is used to convert the type to hexadecimal, the resulting string will always start with '0x' meaning
        # hexadecimal, so we strip off the first two characters from the start of string.
        self.image = "impact" + hex(self.type)[2:] + str(self.time // 4)

        self.time += 1

class Ball(Actor):
    def __init__(self, x=0, y=0, dir=Vector2(0, 0), stuck_to_bat=True, speed=BALL_START_SPEED):
        super().__init__("ball0", (0,0))

        self.x = x
        self.y = y

        # Direction should always be a unit vector (a vector with a length of 1)
        # It's important that we make a full copy of the direction, rather than just copying the reference.
        # Since a Vector2 is an object, it's a reference type. If you copy a reference type it means you now have two
        # variables referring to the same object. If we said below 'self.dir = dir' it would mean that when a ball
        # copied its direction from another ball, the directions of the two balls would remain linked to each other
        self.dir = Vector2(dir)

        self.stuck_to_bat = stuck_to_bat
        self.bat_offset = BALL_INITIAL_OFFSET

        self.speed = speed

        self.speed_up_timer = 0
        self.time_since_touched_bat = 0
        self.time_since_damaged_brick = 0

        self.shadow = Actor("balls", (self.x + 16, self.y + 16))

    def update(self):
        self.time_since_damaged_brick += 1

        if self.stuck_to_bat:
            self.x = game.bat.x + self.bat_offset
            self.y = game.bat.y - BALL_RADIUS

            # Launch ball from bat if fire is pressed
            if game.controls.fire_pressed():
                self.stuck_to_bat = False
                _, self.dir = self.get_bat_bounce_vector()
        else:
            # Normal ball movement
            self.time_since_touched_bat += 1

            # Speed up every so often
            # If ball hasn't touched bat in a while, speed up more frequently
            self.speed_up_timer += 1
            if self.time_since_touched_bat > 5 * 60:
                self.speed_up_timer += 1
            interval = BALL_SPEED_UP_INTERVAL if self.speed < BALL_FAST_SPEED_THRESHOLD else BALL_SPEED_UP_INTERVAL_FAST
            interval2 = interval * 0.75
            if self.speed_up_timer > interval or (self.speed_up_timer > interval2 and self.time_since_touched_bat > interval2):
                self.increment_speed()
                self.speed_up_timer = 0

            # Move one pixel at a time, speed times (rounded down to a whole number)
            for i in range(self.speed):
                # Move and collide on X axis
                self.x += self.dir.x

                # returns tuple of (tuple 2: impact pos, bool: show impact, CollisionType), or None if no collision
                c = game.collide(self.x, self.y, self.dir)

                if c is not None:
                    # Invert X direction and move back to previous position, before the collision
                    self.dir.x = -self.dir.x
                    self.x += self.dir.x

                    if c[1]:
                        # Create impact animation type 12 (C in hexadecimal)
                        game.impacts.append(Impact(c[0], 0xc))

                    if c[2] == CollisionType.BRICK:
                        self.time_since_damaged_brick = 0

                    Ball.collision_sound(c[2])

                # Original y position before movement
                oy = self.y

                # Move and collide on Y axis
                self.y += self.dir.y

                # returns tuple of (tuple 2: impact pos, bool: show impact, CollisionType), or None
                c = game.collide(self.x, self.y, self.dir)

                if c is not None:
                    # Invert Y direction and move back to previous position, before the collision
                    self.dir.y = -self.dir.y
                    self.y += self.dir.y

                    if c[1]:
                        # Create impact animation type 12 (C in hexadecimal)
                        game.impacts.append(Impact(c[0], 0xc))

                    if c[2] == CollisionType.BRICK:
                        self.time_since_damaged_brick = 0

                    Ball.collision_sound(c[2])

                elif self.dir.y > 0:
                    # Check for collision with bat - only if we're moving down

                    # If bottom of ball was previously above/at top edge of bat, but is now below it
                    if oy + BALL_RADIUS <= BAT_TOP_EDGE and self.y + BALL_RADIUS > BAT_TOP_EDGE:
                        # See if we're colliding on X axis
                        collided_x, new_dir = self.get_bat_bounce_vector()
                        if collided_x:
                            # Ball collided with bat
                            if game.bat.current_type == BatType.MAGNET:
                                self.stuck_to_bat = True
                                self.bat_offset = self.x - game.bat.x
                                self.dir = Vector2(0, 0)
                            else:
                                # No magnet powerup, bounce ball in the direction we got from get_bat_bounce_vector
                                self.dir = new_dir

                            self.time_since_touched_bat = 0

                            game.impacts.append(Impact((self.x, self.y), 0xc))

                            Ball.collision_sound(CollisionType.BAT)

                            # If we became stuck to the bat, break out of the movement/speed loop
                            if self.stuck_to_bat:
                                break

                    # If bottom of ball is below top edge of bat, and top of ball is above halfway point of bat
                    elif self.y + BALL_RADIUS > BAT_TOP_EDGE and self.y < BAT_TOP_EDGE + 15:
                        # If the ball hits the top of the bat, the section above will deal with it, if we get here
                        # and the bat/ball positions on the X axis overlap, that means the ball must have hit the
                        # side of the bat.

                        # See if we're colliding on X axis
                        collided_x, _ = self.get_bat_bounce_vector()
                        if collided_x:
                            # Detected ball hitting the side of the bat
                            # Send the ball off at an extreme angle, and increase speed

                            # Determine whether the ball will go left or right
                            dx = 1 if self.x > game.bat.x else -1

                            # Determine new direction vector, with a slightly random Y velocity
                            # The new direction vector is normalised to ensure that it is a unit vector
                            self.dir = Vector2(dx, uniform(-0.3, -0.1)).normalize()

                            self.time_since_touched_bat = 0

                            game.impacts.append(Impact((self.x, BAT_TOP_EDGE), 0xc))

                            self.speed = min(self.speed + 4, BALL_MAX_SPEED)

                            Ball.collision_sound(CollisionType.BAT_EDGE)

        # Set shadow actor's position
        self.shadow.pos = (self.x + 16, self.y + 16)

    def increment_speed(self):
        self.speed = min(self.speed + 1, BALL_MAX_SPEED)

    def get_bat_bounce_vector(self):
        # Determine the direction vector to use for the ball bouncing off the bat
        # For bat side collisions this is handled in update, in that case this
        # method is just used to determine whether the ball overlapped with the
        # bat on the X axis

        # dx = difference in X position between centre of bat and centre of ball
        dx = self.x - game.bat.x

        # dx must be within w pixels for the ball to be able to hit the bat
        w = (game.bat.width // 2) + BALL_RADIUS

        # Is ball is within the correct range of the bat on the X axis?
        if abs(dx) < w:
            # Return that the ball was within the correct range on the X
            # axis for there to be a collision, and the bounce vector this
            # position corresponds to
            vec = Vector2(dx / w, -0.5).normalize()
            return True, vec
        else:
            # Return that the ball was not close enough on the X axis for a
            # collision to be possible. Return a vector pointing straight up
            # in case any code tries to use the bounce vector in this scenario.
            # This shouldn't happen, but better safe than sorry - returning
            # None for these values could result in a crash in such a scenario
            return False, Vector2(0, -1)

    def generate_multiballs(self):
        # Get multi ball initial positions
        # This method is called for each existing ball, returning a list of 3 new balls for each one
        # The original ball is then discarded
        balls = []
        for i in range(3):
            # Create direction vector for new ball, the first ball will have the same direction as
            # its original parent ball, the others will have direction vectors rotated 120 and 240
            # degrees from that
            vec = self.dir.rotate(i * 120)
            if abs(vec.y) < 0.15:
                # dy could be zero if the ball is currently stuck to the bat, or could be very close
                # to zero by chance, which could lead to the ball bouncing left and right for ages
                # So if either of these happen, just generate a random upward vector
                vec = Vector2(uniform(-1,1), -1).normalize()

            balls.append(Ball(self.x, self.y, vec, False, self.speed))

        return balls

    @staticmethod
    def collision_sound(collision_type):
        # A static method relates to the class as a whole rather than a specific instance
        # of the class, so doesn't have self as the first parameter
        if collision_type == CollisionType.BRICK or collision_type == CollisionType.INDESTRUCTIBLE_BRICK:
            game.play_sound("hit_brick")
        elif collision_type == CollisionType.WALL:
            game.play_sound("hit_wall")
        elif collision_type == CollisionType.BAT:
            if game.bat.current_type == BatType.MAGNET:
                game.play_sound("ball_stick")
            else:
                game.play_sound("hit_fast")
        elif collision_type == CollisionType.BAT_EDGE:
            if game.bat.current_type == BatType.MAGNET:
                game.play_sound("ball_stick")
            else:
                game.play_sound("hit_veryfast")

class Bat(Actor):
    def __init__(self, controls):
        super().__init__("blank", (320, 590), anchor=("center", 15))

        self.controls = controls
        self.fire_timer = 0

        # The values of target_type and current_type are instances the BatType enum
        # Normally these will be the same. If the player has just picked up a powerup/powerdown
        # then type is the type of bat we're transitioning to, once the transition animation has finished
        # the current type is set to the type
        self.current_type = BatType.NORMAL
        self.target_type = BatType.NORMAL
        self.frame = 0

        # Create shadow actor
        self.shadow = Actor("blank", (self.x + 16, self.y + 16), anchor=("center", 15))

    def update(self):
        # Handle animating to a new bat type
        # If we're a normal bat, we animate to a new type over 12 game frames,
        # changing animation frame every 4 game frames
        # e.g. changing from normal bat (sprite: bat00) to small bat, we go to
        # bat40 (which is the same as the normal bat), then through bat41, bat42
        # and ending at bat43, the fully shrunk bat.
        if self.target_type != BatType.NORMAL and self.target_type == self.current_type and self.frame < 12:
            self.frame += 1

        # If we're switching to a new type from something other than normal bat,
        # we first animate backwards to the first frame of the current type
        if self.target_type != self.current_type and self.frame > 0:
            self.frame -= 1

        # When we're at frame 0, we can update the current type to equal the
        # new type
        if self.frame == 0:
            self.current_type = self.target_type

        # Choose sprite based on current_type and frame
        self.image = f"bat{int(self.current_type)}{self.frame // 4}"

        self.fire_timer -= 1

        # Fire gun?
        if self.controls.fire_down() and self.current_type == BatType.GUN and self.frame == 12 and self.fire_timer <= 0:
            self.fire_timer = FIRE_INTERVAL

            self.image += "f"  # not really visible for the 1 frame it's shown

            game.bullets.append(Bullet((self.x - 20, self.y), 0))
            game.bullets.append(Bullet((self.x + 20, self.y), 1))

            game.play_sound("laser")

        # Move bat based on controls, don't let it go off the edge of the screen
        new_x = self.x + self.controls.get_x()

        # Enforce left boundary
        min_x = BAT_MIN_X + (self.width // 2)
        new_x = max(min_x, new_x)

        if not game.portal_active:
            # Enforce right boundary
            max_x = BAT_MAX_X - (self.width // 2)
            new_x = min(max_x, new_x)

        self.x = new_x

        # Check for leaving level via portal
        if game.portal_active and new_x == BAT_MAX_X - (self.width // 2):
            self.portal_animation_active = True

        # Update shadow actor
        self.shadow.x = self.x + 16
        self.shadow.y = self.y + 16
        self.shadow.image = f"bats{str(int(self.current_type))}{self.frame // 4}"

    def change_type(self, type):
        self.target_type = type

    def is_portal_transition_complete(self):
        return self.x - (self.width // 2) >= WIDTH

# Does the ball (x, y, radius) collide with the brick at the given
# grid position? Returns the point at which the collision occurred
def brick_collide(x, y, grid_x, grid_y, r):
    # Get ball extent as a square
    x0 = x - r
    y0 = y - r
    x1 = x + r
    y1 = y + r

    # Get brick's left, top, right and bottom coordinates
    xb0 = grid_x * BRICK_WIDTH + BRICKS_X_START
    yb0 = grid_y * BRICK_HEIGHT + BRICKS_Y_START
    xb1 = xb0 + BRICK_WIDTH
    yb1 = yb0 + BRICK_HEIGHT

    # Calculate brick centre position
    xbc = (xb0+xb1) // 2
    ybc = (yb0+yb1) // 2

    # Detecting bounce off side of brick
    # if ball right edge > brick left edge,
    #  and ball left edge < brick right edge
    #  and ball y centre > brick top edge
    #  and ball y centre < brick bottom edge
    if x1 > xb0 and x0 < xb1 and y > yb0 and y < yb1:
        if x < xbc:
            return xb0, y
        else:
            return xb1, y

    # Detect bounce off top or bottom of brick
    # if ball x centre > brick left edge
    #  and ball x centre < brick right edge
    #  and ball y bottom > brick y top
    #  and ball y top < brick y bottom
    if x > xb0 and x < xb1 and y1 > yb0 and y0 < yb1:
        if y < ybc:
            return x, yb0
        else:
            return x, yb1

    # Put x/y position into a Vector2 object, which allows us to use the Vector2 methods length/length_squared
    # to calculate distances
    pos_vector = Vector2(x, y)

    # Get closest brick corner
    # We call the Python min function with a list of positions (one for each corner of the brick)
    # The key argument is a lambda function which calculates the squared distance between pos_vector (the pos we're
    # checking) and the corner position (p). We use length_squared rather than length because it's faster and we just
    # care about which corner is closest, not what the actual distance is
    closest = min([(xb0, yb0), (xb1, yb0), (xb0, yb1), (xb1, yb1)],
                  key = lambda p: (pos_vector - Vector2(p)).length_squared())

    # Check if we are actually overlapping with the nearest corner
    if (pos_vector - Vector2(closest)).length() < r:
        # Position does overlap with nearest corner, return corner position
        return closest
    else:
        # No collision with this brick
        return None

class Game:
    def __init__(self, controls=None, lives=3):
        self.controls = controls if controls else AIControls()
        self.lives = lives
        self.score = 0

        self.new_level(0)

    def new_level(self, level_num):
        self.play_sound("start_game")

        # Go back to first level if we've finished last level
        if level_num >= len(LEVELS):
            level_num = 0

        # Create bitmaps for brick and shadow backgrounds
        self.brick_surface = surface.Surface((WIDTH, HEIGHT), flags=pygame.SRCALPHA)
        self.brick_surface.fill((0, 0, 0, 0))

        self.shadow_surface = surface.Surface((WIDTH, HEIGHT), flags=pygame.SRCALPHA)
        self.shadow_surface.fill((0, 0, 0, 0))

        level = get_mirrored_level(LEVELS[level_num])

        self.num_rows = len(level)
        self.num_cols = len(level[0])

        # Convert level data, a list of strings, to as 2D list of integers (or None where no brick is present)
        # The numbers in the level data are in hexadecimal (base 16), where A to F represent 10 to 15
        self.bricks = [[None if level[y][x] == " " else int(level[y][x], 16) for x in range(self.num_cols)] for y in range(self.num_rows)]

        # Draw bricks, and count how many there are, not counting brick ID 13 which is indestructible
        self.bricks_remaining = 0
        for y in range(self.num_rows):
            for x in range(self.num_cols):
                self.redraw_brick(x, y)
                if self.bricks[y][x] != None and self.bricks[y][x] != 13:
                    self.bricks_remaining += 1

        self.balls = [Ball()]
        self.bat = Bat(self.controls)

        self.bullets = []
        self.barrels = []
        self.impacts = []

        self.level_num = level_num
        self.portal_active = False
        self.portal_frame = 0
        self.portal_timer = 0

    def redraw_brick(self, x, y):
        screen_x = x * BRICK_WIDTH + BRICKS_X_START
        screen_y = y * BRICK_HEIGHT + BRICKS_Y_START
        if self.bricks[y][x] != None:
            # Display a brick at this position

            # Get brick image via filename, the files have names brick0 to brickd, see Impact class for a comment
            # explaining how we use hexadecimal numbers here
            brick_image = getattr(images, "brick" + hex(self.bricks[y][x])[2:])

            # Display the brick image to the brick surface, which is an image just containing the bricks
            self.brick_surface.blit(brick_image, (screen_x, screen_y))

            # Update shadow surface
            self.shadow_surface.blit(images.bricks, (screen_x + SHADOW_OFFSET, screen_y + SHADOW_OFFSET))
        else:
            # Remove a brick (and its shadow) from this position)
            self.brick_surface.fill((0, 0, 0, 0), (screen_x, screen_y, BRICK_WIDTH, BRICK_HEIGHT))
            self.shadow_surface.fill((0, 0, 0, 0), (screen_x + SHADOW_OFFSET, screen_y + SHADOW_OFFSET, BRICK_WIDTH, BRICK_HEIGHT))

    def collide(self, x, y, dir, r=BALL_RADIUS):
        # Called to check whether a ball or a bullet would collide with something if it moved in the specified direction
        # Only checks for walls and bricks, collisions with bat are handled elsewhere
        # If there's a collision with a destructible brick, the brick will take damage
        # returns tuple of (tuple 2: impact pos, bool: show impact, CollisionType), or None if no collision

        # Extract x and y of direction into separate variables
        dx,dy = dir

        if dx < 0 and x < LEFT_EDGE + r:
            return (LEFT_EDGE, y), True, CollisionType.WALL
        if dx > 0 and x > RIGHT_EDGE - r:
            return (RIGHT_EDGE, y), True, CollisionType.WALL
        if dy < 0 and y < TOP_EDGE + r:
            return (x, TOP_EDGE), True, CollisionType.WALL

        # Work out the range of brick rows and columns that the ball overlaps
        # This means we don't need to check the ball against every brick,
        # only against the bricks it could potentially be colliding with
        x0 = max(0, math.floor((x-BRICKS_X_START-r)/BRICK_WIDTH))
        y0 = max(0, math.floor((y-BRICKS_Y_START-r)/BRICK_HEIGHT))
        x1 = min(self.num_cols - 1, math.floor((x - BRICKS_X_START + r) / BRICK_WIDTH))
        y1 = min(self.num_rows - 1, math.floor((y - BRICKS_Y_START + r) / BRICK_HEIGHT))

        # Collide with bricks
        for yb in range(y0, y1+1):
            for xb in range(x0, x1+1):
                # Is there a brick in this position?
                if self.bricks[yb][xb] != None:
                    # Check for collision with current brick
                    c = brick_collide(x, y, xb, yb, r)

                    if c is not None:
                        # There was a collision
                        centre_pos = (xb * BRICK_WIDTH + BRICKS_X_START + BRICK_WIDTH // 2,
                                      yb * BRICK_HEIGHT + BRICKS_Y_START + BRICK_HEIGHT // 2)

                        collision_type = CollisionType.BRICK

                        # Check brick type
                        # Brick 12 (brickc.png) requires a hit to turn into brick 11
                        # Brick 13 (brickd.png) is indestructible
                        if self.bricks[yb][xb] >= 12:
                            # Indestructible brick
                            if self.bricks[yb][xb] == 13:
                                collision_type = CollisionType.INDESTRUCTIBLE_BRICK
                            self.impacts.append(Impact(centre_pos, 13))
                            if self.bricks[yb][xb] == 12:
                                self.bricks[yb][xb] = 11
                        else:
                            self.impacts.append(Impact(centre_pos, self.bricks[yb][xb]))

                            if random() < POWERUP_CHANCE:
                                self.barrels.append(Barrel(centre_pos))

                            self.bricks[yb][xb] = None
                            self.redraw_brick(xb, yb)

                            self.bricks_remaining -= 1
                            if self.bricks_remaining == 0:
                                self.activate_portal()

                            self.score += 10

                        return c, False, collision_type

        return None

    def activate_portal(self):
        self.portal_active = True
        self.play_sound("portal_exit")

    def update(self):
        # Update bat and balls
        for obj in [self.bat] + self.balls:
            obj.update()

        # Remove any balls which are off the bottom of the screen
        # We achieve this by regenerating the balls list using a list comprehension, only keeping balls which are
        # still on the screen
        self.balls = [obj for obj in self.balls if obj.y < HEIGHT]

        # Lose a life if there are no balls
        if len(self.balls) == 0:
            # We don't care about how many lives the player has in demo mode
            if self.lives > 0 or self.in_demo_mode():
                self.lives -= 1
                self.balls = [Ball()]
                self.bat.change_type(BatType.NORMAL)

            self.play_sound("lose_life")

        # Update impacts, barrels and bullets
        for obj in self.impacts + self.barrels + self.bullets:
            obj.update()

        # Remove timed-out impacts, barrels which have gone off the bottom of
        # the screen, and bullets which are no longer alive
        self.impacts = [obj for obj in self.impacts if obj.time < 16]
        self.barrels = [obj for obj in self.barrels if obj.y < HEIGHT]
        self.bullets = [obj for obj in self.bullets if obj.alive]

        # Update the portal that allows you to leave the level
        if self.portal_active:
            if self.portal_frame < 3:
                # Update portal animation
                self.portal_timer -= 1
                if self.portal_timer <= 0:
                    self.portal_timer = PORTAL_ANIMATION_SPEED
                    self.portal_frame += 1
            elif self.bat.is_portal_transition_complete():
                self.new_level(self.level_num + 1)

        # If no balls have damaged/destroyed bricks or touched the bat in the last 30 seconds, change all
        # indestructible bricks to two-hit bricks, to avoid a situation where the ball can get stuck bouncing
        # between indestructible bricks
        if self.detect_stuck_balls():
            # Go through all bricks, change indestructible bricks to two-hit bricks
            changed_any = False
            for row in range(self.num_rows):
                for col in range (self.num_cols):
                    # 13 is indestructible brick, 12 is two-hit brick
                    if self.bricks[row][col] == 13:
                        self.bricks[row][col] = 12
                        self.redraw_brick(col, row)
                        changed_any = True

            # Play a sound effect, but only if there were indestructible blocks that were changed
            if changed_any:
                self.play_sound("bat_small", 1)

            # To prevent this triggering again next frame, which should have no gameplay impact but could have
            # a performance impact, we'll pretend that one of the balls has touched the bat in the last 30 seconds
            if len(self.balls) > 0:
                self.balls[0].time_since_touched_bat = 0

    def detect_stuck_balls(self):
        # Detect whether all balls are stuck bouncing between indestructible bricks,
        if len(self.balls) == 0:
            # Having no balls in play doesn't count as all balls being stuck
            return False

        for ball in self.balls:
            if ball.time_since_damaged_brick < 30 * 60 or ball.time_since_touched_bat < 30 * 60:
                # This ball has damaged a brick or touched a bat in the last 30 seconds, so all balls aren't stuck
                return False

        # All balls are stuck
        return True

    def draw(self):
        screen.blit(f"arena{self.level_num % len(LEVELS)}", (0,0))

        # Draw exit portal
        screen.blit(f"portal_exit{self.portal_frame}", (WIDTH - 70 - 20, HEIGHT - 70))

        # Draw enemy doors - currently unused, but animations are present for the doors opening and closing,
        # and for enemies - try adding enemies to the game and making use of these animations!
        screen.blit("portal_meanie00", (110, 40))
        screen.blit("portal_meanie10", (440, 40))

        # This prevents drawing onto the edges of the screen, meaning that the
        # shadows don't overlap with the darker part of the right hand wall
        screen.surface.set_clip((20, 42, 600, 598))

        # Draw brick shadows
        screen.blit(self.shadow_surface, (0, 0))

        # Draw shadows for powerup barrels, balls and bat
        for obj in self.barrels + self.balls + [self.bat]:
            obj.shadow.draw()

        # Draw bricks
        screen.blit(self.brick_surface, (0, 0))

        # Draw balls, bat, barrels and bullets
        for obj in self.balls + [self.bat] + self.barrels + self.bullets:
            obj.draw()

        # Cancel screen clipping mode set earlier
        screen.surface.set_clip(None)

        # Draw impact animations
        for obj in self.impacts:
            obj.draw()

        # Only draw score and lives in normal mode, not in AI/demo mode
        if not self.in_demo_mode():
            self.draw_score()
            self.draw_lives()

    def draw_score(self):
        # Convert score into a string of digits (e.g. "150") so we can
        # draw each individual digit, from left to right
        x = 15
        for digit in str(self.score):
            image = "digit" + digit
            screen.blit(image, (x, 50))
            x += 55

    def draw_lives(self):
        x = 0
        for i in range(self.lives):
            screen.blit("life", (x, HEIGHT-20))
            x += 50

    def play_sound(self, name, count=1):
        # We don't play any in-game sound effects if player is an AI player - as this means we're on the menu
        if not self.in_demo_mode():
            try:
                # Pygame Zero allows you to write things like 'sounds.explosion.play()'
                # This automatically loads and plays a file named 'explosion.wav' (or .ogg) from the sounds folder (if
                # such a file exists)
                # But what if you have files named 'explosion0.ogg' to 'explosion5.ogg' and want to randomly choose
                # one of them to play? You can generate a string such as 'explosion3', but to use such a string
                # to access an attribute of Pygame Zero's sounds object, we must use Python's built-in function getattr
                getattr(sounds, name + str(randint(0, count - 1))).play()
            except Exception as e:
                # If no sound file of that name was found, print the error that Pygame Zero provides, which
                # includes the filename.
                # Also occurs if sound fails to play for another reason (e.g. if this machine has no sound hardware)
                print(e)

    def change_all_ball_speeds(self, change):
        for b in self.balls:
            b.speed = min(max(b.speed + change, BALL_MIN_SPEED), BALL_MAX_SPEED)

    def in_demo_mode(self):
        return isinstance(self.controls, AIControls)

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
    PLAY = 2
    GAME_OVER = 3

# Pygame Zero calls the update and draw functions each frame

def update():
    global state, game, total_frames

    total_frames += 1

    update_controls()

    if state == State.TITLE:
        ai_controls.update()
        game.update()

        # Check for start game
        for controls in (keyboard_controls, joystick_controls):
            # Check for fire button being pressed on each controls object
            # joystick_controls will be None if there is no controller, so must check for that
            if controls is not None and controls.fire_pressed():
                game = Game(controls)
                state = State.PLAY
                stop_music()
                break

    elif state == State.PLAY:
        if game.lives > 0:
            game.update()
        else:
            game.play_sound("game_over")
            state = State.GAME_OVER

    elif state == State.GAME_OVER:
        for controls in (keyboard_controls, joystick_controls):
            if controls is not None and controls.fire_pressed():
                # Return to title screen, which includes a game being played by AI in the background
                game = Game(ai_controls)
                state = state.TITLE
                play_music("title_theme")

def draw():
    game.draw()

    if state == State.TITLE:
        screen.blit("title", (0,0))
        screen.blit("startgame", (20,80))
        screen.blit(f"start{(total_frames // 4) % 13}", (WIDTH//2 - 250//2, 530))

    elif state == State.GAME_OVER:
        screen.blit(f"gameover{(total_frames // 4) % 15}", (WIDTH//2 - 450//2, 450))

def play_music(name):
    try:
        music.play(name)
    except Exception:
        # If an error occurs (e.g. no sound hardware), ignore it
        pass

def stop_music():
    try:
        music.stop()
    except Exception:
        # If an error occurs (e.g. no sound hardware), ignore it
        pass

##############################################################################

# Set up sound system and start music
try:
    # Restart the Pygame audio mixer which Pygame Zero sets up by default. We find that the default settings
    # cause issues with delayed or non-playing sounds on some devices
    pygame.mixer.quit()
    pygame.mixer.init(44100, -16, 2, 1024)
    play_music("title_theme")
    music.set_volume(0.3)
except Exception:
    # If an error occurs (e.g. no sound hardware), ignore it
    pass

# Set up controls
keyboard_controls = KeyboardControls()
ai_controls = AIControls()
setup_joystick_controls()

# Set up state and Game object
state = State.TITLE
game = Game(ai_controls)

total_frames = 0

# Tell Pygame Zero to take over
pgzrun.go()
