"""
Unshred image using PIL.
========================

Courtesy of Instagram : http://instagram-engineering.tumblr.com/post/12651721845/instagram-engineering-challenge-the-unshredder

This algorithm is very simple, it splits an image using shred objects.
It starts from the left shred, searching the fitting shred on its right.

Algorithm
---------

I adopt a naive algorithm (with no signal theory).

I compare each time one shred with every other shreds not ordered yet.

If two shreds are very similar on their border, they must be consequently neighbor.
So I just compare pixels of their border. The current implementation can use a mean approach
with the border pixels to not just compare one pixel at a time but more. Some tests show that 3 pixels by
each side is a good value (it also depends of the shred's width).

E[P(x-2)P(x-1)P(x)] | E[P(x+1)P(x+2)P(x+3)]

        E1                  E2

We subtract E1 and E2 (the closer they are, the more the result is close to 0).
We iterate through the whole height (an optimization can be done here to only test some points).
It gives us a score that we can compare.

The final smaller score is the neighbor. With this algorithm, we can find neighbor.

Strategy
--------

For example (the good order is the crescent order):

4 -> 5 -> 1 -> 2 -> 3

So in this example 5 is the right border and 1 is the left border.
The algorithm starts with :

who is the right side of '4'.
We found 5.
We perform an inverse search to found the left side of 5. It is 4. We can continue.
4 -> 5

who is the right side of '5'
We found '2' (can be anything, it will find something but this is meaningless, it is an edge case not solved here).
We perform an inverse search which is not 2 (if we are unlucky, it is 2 again, another edge case here, not solved).
So we can nearly say (see edge case) that '5' is the right border.

We reverse the current order to perform an inverse search. We do not need to validate left side now.
5 -> 4

Who is the left side of '4'
We found '3'.
5 -> 4 -> 3

And so on ...

5 -> 4 -> 3 -> 2 -> 1

Finally we reverse again.

1 -> 2 -> 3 -> 4 -> 5

It works.

It can fail if it is unable to determine a neighbor (it will wrongly determine a border).

Plus
----

Performance tip: all scoring is done with color (+alpha) tuple. It can be avoided to gain speed and memory to just sum them into a single int.

"""

__author__ = "Samy Duc"
__email__ = "samy.duc@gmail.com"

import sys
import getopt

from PIL import Image

# fixed
VAR_SHRED_WIDTH = 32
# number used to compute number of pixel to do average on a side, heavily depends on the image ration
VAR_MAGIC_NUMBER = 3
# start the algorithm with the given shred (left to right)
VAR_START_WITH = 0

class Shred(object):
	"""
	Describe a shred object.

	"""

	def __init__(self, image, width, x, number):
		"""
		Init a shred.

		x means bottom left of the shred.
		number means original position in shredded image.

		"""

		self.image = image
		self.data = self.image.getdata()

		self.width = width
		self.x = x
		self.number = number

		# number of point to do an average pixel
		self.magic_average = VAR_MAGIC_NUMBER

	def __repr__(self):
		"""
		Repr.

		"""

		return str(self.number)

	def get_pixel_value(self, x, y):
		"""
		Get pixel value given a position, courtesy of Instagram.

		"""

		width, height = self.image.size
		pixel = self.data[y * width + x]
		return pixel

	def get_average_pixel(self, pixel_1, pixel_2):
		"""
		Get two pixels and compute an average.

		"""

		average = []

		for x, y in zip(pixel_1, pixel_2):
			average.append((x + y) / 2)

		return average

	def get_right_pixels(self, y):
		"""
		Given a height, get the average right pixel.

		"""

		pixels = []

		for i in range(0, self.magic_average):
			pixels.append(self.get_pixel_value(self.x + self.width - (i+1), y))

		average_pixel = reduce(self.get_average_pixel, pixels)

		return average_pixel

	def get_left_pixels(self, y):
		"""
		Given a height, get the average left pixel.

		"""

		pixels = []

		for i in range(0, self.magic_average):
			pixels.append(self.get_pixel_value(self.x + i, y))

		average_pixel = reduce(self.get_average_pixel, pixels)

		return average_pixel

