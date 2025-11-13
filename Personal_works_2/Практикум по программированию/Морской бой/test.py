from tkinter import *
import matplotlib.pyplot as plt
import tkinter as tk
import time

from matplotlib.backends.backend_tkagg import *

# create the main window
root = Tk()
# title at the top of the window
root.title("MT5 Socket Server Vital$oft(c) 2023")
# main window dimensions
root.geometry("1280x600")
# main window color
root["bg"] = "gainsboro"
# create a frame for the chart
frameUp = Frame(root, borderwidth=1, relief=RAISED)
# frame location
frameUp.place(x=10, y=100, width=1260, height=450)
# create a figure
figure = plt.Figure(figsize=(6, 4), dpi=100, facecolor="gainsboro")
# create FigureCanvasTkAgg object
figure_canvas = FigureCanvasTkAgg(figure, master=frameUp)
# create the toolbar
toolbar = NavigationToolbar2Tk(figure_canvas, root)
# toolbar['bg'] = 'gainsboro'
toolbar.update()
# create axes
# axes = figure.add_subplot(1, 1, 1)
axes = figure.subplots()
# to draw the second line
axes2 = axes.twinx()
# background graphics black
axes.set_facecolor("black")
widg = figure_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)


# draw lines based on the received data
# socket 1
def graph1(X, Y):
    # clear
    axes.clear()
    # grid
    # axes.grid()
    # line draw
    axes.plot(X, Y, color="red", linewidth=1)
    figure.canvas.draw_idle()
    figure.canvas.flush_events()
    time.sleep(0.02)


# socket 2
def graph2(X, Y):
    # clear
    axes2.clear()
    # grid
    # axes.grid()
    # line draw
    axes2.plot(X, Y, color="blue", linewidth=1)
    figure.canvas.draw_idle()
    figure.canvas.flush_events()
    time.sleep(0.02)
