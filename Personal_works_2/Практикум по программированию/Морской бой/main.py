import tkinter as tk
from backend import Field
from bot import Bot


class FieldUI(tk.Canvas):
    def __init__(self, field, master, ship=False, click=False, visible=True):
        self.visible = visible
        self.field = field
        self.cell = 30
        self.space = 3
        self.get_current_moving_ship = ship
        self.click_heandler = click
        self.side = self.cell * 10 + self.space * 11

        super().__init__(master, width=self.side, height=self.side, background="grey")
        self.bind("<Motion>", self.moving)
        self.bind("<Button-1>", self.click)
        self.bind("<Button-3>", self.click)
        self.redraw()
        self.last_coords = []

    def redraw(self):
        self.delete("all")

        for y in range(10):
            for x in range(10):
                if self.visible:
                    color = [
                        "white",
                        "black",
                        "purple",
                        "red",
                    ][self.field.field[y, x]]
                else:
                    color = [
                        "white",
                        "black",
                        "white",
                        "purple",
                    ][self.field.field[y, x]]

                self.create_rectangle(
                    self.cell * x + self.space * (x + 1),
                    self.cell * y + self.space * (y + 1),
                    (self.cell + self.space) * (x + 1),
                    (self.cell + self.space) * (y + 1),
                    fill=color,
                    outline="",
                )

    def draw_ship(self, y, x, d=0, le=0):
        cords = []
        for i in range(le):
            cords.append([y, x])
            cords[-1][d] += i

        for y, x in cords:
            self.create_rectangle(
                self.cell * x + self.space * (x + 1),
                self.cell * y + self.space * (y + 1),
                (self.cell + self.space) * (x + 1),
                (self.cell + self.space) * (y + 1),
                fill="purple",
                outline="",
            )

    def click(self, event):
        x = min(event.x // (self.side // 10), 9)
        y = min(event.y // (self.side // 10), 9)
        self.click_heandler(y, x, event.num)
        self.redraw()

    def moving(self, event):
        if self.get_current_moving_ship:
            _dir, _len = self.get_current_moving_ship()
            x = min(event.x // (self.side // 10), 9)
            y = min(event.y // (self.side // 10), 9)
            if self.last_coords == [y, x]:
                return
            self.last_coords = [y, x]
            self.redraw()
            self.draw_ship(y, x, _dir, _len)


class ShipsUI(tk.Canvas):
    def __init__(self, master, field, click):
        self.click_heandler = click
        self.field = field
        self.cell = 30
        self.space = 3
        self.side = self.cell * 4 + self.space * 5

        super().__init__(master, width=self.side, height=self.side)
        self.bind("<Button-1>", self.onclick)
        self.redraw()

    def redraw(self):
        for le in range(4):
            for i in range(le + 1):
                self.create_rectangle(
                    self.cell * le + self.space * (le + 1),
                    self.cell * i + self.space * (i + 1),
                    (self.cell + self.space) * (le + 1),
                    (self.cell + self.space) * (i + 1),
                    fill="purple",
                    outline="",
                )

    def onclick(self, event):
        if self.click_heandler:
            le = int(min(event.x // (self.side / 4) + 1, 4))
            self.click_heandler(le)


class Game(tk.Tk):
    def __init__(self):
        super().__init__()
        self.fields = tk.Frame()
        self.fields.pack()

        self.control = tk.Frame()
        self.control.pack()

        self.bot_field = Field()
        self.bot_field.auto_fill()
        self.bot_field_ui = FieldUI(
            self.bot_field, self.fields, click=self.bot_click_heandler, visible=False
        )
        self.bot_field_ui.pack(side="right")

        self.player_field = Field()
        self.player_field_ui = FieldUI(
            self.player_field,
            self.fields,
            self.get_creating_ship,
            self.user_click_heandler,
        )
        self.player_field_ui.pack(side="left")

        self.create_ships_ui = ShipsUI(
            self.control, self.bot_field, self.set_creating_ship
        )
        self.create_ships_ui.pack(side="left")

        self.buttons = tk.Frame(self.control)
        self.buttons.pack(side="right")

        self.play_btn = tk.Button(
            self.buttons,
            width=10,
            height=2,
            text="Play",
            font="Arial 18",
            command=self.start,
        )
        self.play_btn.pack()
        self.auto_fill_btn = tk.Button(
            self.buttons,
            width=10,
            height=2,
            text="Autofill",
            font="Arial 18",
            command=self.player_autofill,
        )
        self.auto_fill_btn.pack()

        self.__game_state = 0

        self.current_ship = [0, 0]

        self.bind("<Control_L>", self.dir)

        self.move = 0

        self.bot = Bot()
        self.info = tk.Label(text="...", font="Arial 16")

    def start(self, *_):
        if (
            sum(self.bot_field.needs_ships.values()) == 0
            and sum(self.player_field.needs_ships.values()) == 0
        ):
            self.__game_state = 1
            self.bot_field.start_game()
            self.player_field.start_game()
            self.control.pack_forget()
            self.info.pack()

    def dir(self, _):
        self.current_ship[0] = 1 - self.current_ship[0]
        self.player_field_ui.redraw()
        self.player_field_ui.draw_ship(
            *self.player_field_ui.last_coords, *self.current_ship
        )

    def player_autofill(self):
        self.player_field.auto_fill()
        self.player_field_ui.redraw()

    def get_creating_ship(self):
        # horizontal, 3
        return self.current_ship

    def set_creating_ship(self, le, d=0):
        if self.player_field.needs_ships.get(le, 0) > 0:
            self.current_ship = [d, le]
        else:
            self.current_ship = [0, 0]

    def bot_click_heandler(self, y, x, *_):
        if self.__game_state == 1:
            self.game_loop(y, x)

    def user_click_heandler(self, y, x, btn):
        if self.__game_state == 0:
            if btn == 1:
                self.player_field.add_ship(y, x, *self.current_ship)
                if self.player_field.needs_ships.get(self.current_ship[1], 0) == 0:
                    self.current_ship = [0, 0]
            elif btn == 3:
                self.player_field.remove_ship(y, x)

    def game_loop(self, y=-1, x=-1):
        if self.move == 0:
            # ход игрока
            res = self.bot_field.shoot(y, x)
            self.bot_field_ui.redraw()
            self.info["text"] = ["Мимо", "Повтрор", "Ранел", "Сбил", "Вы выиграли"][res]
            if res == 4:
                self.__game_state = 2
            elif res == 0:
                self.move = 1 - self.move
                self.game_loop()
        else:
            y, x = self.bot.get_shoot()
            res = self.player_field.shoot(y, x)
            self.bot.result(res)
            self.player_field_ui.redraw()
            if res == 4:
                self.__game_state = 2
                self.info["text"] = "Вы проиграли"
            elif res == 0:
                self.move = 1 - self.move
            else:
                self.game_loop()


game = Game()
game.mainloop()
