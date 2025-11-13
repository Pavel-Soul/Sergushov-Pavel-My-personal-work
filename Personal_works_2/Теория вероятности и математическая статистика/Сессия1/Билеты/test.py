import tkinter as tk

root = tk.Tk()
root.title("Текстовый редактор")

FONT = "Arial 14"
LINE_SPACE = 1


scrollbar = tk.Scrollbar()
scrollbar.pack(side="right", fill="y")

text_widget = tk.Text(root, spacing1=LINE_SPACE, font=FONT)
text_widget.pack(side="right", expand=True, fill="both")
text_widget.focus_set()

line_numbers = tk.Text(
    root,
    bg="#f0f0f0",
    fg="black",
    width=4,
    bd=0,
    highlightthickness=0,
    spacing1=LINE_SPACE,
    font=FONT,
)
line_numbers.pack(side="left", fill="y")


def on_update(event):
    line_numbers.delete(1.0, "end")
    lines = text_widget.get(1.0, "end-1c").split("\n")
    for i, lines in enumerate(lines, 1):
        line_numbers.insert("end", str(i) + "\n")


def on_scrollbar(*args):
    """прокручивает оба текста при скроллинге"""
    line_numbers.yview(*args)
    text_widget.yview(*args)


def on_textscroll(*args):
    """передача аргумента скроллинга"""
    scrollbar.set(*args)
    on_scrollbar("moveto", args[0])


text_widget.bind("<KeyRelease>", on_update)

scrollbar["command"] = on_scrollbar
line_numbers["yscrollcommand"] = on_textscroll
text_widget["yscrollcommand"] = on_textscroll

root.mainloop()
