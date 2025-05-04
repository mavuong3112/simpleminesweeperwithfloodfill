import os
import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Button
import random
import json
import requests
import pygame
import threading

SCORES_FILE = "DiemCao.txt"
CUSTOM_FILE = "Custom.txt"
DEFAULT_SCORES = {"easy": 999, "medium": 999, "hard": 999, "custom": 999}
DEFAULT_CUSTOM = {"rows": 10, "cols": 10, "mines": 10}

DIFFICULTY_PRESETS = {
    "Dễ": (8, 10, 10, "easy"),
    "Vừa": (14, 18, 35, "medium"),
    "Khó": (20, 24, 70, "hard"),
    "Tùy chỉnh": None
}

NUMBER_COLORS = {
    1: "blue",
    2: "green",
    3: "red",
    4: "darkblue",
    5: "maroon",
    6: "turquoise",
    7: "black",
    8: "gray"
}

def ensure_audio_files():
    urls = {
        "win.mp3": "https://github.com/thanhduc2000/audio-files/raw/main/win.mp3",
        "lose.mp3": "https://github.com/thanhduc2000/audio-files/raw/main/lose.mp3"
    }
    for filename, url in urls.items():
        if not os.path.exists(filename):
            try:
                r = requests.get(url)
                with open(filename, "wb") as f:
                    f.write(r.content)
            except:
                pass

def play_sound(filename, sound_on=True):
    def _inner():
        if sound_on:
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Lỗi phát âm thanh: {e}")
    threading.Thread(target=_inner, daemon=True).start()


class Cell:
    def __init__(self, x, y, button):
        self.x = x
        self.y = y
        self.button = button
        self.is_mine = False
        self.is_open = False
        self.is_flagged = False
        self.adjacent_mines = 0

