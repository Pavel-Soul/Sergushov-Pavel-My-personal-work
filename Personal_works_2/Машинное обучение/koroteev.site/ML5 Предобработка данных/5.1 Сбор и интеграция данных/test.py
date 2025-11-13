import PySimpleGUI as sg
import random

layout = [
    [
        sg.Button(
            "Новое число", enable_events=True, key="-FUNCTION-", font="Helvetica 16"
        )
    ],
    [sg.Text("Результат:", size=(25, 1), key="-text-", font="Helvetica 16")],
]

window = sg.Window("Генератор случайных чисел", layout, size=(350, 100))


def update():
    r = random.randint(1, 100)
    text_elem = window["-text-"]
    text_elem.update("Результат: {}".format(r))


if __name__ == "__main__":
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break
        if event == "-FUNCTION-":
            update()
    window.close()
