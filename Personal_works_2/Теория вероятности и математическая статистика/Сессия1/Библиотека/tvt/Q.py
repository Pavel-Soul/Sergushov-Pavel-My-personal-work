from IPython import display

from .Q1 import mas as q1
from .Q2 import mas as q2
from .Q3 import mas as q3


def show(text):
    display.display(display.Markdown(text))


mas = q1 + q2 + q3


def f(info):
    if isinstance(info, int):
        show(info)
    if isinstance(info, list):
        show((q1, q2, q3)[info[0]][info[1]])
    else:
        for text in mas:
            if info in text:
                show(text)
