import matplotlib.pyplot as plt
import matplotlib.lines as lines

class draggable_lines:
	def __init__(self, ax, xPos, yPos, hLength=5, vLength=20, linewidth=3, color='m', doPick=False):
		self.ax = ax
		self.c = ax.get_figure().canvas

		self.hLineLength = hLength
		self.vLineLength = vLength

		# horz line
		x = [xPos, xPos+hLength]
		y = [yPos, yPos]
		self.hLine = lines.Line2D(x, y, linewidth=linewidth, c=color, picker=5)
		self.ax.add_line(self.hLine)

		# vert line
		x = [xPos, xPos]
		y = [yPos, yPos+vLength]
		self.vLine = lines.Line2D(x, y, linewidth=linewidth, c=color, picker=None)
		self.ax.add_line(self.vLine)

		self.c.draw_idle()
		self.sid = self.c.mpl_connect('pick_event', self.clickonline)

	def clickonline(self, event):
		if event.artist == self.hLine:
			print("line selected ", event.artist)
			self.follower = self.c.mpl_connect("motion_notify_event", self.followmouse)
			self.releaser = self.c.mpl_connect("button_press_event", self.releaseonclick)

	def followmouse(self, event):
		self.hLine.set_ydata([event.ydata, event.ydata])
		self.hLine.set_xdata([event.xdata, event.xdata + self.hLineLength])
		# a second line print('Vline is vertical')
		self.vLine.set_xdata([event.xdata, event.xdata])
		self.vLine.set_ydata([event.ydata, event.ydata + self.vLineLength])

		self.c.draw_idle()

	def releaseonclick(self, event):
		self.c.mpl_disconnect(self.releaser)
		self.c.mpl_disconnect(self.follower)

fig = plt.figure()
ax = fig.add_subplot(111)
Hline = draggable_lines(ax, 10, 10, hLength=5, vLength=20, linewidth=3, doPick=True)

ax.set_xlim(0,50)
ax.set_ylim(0,50)

plt.show()
