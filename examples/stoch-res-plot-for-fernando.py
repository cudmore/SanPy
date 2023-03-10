"""
summary plot for stochastic responance

making this by hand for fernando and his talks
"""
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

plt.style.use('dark_background')

x = [1,2,3,4,5]
y = [0.56, 0.71, 0.42, 0.25, 0.255]

ax = plt.subplot(111)
ax.plot(x,y, 'o-', lw=4)

ax.set_ylim([0, 1])

# plt.xlabel('xlabel', fontsize=18)
# plt.ylabel('ylabel', fontsize=16)

# changing the fontsize of yticks
plt.xticks(fontsize=24)
plt.yticks(fontsize=24)

#ax = plt.figure().gca()
ax.xaxis.set_major_locator(MaxNLocator(integer=True))

# Hide the right and top spines
ax.spines.right.set_visible(False)
ax.spines.top.set_visible(False)

plt.show()