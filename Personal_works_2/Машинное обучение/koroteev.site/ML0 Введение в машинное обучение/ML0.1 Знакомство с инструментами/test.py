import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots()
pos = [0.1, 0.3]
add = np.array([0.01, 0.03])
r = 0.1
circle = plt.Circle(pos, r, fill="white")
ax.set_aspect(1)
ax.add_artist(circle)
plt.ion()
while True:
    pos += add
    circle.center = pos
    if abs(round(pos[0], 3) - 0.5) * 2 >= 1 - r * 2:
        add[0] *= -1
    if abs(round(pos[1], 3) - 0.5) * 2 >= 1 - r * 2:
        add[1] *= -1

    plt.pause(0.014)
plt.show()
