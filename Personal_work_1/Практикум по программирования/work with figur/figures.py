class Figure:
    coords = np.array([])

    def __init__(self, x, y, *side):
        if len(side) > 1:
            a = np.array([x, y])
            b = np.array(side[:2])
            # b справа
            if x > b[0]:
                a, b = b, a
            if x == b[0] and y > b[1]:
                a, b = b, a
            v = b-a
            self.side = sum(v**2)**0.5
            if v[0] == 0:
                angle = 90
            else:
                angle = np.math.atan(v[1]/v[0])*180/pi
            if side[2] == 0:
                self.set_coords(*a, self.side)
                self.rotate(angle, *a)
            else:
                self.set_coords(*b, self.side)
                self.rotate(angle-180, *b)
        else:
            self.side = side[0]
            self.set_coords(x, y, self.side)

    def set_coords(self):
        ...

    def draw(self, ax, color='cyan'):
        poly = Polygon(self.coords, fill=True, closed=True, color=color)
        ax.add_patch(poly)

    def rotate(self, angle, x=0, y=0):
        mat = np.array([
            [np.math.cos(angle*pi/180), -np.math.sin(angle*pi/180)],
            [np.math.sin(angle*pi/180), np.math.cos(angle*pi/180)]
        ])
        for n, cors in enumerate(self.coords):
            self.coords[n] = (mat @ (cors - [x, y])) + [x, y]

    def mirror(self, x=False, y=False):
        if x:
            self.coords[:, 0] *= -1
        if y:
            self.coords[:, 1] *= -1

    def move(self, x, y):
        self.coords[:, 0] += x
        self.coords[:, 1] += y

    def gom(self, delta):
        self.coords = self.coords / delta

    def dif(self, x, y):
        cors = self.coords
        center = cors.sum(0)/cors.shape[0]
        # True если точка внутри фигуры
        #! Находим расстояния до всех вершин фигуры
        l = ((cors - [x, y])**2).sum(axis=1)**0.5
        #! Сортируем точки по возрастанию расстояния
        c = cors[np.argsort(l)]
        #! Находим ближайший вектор
        v = c[1] - c[0]
        #! Проецируем точку на отрезок по Y
        if v[0] != 0:
            dot_shift = (x-c[0, 0])*v[1]/v[0]+c[0, 1] - y
            center_shift = (center[0]-c[0, 0])*v[1]/v[0]+c[0, 1] - center[1]
        else:
            dot_shift = x*v[0]/v[1]+c[0, 0] - x
            center_shift = center[1]*v[0]/v[1]+c[0, 0] - center[0]
        #! Определяем одинаковый ли по знаку сдвиг
        # ? 0 - сдвига небыло
        return dot_shift * center_shift > 0

    def is_cross(self, fi, first=True):
        # Проверяем лежит ли хоть одна из наших точек в другой фигуре
        center = self.coords.sum(0)/self.coords.shape[0]
        for x, y in self.coords:
            if fi.dif(x, y):
                return True
        if fi.dif(*center):
            return True

        if first:
            return fi.is_cross(self, False)
        return False
