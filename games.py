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
	''' Return an rgba list given an rgb list and the color which should be made transparent. '''
	if color == clear_color:
		return (0, 0, 0, 0)
	else:
		r,g,b = color
		return (r,g,b, 255)

def load_image(name, transparent = False):
	''' Load a bitmap image with filename of name. If the second argument is True, all pixels the smae color as that in the top, left corner will be made transparent.'''
	image = pygame.image.load(name).convert_alpha()
	if transparent:
		clear_color = image.get_at((0, 0))[:3]
		for row in range(image.get_height()):
			for col in range(image.get_width()):
				image.set_at((col, row), _rgba_for_color(image.get_at((col, row))[:3], clear_color))
	return image


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

	def sort(self):
		self._objects = sorted(self._objects,key=lambda o: o.z_order)
		self._objects.reverse()

	def add(self, obj):
		obj.scene = self
		self._objects.append(obj)
		self.sort()
				

	def remove(self, object):
		try:
			self._objects.remove(object)
		except:
			pass


	def add_timer(self, timer):
		self._timers.append(timer)
		timer.scene = self

	def remove_timer(self, timer):
		self._timers.remove(timer)

	def key_pressed(self, key):
		return (self._key == key)

	def mouse_pos(self):
		return pygame.mouse.get_pos()

	def mouse_pressed(self, button):
		return pygame.mouse.get_pressed()[button]

	def get_joystick(self):
		if len(joysticks) > 0:
			if not joysticks[0].get_init():
				joysticks[0].init()
			return joysticks[0]
		else:
			return None

	def play_sfx(self, filename):
		try:
			sfx = pygame.mixer.Sound(filename)
			sfx.play()
		except:
			print 'Unable to play sound file "' + filename + '"'

	def overlapping_objects(self, object):
		''' Create a list of all objects that are collideable and are touching an object. '''
		overlapping = []
		for o in self._objects:
			if object._get_rect().colliderect(o._get_rect()) and o != object and o.collideable:
				overlapping.append(o)
		return overlapping

	def pause(self):
		self._paused = True

	def unpause(self):
		self._paused = False

	def begin(self, fps = 40):
		self._running = True
		lastTime = time.time()

		while self._running:
			self._clock.tick(fps)
		
			self._handle_events()
			deltaTime = time.time() - lastTime
			lastTime = time.time()
			if not self._paused:	
				for object in self._objects:
					object.update(deltaTime)
				for timer in self._timers:
					timer._update_timer()

			self._screen.fill((0,0,0))
			if self._background != None:
				self._screen.blit(self._background, self._background.get_rect())
			for object in self._objects:
				self._screen.blit(object.surface, object._get_rect()) 
			pygame.display.flip()

	def quit(self):
		self._running = False
		for o in self._objects:
			if isinstance(o, Timer):
				o.stop()
class Object(object):
	''' An object in the scene. '''
	def __init__(self, x, y, collideable = True):
		self.x = x
		self.y = y
		self.width = 0
		self.height = 0
		self._xoffset = 0
		self._yoffset = 0
		self._surface = pygame.Surface((0, 0))
		self.rotation = 0
		self.scene = None
		self._z_order = 0
		self.collideable = collideable

	def _get_rect(self):
		return pygame.Rect(self.x-self._xoffset, self.y-self._yoffset, self.width, self.height)

	def update(self):
		pass

	def destroy(self):
		self.scene.remove(self)

	def key_pressed(self, key):
		return self.scene.key_pressed(key)

	def mouse_pos(self):
		return self.scene.mouse_pos()

	def mouse_pressed(self, button):
		return self.scene.mouse_pressed(button)
	
	def getsurface(self):
		return pygame.transform.rotate(self._surface, self.rotation)

	def setsurface(self, surface):
		self._surface = surface
		self.width = self._surface.get_rect().width
		self.height = self._surface.get_rect().height
		self._xoffset = self.width/2
		self._yoffset = self.height/2

	surface = property(getsurface, setsurface)

	def getzorder(self):
		return self._z_order

	def setzorder(self, z_order):
		self._z_order = z_order
		if self.scene:
			self.scene.sort()

	z_order = property(getzorder, setzorder)

class Sprite(Object):
	def __init__(self, x, y, image, collideable = True):
		Object.__init__(self, x, y, collideable)
		self.image = image
		self.scene = None

	def setimage(self, image):
		self._image = image
		self.surface = self._image

	def getimage(self):
		return self._image

	image = property(getimage, setimage)

	def overlapping_objects(self):
		return self.scene.overlapping_objects(self)

class Timer(object):
	def __init__(self, interval):
		self.interval = interval
		self._running = True
		self._counter = 0
		self.scene = None

	def _update_timer(self):
		if self._running:
			self._counter += 1
			if self._counter > self.interval:
				self._counter = 0
				self.tick()
		
	def tick(self):
		pass

	def stop(self):
		self._running = False

class Delay(object):
	def __init__(self, function, delay):
		self.function = function
		self.delay = delay
		threading.Timer(self.delay, self.function).start()

class Font(object):
	def __init__(self, filename, size):
		self._font = pygame.font.Font(filename, size)

class Text(Object):
	def __init__(self, x, y, font, text, color = (255, 255, 255)):
		Object.__init__(self, x, y, False)
		self._font = font._font
		self._text = text
		self._color = color
		self.surface = self._font.render(self._text, True, self._color)
	
	def gettext(self):
		return self._text

	def settext(self, value):
		self._text = value
		self.surface = self._font.render(self._text, True, self._color)

	text = property(gettext, settext)


	def getfont(self):
		return self._font

	def setfont(self, value):
		self._font = value
		self.surface = self._font.render(self._text, True, self._color)

	font = property(getfont, setfont)

	def getcolor(self):
		return self._color

	def setcolor(self, value):
		self._color = value
		self.surface = self._font.render(self._text, True, self._color)

	color = property(getcolor, setcolor)

class Animation(Sprite, Timer):
	def __init__(self, x, y, image_names, repeating = False, frame_time = 1):
		Sprite.__init__(self, x, y, None, collideable = False)
		Timer.__init__(self, frame_time)
		self.images = []
		self._frame = 0
		self._repeating = repeating
		for name in image_names:
			self.images.append(load_image(name, True))
		self.image = self.images[self._frame]

	def tick(self):
		self._frame += 1
		if self._frame > len(self.images)-1:
			if not self._repeating:
				self.stop()
				self.destroy()
				return
			self._frame = 0
		self.image = self.images[self._frame]

	def update(self):
		self._update_timer()