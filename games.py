import pygame
from pygame.locals import *
import os
import threading
import sys
import time

# Setup pygame, font, and sound
pygame.init()
pygame.font.init()

try:
	pygame.mixer.init()
except:
	print "Unable to initialize sound module. Sound effects will not work."

# Setup the initial mode for the pygame display
pygame.display.set_mode((0,0), DOUBLEBUF)

# Setup the joystick module
pygame.joystick.init()

# Get a list of joysticks available
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]


# Mouse Button Constants
M_LEFT = 0
M_MIDDLE = 1
M_RIGHT = 2

# Key constants are imported from pygame.locals

def _rgba_for_color(color, clear_color):
	''' Return an rgba tuple given an rgb tuple and the color which should be made transparent. '''
	if color == clear_color:
		return (0, 0, 0, 0)
	else:
		r,g,b = color
		return (r,g,b, 255)

def load_image(name, transparent = False):
	''' Load a bitmap image with filename of name. If the second argument is True, all pixels the same color as that in the top left corner will be made transparent.'''
	image = pygame.image.load(name).convert_alpha()
	if transparent:
        # Find the transparency color
		clear_color = image.get_at((0, 0))[:3]
		for row in range(image.get_height()):
			for col in range(image.get_width()):
				image.set_at((col, row), _rgba_for_color(image.get_at((col, row))[:3], clear_color))
	return image

def load_images(image_names, transparent = False):
	''' Load a list of images. Usually used for loading animation frames. '''
	images = []
	for name in image_names:
		images.append(load_image(name, transparent))
	return images

# Scene
# The Scene class is the core of each game. It handles user input, updating objects on the screen, and general game flow
class Scene(object):
	''' A game scene which can contain sprites, text, etc. '''
	def __init__(self, width, height):
		self.width = width
		self.height = height
		self._screen = pygame.display.set_mode((width, height), DOUBLEBUF)
		self._clock = pygame.time.Clock()
		self._key = None
		self._background = None
		self._objects = []
		self._timers = []
		self._running = False
		self._paused = False # If True, object update methods will not be called
		pygame.mouse.set_visible(False)

	def set_background(self, image):
		''' Set the scene background image. '''
		self._background = image

	def _handle_events(self):
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				self._key = event.key
			elif event.type == KEYUP:
				self._key = None
			elif event.type == QUIT:
				self.quit()

	# sort - Sort the screen objects by z_order
	def sort(self):
		self._objects = sorted(self._objects,key=lambda o: o.z_order)
		self._objects.reverse()

	# add - Add an object to the scene
	def add(self, obj):
		obj.scene = self
		self._objects.append(obj)
		self.sort()

	# remove - Remove an object from the scene
	def remove(self, object):
		if object in self._objects:
			self._objects.remove(object)

	# clear - Clear the entire scene
	def clear(self):
		self._objects = []

	# add_timer - Add a timer object for the scene to update
	def add_timer(self, timer):
		self._timers.append(timer)
		timer.scene = self

	# remove_timer - Remove a timer object from the update cycle
	def remove_timer(self, timer):
		self._timers.remove(timer)

	# clear_timers - Remove all timers from the update cycle
	def clear_timers(self):
		self._timers = []

	# key_pressed - Returns True if the key (from pygame constants) is currently pressed. False otherwise.
	def key_pressed(self, key):
		return (self._key == key)

    # mouse_pos - Returns a tuple with x and y coordinates of mouse cursor
	def mouse_pos(self):
		return pygame.mouse.get_pos()

	# mouse_pressed - Returns True if the indicated button (from pygame constants) is currently pressed. False otherwise
	def mouse_pressed(self, button):
		return pygame.mouse.get_pressed()[button]

	# get_joystick - If a joystick is connected, return the joystick instance
	def get_joystick(self):
		if len(joysticks) > 0:
			if not joysticks[0].get_init():
				joysticks[0].init()
			return joysticks[0]
		else:
			return None

	# play_sfx - Play a one-shot sound effect
	def play_sfx(self, filename):
		try:
			sfx = pygame.mixer.Sound(filename)
			sfx.play()
		except:
			print 'Unable to play sound file "' + filename + '"'

	# overlapping_objects - Returns a list of all objects whose bounding box intersects the given object's box
	def overlapping_objects(self, object):
		''' Create a list of all objects that are collideable and are touching an object. '''
		overlapping = []
		for o in self._objects:
			if object._get_rect().colliderect(o._get_rect()) and o != object and o.collideable:
				overlapping.append(o)
		return overlapping

	# pause - Pause updates of the scene
	def pause(self):
		self._paused = True

	# unpause - Resume updates of the scene
	def unpause(self):
		self._paused = False

	# begin - Start the scene (default fps is 60)
	def begin(self, fps = 60):
		self._running = True
		self._loop(fps)

	# quit - End the main loop and stop any Timer objects.
	#        Must stop Timer objects since they are on separate threads.
	def quit(self):
		self._running = False
		for o in self._objects:
			if isinstance(o, Timer):
				o.stop()

	# _loop - Updates the entire game state for one tick
	def _loop(self, fps):
		# Initialize the lastTime variable. Tracks the time of the last frame update
		lastTime = time.time()
		while self._running:
			self._clock.tick(fps) # Hang until at least 1/fps seconds have elapsed

			self._handle_events() # Update user input events

			# Compute delta_time, the time elapsed between this frame and the last frame
			delta_time = time.time() - lastTime

			# Update the time of the last frame update
			lastTime = time.time()

			# If the scene is not paused, update all the objects and timers
			if not self._paused:
				for object in self._objects:
					object.update(delta_time)
				for timer in self._timers:
					timer._update_timer(delta_time)

			# Erase the screen
			self._screen.fill((0,0,0))

			# If the background has been set, put it on the screen
			if self._background != None:
				self._screen.blit(self._background, self._background.get_rect())

			# Display each object on the screen
			for object in self._objects:
				self._screen.blit(object.surface, object._get_rect())

			# Update the display buffer
			pygame.display.flip()

