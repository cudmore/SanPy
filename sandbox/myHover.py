import matplotlib.pyplot as plt
import mplcursors
import numpy as np

if 0:

	labels = ["a", "b", "c", "d", "e"]
	x = np.array([0, 1, 2, 3, 4])

	fig, ax = plt.subplots()
	line, = ax.plot(x, x, "ro")
	mplcursors.cursor(ax).connect(
		"add", lambda sel: sel.annotation.set_text(labels[sel.target.index]))

	plt.show()

if 1:
	np.random.seed(42)

	fig, ax = plt.subplots()
	right_artist = ax.scatter(*np.random.random((2, 26)))
	ax.set_title("Mouse over a point")

	#mplcursors.cursor(hover=True)

	# Make the box have a white background with a fancier connecting arrow
	c2 = mplcursors.cursor(right_artist, hover=True)
	@c2.connect("add")
	def _(sel):
		sel.annotation.get_bbox_patch().set(fc="white")
		sel.annotation.arrow_patch.set(arrowstyle="simple", fc="white", alpha=.5)
		# row in df is from sel.target.index
		print('sel.target.index:', sel.target.index)
		sel.annotation.set_text(sel.target.index)

	plt.show()