class Shreddator(object):
	"""
	Unshred image.

	"""

	def __init__(self, source_path, destination_path):
		"""
		Init Shreddator.

		"""

		self.source_path = source_path
		self.destination_path = destination_path

		self.source_image = Image.open(self.source_path)
		self.source_data = self.source_image.getdata()

		# result will be here
		self.shred_ordered =[]

		# fixed value
		self.shred_width = VAR_SHRED_WIDTH
		self.shred_height =  self.source_image.size[1]

		# determine number of shredded part -> naive approach
		self.nb_column = self.source_image.size[0] / self.shred_width
		self.shred_list = [Shred(self.source_image, self.shred_width, i*self.shred_width, i) for i in range(self.nb_column)]

	def compare_shred(self, shred_left, shred_right):
		"""
		Compare two shreds.

		Returned score is smaller if shred_left is probably the left neighbor of shred_right.

		"""

		# initialize scoring
		score = 0

		for y in range(self.source_image.size[1]):
			# compare left pixel and right pixel with tolerance
			pixel_left = shred_left.get_right_pixels(y)
			pixel_right = shred_right.get_left_pixels(y)

			# score is a flat number (clarity)
			score += abs(pixel_left[0] - pixel_right[0]) \
					+ abs(pixel_left[1] - pixel_right[1]) \
					+ abs(pixel_left[2] - pixel_right[2]) \
					+ abs(pixel_left[3] - pixel_right[3]) 

		return score

	def find_neighbor(self, seek_right, shred):
		"""
		Find the next shred given a direction.

		"""

		global_score = {}

		for targeted_shred in self.shred_list:

			if targeted_shred.x == shred.x or targeted_shred in self.shred_ordered:
				# same shred or already ordered, do not compare
				continue

			if seek_right:
				score = self.compare_shred(shred, targeted_shred)
			else:
				score = self.compare_shred(targeted_shred, shred)

			global_score[targeted_shred.number] = score

		# the side is given by the lowest score
		index = min(global_score, key=global_score.get)
		
		return self.shred_list[index]

	def find_right(self, left_shred):
		"""
		Find the right shred for the given shred.

		"""
		
		return self.find_neighbor(True, left_shred)

	def find_left(self, right_shred):
		"""
		Find the right shred for the given shred.

		"""

		return self.find_neighbor(False, right_shred)

	def order_shred(self, seek_right, shred):
		"""
		Complete the shred_orderer list in the given direction.

		"""

		# exit condition
		loop = True

		if seek_right:
			local_find = self.find_right
		else:
			local_find = self.find_left

		while(len(self.shred_ordered) < len(self.shred_list) and loop):
			# search neighbor while all shred are not ordered
			current_shred = local_find(shred)

			# must not be possible
			assert(current_shred not in self.shred_ordered)

			if seek_right:
				# check if it is a good fit with its left side
				left_shred = self.find_left(current_shred)

				if left_shred.x != shred.x:
					# it is the right border
					loop = False

			self.shred_ordered.append(current_shred)
			shred = current_shred

	def compute(self):
		"""
		Start the logic here.

		"""

		# peek the first shred to start
		self.shred_ordered.append(self.shred_list[VAR_START_WITH])
		# order from left to right
		self.order_shred(True, self.shred_ordered[-1])
		# reverse to order from right to left
		self.shred_ordered.reverse()
		self.order_shred(False, self.shred_ordered[-1])
		# reverse again to get the original order
		self.shred_ordered.reverse()
	
	def save(self):
		"""
		Save unshredded image, courtesy of Instagram.

		"""

		unshredded = Image.new("RGBA", self.source_image.size)
		destination_point = (0, 0)

		for shred in self.shred_ordered:
			source_region = self.source_image.crop((shred.x, 0, shred.x + shred.width, self.source_image.size[1]))
			unshredded.paste(source_region, destination_point)
			destination_point = (destination_point[0] + shred.width, 0)

		unshredded.save(self.destination_path, "PNG")


def usage():
	"""
	Print command line usage.

	"""

	print('Usage: -s source_file -d destination_file')      


if __name__ == "__main__" :
	# entry point with command line interface

	try:                                
		opts, args = getopt.getopt(sys.argv[1:], "hs:d:", ["help", "source=", "destination="])
	except getopt.GetoptError:          
		usage()                 
		sys.exit(1)

	source = None
	destination = None

	for opt, arg in opts:
		if opt in ("-s", "--source"):
			source = arg
		elif opt in ("-d", "--destination"):
			destination = arg
		elif opt in ("-h", "--help"):
			usage()                
			sys.exit(1)

	if source and destination:
		# everything needed is here
		shred = Shreddator(source, destination)
		shred.compute()
		shred.save()
	else:
		# exit
		usage()
		sys.exit(1)
		
	 