class Object(object):
	''' An object in the scene. '''
	def __init__(self, x, y, collideable = True):
		self.x = x          # x coordinate of sprite center
		self.y = y          # y coordinate of sprite center
		self.width = 0      # width in pixels
		self.height = 0     # height in pixels
		self._xoffset = 0   # x offset (half of width)
		self._yoffset = 0   # y offset (half of height)
		self._surface = pygame.Surface((0, 0)) # surface to be displayed
		self.rotation = 0   # Angle of rotation
		self.scene = None   # Parent scene
		self._z_order = 0   # z_order sorting
		self.collideable = collideable # True if this object should be able to collide with others

	# _get_rect - Grab this object's bounding box on the screen
	def _get_rect(self):
		return pygame.Rect(self.x-self._xoffset, self.y-self._yoffset, self.width, self.height)

	# update - Called by the scene every frame update
	def update(self, delta_time):
		pass

	# destroy - Remove this object from its parent scene
	def destroy(self):
		self.scene.remove(self)

	# key_pressed - Convenience method for access to parent scene's key_pressed method
	def key_pressed(self, key):
		return self.scene.key_pressed(key)

	# mouse_pos - Convenience method for access to parent scene's mouse_pos method
	def mouse_pos(self):
		return self.scene.mouse_pos()

	# mouse_pressed - Convenience method for access to parent scene's mouse_pressed method
	def mouse_pressed(self, button):
		return self.scene.mouse_pressed(button)

	# Setup surface getters and setters since we need to update the x and y offsets if it changes
	def getsurface(self):
		return pygame.transform.rotate(self._surface, self.rotation)

	def setsurface(self, surface):
		self._surface = surface
		self.width = self._surface.get_rect().width
		self.height = self._surface.get_rect().height
		self._xoffset = self.width/2
		self._yoffset = self.height/2

	surface = property(getsurface, setsurface)

	# Setup z_order getters and setters since we need to resort the scene if it changes
	def getzorder(self):
		return self._z_order

	def setzorder(self, z_order):
		self._z_order = z_order
		if self.scene:
			self.scene.sort()

	z_order = property(getzorder, setzorder)