class Minesweeper:
    def __init__(self, root, rows, cols, mines, mode):
        self.root = root
        self.rows = rows
        self.cols = cols
        self.total_mines = mines
        self.mode = mode
        self.flags_left = mines
        self.first_click = True
        self.time = 0
        self.timer_id = None
        self.sound_on = True
        self.board = []
        self.scores = self.load_json(SCORES_FILE, DEFAULT_SCORES)
        self.custom = self.load_json(CUSTOM_FILE, DEFAULT_CUSTOM)
        self.setup_ui()

    def load_json(self, filename, default_data):
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                json.dump(default_data, f)
            return default_data.copy()
        with open(filename, "r") as f:
            return json.load(f)

    def save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f)

    def setup_ui(self):
        self.top = tk.Frame(self.root, bg="#228B22")
        self.top.pack(fill="x")

        self.diff_var = tk.StringVar(value="Tùy chỉnh")
        tk.OptionMenu(self.top, self.diff_var, *DIFFICULTY_PRESETS.keys(), command=self.change_difficulty).pack(side="left", padx=4)
        self.sound_btn = tk.Button(self.top, text="🔈", command=self.toggle_sound)
        self.sound_btn.pack(side="left")
        tk.Button(self.top, text="☰", command=self.show_rules).pack(side="left", padx=5)
        self.smiley = tk.Label(self.top, text="🙂", bg="#228B22", font=("Arial", 16))
        self.smiley.pack(side="left", padx=10)

        self.flag_label = tk.Label(self.top, text=f"🚩 {self.flags_left}", bg="#228B22", fg="white", font=("Arial", 12))
        self.flag_label.pack(side="right", padx=6)
        self.timer_label = tk.Label(self.top, text="🕒 0", bg="#228B22", fg="white", font=("Arial", 12))
        self.timer_label.pack(side="right", padx=6)

        self.frame = tk.Frame(self.root)
        self.frame.pack()

        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                btn = tk.Button(self.frame, width=2, height=1, font=("Arial", 11),
                                command=lambda x=i, y=j: self.left_click(x, y))
                btn.bind("<Button-3>", lambda e, x=i, y=j: self.right_click(x, y))
                btn.bind("<Enter>", lambda e, b=btn: b.config(highlightbackground="blue", highlightthickness=1))
                btn.bind("<Leave>", lambda e, b=btn: b.config(highlightthickness=0))
                btn.grid(row=i, column=j)
                row.append(Cell(i, j, btn))
            self.board.append(row)

    def toggle_sound(self):
        self.sound_on = not self.sound_on
        self.sound_btn.config(text="🔈" if self.sound_on else "🔇")

    def update_ui(self):
        self.flag_label.config(text=f"🚩 {self.flags_left}")
        self.timer_label.config(text=f"🕒 {self.time}")

    def start_timer(self):
        self.time = 0
        self.update_timer()

    def update_timer(self):
        self.time += 1
        self.update_ui()
        self.timer_id = self.root.after(1000, self.update_timer)

    def place_mines(self, safe_x, safe_y):
        placed = 0
        while placed < self.total_mines:
            x, y = random.randint(0, self.rows-1), random.randint(0, self.cols-1)
            if (x, y) != (safe_x, safe_y) and not self.board[x][y].is_mine:
                self.board[x][y].is_mine = True
                placed += 1
        for i in range(self.rows):
            for j in range(self.cols):
                self.board[i][j].adjacent_mines = sum(
                    1 for a in range(max(0, i-1), min(self.rows, i+2))
                      for b in range(max(0, j-1), min(self.cols, j+2))
                      if self.board[a][b].is_mine)

    def left_click(self, x, y):
        if self.first_click:
            self.place_mines(x, y)
            self.first_click = False
            self.start_timer()
        self.reveal(x, y)
        self.check_win()

    def right_click(self, x, y):
        cell = self.board[x][y]
        if cell.is_open:
            return
        if cell.is_flagged:
            cell.button.config(text="")
            cell.is_flagged = False
            self.flags_left += 1
        else:
            if self.flags_left > 0:
                cell.button.config(text="🚩", fg="orange")
                cell.is_flagged = True
                self.flags_left -= 1
        self.update_ui()

    def reveal(self, x, y):
        cell = self.board[x][y]
        if cell.is_open or cell.is_flagged:
            return
        cell.is_open = True
        if cell.is_mine:
            cell.button.config(text="💣", bg="red")
            play_sound("lose.mp3", self.sound_on)
            self.end_game(False)
            return
        if cell.adjacent_mines > 0:
            color = NUMBER_COLORS.get(cell.adjacent_mines, "black")
            cell.button.config(text=str(cell.adjacent_mines), fg=color)
        else:
            cell.button.config(bg="lightgrey")
            for i in range(max(0, x-1), min(self.rows, x+2)):
                for j in range(max(0, y-1), min(self.cols, y+2)):
                    self.reveal(i, j)

    def check_win(self):
        for row in self.board:
            for cell in row:
                if not cell.is_mine and not cell.is_open:
                    return
        play_sound("win.mp3", self.sound_on)
        self.end_game(True)

    def end_game(self, won):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        for row in self.board:
            for cell in row:
                if cell.is_mine:
                    cell.button.config(text="💣")

        if won:
            play_sound("badge-coin-win-14675.mp3", self.sound_on)
            old = self.scores.get(self.mode, 999)
            if self.time < old:
                self.scores[self.mode] = self.time
                self.save_json(SCORES_FILE, self.scores)
                msg = f"🎉 Kỷ lục mới: {self.time} giây!"
            else:
                msg = f"🎉 Bạn thắng sau {self.time} giây!"
            emoji = "🏆"
            bg_color = "#d0f0c0"
        else:
            play_sound("losing-horn-313723.mp3", self.sound_on)
            msg = "💥 Bạn đã mở trúng mìn!"
            emoji = "💣"
            bg_color = "#ffd1d1"

        # Giao diện custom popup
        popup = Toplevel(self.root)
        popup.title("Kết thúc")
        popup.configure(bg=bg_color)

        tk.Label(popup, text=f"{emoji} {msg}", font=("Arial", 13, "bold"), bg=bg_color, fg="black").pack(pady=(15, 10),
                                                                                                         padx=20)
        tk.Label(popup, text="Bạn có muốn chơi lại không?", font=("Arial", 11), bg=bg_color).pack(pady=(0, 10))

        btn_frame = tk.Frame(popup, bg=bg_color)
        btn_frame.pack(pady=(0, 15))

        def play_again():
            popup.destroy()
            self.root.destroy()
            launch_game(self.rows, self.cols, self.total_mines, self.mode)

        def quit_game():
            popup.destroy()
            self.root.destroy()

        Button(btn_frame, text="🔁 CHƠI LẠI", width=12, bg="#90ee90", font=("Arial", 10, "bold"),
               command=play_again).pack(side="left", padx=10)
        Button(btn_frame, text="❌ THOÁT", width=12, bg="#ff7f7f", font=("Arial", 10, "bold"), command=quit_game).pack(
            side="right", padx=10)

    def change_difficulty(self, level):
        preset = DIFFICULTY_PRESETS[level]
        if preset:
            self.root.destroy()
            launch_game(*preset)
        else:
            rows = simpledialog.askinteger("Tùy chỉnh", "Số hàng:", minvalue=6, maxvalue=22)
            cols = simpledialog.askinteger("Tùy chỉnh", "Số cột:", minvalue=10, maxvalue=45)
            mines = simpledialog.askinteger("Tùy chỉnh", "Số mìn:", minvalue=5, maxvalue=rows*cols-1)
            custom = {"rows": rows, "cols": cols, "mines": mines}
            with open(CUSTOM_FILE, "w") as f:
                json.dump(custom, f)
            self.root.destroy()
            launch_game(rows, cols, mines, "custom")

    def show_rules(self):
        rule = Toplevel(self.root)
        rule.title("📘 Luật chơi & Mẹo")
        rule.configure(bg="#f0f8ff")  # nền xanh nhạt

        header = tk.Label(rule, text="📘 LUẬT CHƠI", font=("Arial", 14, "bold"), fg="#2a4d69", bg="#f0f8ff")
        header.pack(pady=(10, 5))

        rules_text = (
            "- Click trái chuột để mở ô.\n"
            "- Click phải để đặt cờ vào ô nghi ngờ có mìn.\n"
            "- Mở hết các ô KHÔNG có mìn để chiến thắng.\n"
            "- Nếu bạn mở trúng mìn thì sẽ thua ngay."
        )
        tk.Label(rule, text=rules_text, font=("Arial", 12), justify="left", bg="#f0f8ff").pack(padx=15, anchor="w")

        tips_header = tk.Label(rule, text="💡 MẸO CHƠI", font=("Arial", 14, "bold"), fg="#556b2f", bg="#f0f8ff")
        tips_header.pack(pady=(15, 5))

        tips_text = (
            "- Các ô trống liền kề sẽ tự động mở.\n"
            "- Nếu một ô số đã đủ số cờ xung quanh, bạn có thể mở nhanh các ô còn lại.\n"
            "- Đừng quên sử dụng logic loại trừ để đoán vị trí mìn."
        )
        tk.Label(rule, text=tips_text, font=("Arial", 12), justify="left", bg="#f0f8ff").pack(padx=15, anchor="w")

        tk.Button(rule, text="ĐÓNG", command=rule.destroy, bg="#e0e0e0", font=("Arial", 11)).pack(pady=15)


def launch_game(rows, cols, mines, mode):
    ensure_audio_files()
    root = tk.Tk()
    root.title("🧨 Dò Mìn")
    Minesweeper(root, rows, cols, mines, mode)
    root.mainloop()

def main():
    if not os.path.exists(CUSTOM_FILE):
        with open(CUSTOM_FILE, "w") as f:
            json.dump(DEFAULT_CUSTOM, f)
    with open(CUSTOM_FILE, "r") as f:
        preset = json.load(f)
    launch_game(preset["rows"], preset["cols"], preset["mines"], "custom")

if __name__ == "__main__":
    main()
