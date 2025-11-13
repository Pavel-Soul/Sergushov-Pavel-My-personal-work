import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from cmath import polar, rect, pi

data = {"width": 700, "height": 300, "th": 70, "scale": 0, "car": None}
app = tk.Tk()
canvas = tk.Canvas(width=data["width"], height=data["height"], bg="white")
canvas.pack()
scale = 0
canvas.create_arc(
    data["th"],
    data["th"],
    data["height"] - data["th"],
    data["height"] - data["th"],
    start=90,
    extent=180,
    width=data["th"],
    style="arc",
    outline="grey",
)
canvas.create_arc(
    data["width"] - (data["height"] - data["th"]),
    data["th"],
    data["width"] - data["th"],
    data["height"] - data["th"],
    start=-90,
    extent=180,
    width=data["th"],
    style="arc",
    outline="grey",
)
canvas.create_rectangle(
    data["height"] / 2,
    data["th"] / 2,
    data["width"] - data["height"] / 2,
    data["th"] * 1.5,
    fill="grey",
    outline="grey",
)
canvas.create_rectangle(
    data["height"] / 2,
    data["height"] - data["th"] / 2,
    data["width"] - data["height"] / 2,
    data["height"] - data["th"] * 1.5,
    fill="grey",
    outline="grey",
)


def give_car(angle=0):
    if data["car"] is None:
        # raw_image_car = Image.open("./car.png")
        raw_image_car = Image.open(r"D:\DISTR\Загрузки\iMe Desktop\car.png")
        data["scale"] = data["scale"] or raw_image_car.height / data["th"]
        data["car"] = raw_image_car.resize(
            (np.array(raw_image_car.size) / data["scale"]).astype(int)
        )
    data["imcar"] = ImageTk.PhotoImage(data["car"].rotate(angle))
    return data["imcar"]


def move_car(car):
    x, y = canvas.coords(car)

    if data["height"] / 2 < x < data["width"] - data["height"] / 2:
        shift = (y < data["height"] / 2) * 2 - 1
        canvas.move(car, shift * 2, 0)
    else:
        le = pi * data["height"]
        yc = data["height"] / 2
        if x > data["width"] / 2:
            xc = data["width"] - data["height"] / 2
        else:
            xc = data["height"] / 2
        x = x - xc
        y = y - yc
        r, phi = polar(complex(x, y))
        p = phi
        part = phi / pi
        phi = (le * part + 10) / le * pi
        co = rect(r, phi)

        _image_car = give_car(-90 - (p * 180 / pi))
        car = canvas.create_image(x + xc, y + yc, image=_image_car)
        canvas.move(car, co.real - x, co.imag - y)

    app.after(10, move_car, car)


car = canvas.create_image(data["width"] / 2, data["th"], image=give_car())
move_car(car)
app.mainloop()