class Sprite(Object):
	''' An object with an image. '''
	def __init__(self, x, y, image, collideable = True):
		Object.__init__(self, x, y, collideable)
		self.image = image  # Image for this sprite
		self.scene = None   # Parent scene

	# Image getters and setters since we need to update the surface when the image is set
	def setimage(self, image):
		self._image = image
		self.surface = self._image

	def getimage(self):
		return self._image

	image = property(getimage, setimage)

	# overlapping_objects - Returns a list of all objects whose bounding boxes overlap that of this sprite
	def overlapping_objects(self):
		return self.scene.overlapping_objects(self)

class Timer(object):
	''' A timer. '''
	def __init__(self, interval):
		self.interval = interval # Seconds between ticks
		self._running = True     # True if the timer is active
		self._counter = 0        # Counter for tracking elapsed time
		self.scene = None        # Parent scene

	def _update_timer(self , delta_time):
		if self._running:
			# Increment the counter
			self._counter += delta_time

			# See if the required time has elapsed
			# If so, then call the tick() function
			if self._counter > self.interval:
				self._counter = 0
				self.tick()

	def tick(self):
		# Override in subclass
		pass

	# stop - Stop the timer from ticking
	def stop(self):
		self._running = False

	# start - Start the timer
	def start(self):
		self._running = True

class Delay(object):
	''' Executes a function after a delay. '''
	def __init__(self, delay, function):
		self.function = function    # Function to perform after delay
		self.delay = delay          # Length of delay
		self._timer = threading.Timer(self.delay, self.function) # threading.Timer object to execute delay

	# start - Begins the delay, then runs function afterward
	def start(self):
		self._timer.start()

class Font(object):
	''' A font to be used in the game. '''
	def __init__(self, filename, size):
		self._font = pygame.font.Font(filename, size) # Load and create the font

class Text(Object):
	''' A string of text that can be displayed in a scene. '''
	def __init__(self, x, y, font, text, color = (255, 255, 255)):
		Object.__init__(self, x, y, False)
		self._font = font._font     # Font to be used
		self._text = text           # String of text
		self._color = color         # Color of text
		self.surface = self._font.render(self._text, True, self._color) # Render the text to the surface

	# Text getters and setters since we need to re-render the text when it changes
	def gettext(self):
		return self._text

	def settext(self, value):
		self._text = value
		self.surface = self._font.render(self._text, True, self._color)

	text = property(gettext, settext)

	# Font getters and setters since we need to re-render when the font changes
	def getfont(self):
		return self._font

	def setfont(self, value):
		self._font = value
		self.surface = self._font.render(self._text, True, self._color)

	font = property(getfont, setfont)

	# Color getters and setters since we need to re-render when the color changes
	def getcolor(self):
		return self._color

	def setcolor(self, value):
		self._color = value
		self.surface = self._font.render(self._text, True, self._color)

	color = property(getcolor, setcolor)

class Animation(Sprite, Timer):
	''' An animation sequence. '''
	def __init__(self, x, y, images, repeating = False, fps = 15.0):
		Sprite.__init__(self, x, y, images[0], collideable = False)
		Timer.__init__(self, 1.0 / fps)
		self.images = images            # List of images in sequence
		self._frame = 0                 # Index of current frame displayed
		self._repeating = repeating     # True if the animation should loop
		self.image = self.images[self._frame] # Initialize the first frame

	# tick - Called by the Timer superclass after the delay between frames has elapsed
	def tick(self):
		# Increment frame index
		self._frame += 1

		# Check if all the frames have been shown
		if self._frame > len(self.images)-1:
			# If so, and the animation should not loop, then destroy this object
			if not self._repeating:
				self.stop()
				self.destroy()
				return
			# Otherwise, reset the frame index to 0
			self._frame = 0

		# Update the image with the next frame
		self.image = self.images[self._frame]

	# update - Animations must be sure to update their timer to keep animating
	def update(self, delta_time):
		self._update_timer(delta_time)
