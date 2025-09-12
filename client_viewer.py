import tkinter as tk
import json

class ClientViewer:
    def __init__(self):
        self.board_size = 600
        self.grid = 8
        self.grid_size = self.board_size // self.grid
        self.start_posy = 100
        self.board = [[0 for i in range(self.grid)] for j in range(self.grid)]
        self.prev_move = None  # 前の手を記録する
        self.valid_moves = []  # 置ける場所のリスト
        self.gameover = False
        self.player_num = None  # プレイヤー番号を保持
        self.turn = 1  # 1が黒、2が白
        self.room_id = None  # 部屋番号を保持
        self.sock = None

        self.root = tk.Tk()
        self.root.geometry(f"{self.board_size}x{self.board_size + 200}")
        self.root.title("オセロ")
        # ウィジェットの配置
        tk.Label(self.root, text="Simple Othello", font=("Arial", 32)).pack()
        self.room_id_text = tk.Label(self.root, text=f"Room ID: {self.room_id}", font=("Arial", 24))
        self.room_id_text.pack()
        self.canvas = tk.Canvas(self.root, width=self.board_size, height=self.board_size, bg="green")
        # グリッド線を描画
        for i in range(self.grid+1):
            self.canvas.create_line(0, i * self.grid_size, self.board_size, i * self.grid_size, fill="black")
            self.canvas.create_line(i * self.grid_size, 0, i * self.grid_size, self.board_size, fill="black")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.move)
        self.score_label = tk.Label(self.root, text=f"Black: 2  White: 2", font=("Arial", 24))
        self.score_label.pack()

    def end(self):
        black, white = self.count()
        if black > white:
            result_text = tk.Label(self.root, text=f"BLACK WIN! {black} vs {white}", font=("Arial", 32), fg="black", bg="white")
            result_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        elif black < white:
            result_text = tk.Label(self.root, text=f"WHITE WIN! {black} vs {white}", font=("Arial", 32), fg="white", bg="black")
            result_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            result_text = tk.Label(self.root, text=f"DRAW! {black} vs {white}", font=("Arial", 32), fg="black", bg="white")
            result_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def draw(self):
        self.canvas.delete("marker") # 前の手のマーカーを消す
        black, white = self.count()
        self.score_label.config(text=f"Black: {black}  White: {white}")
        # 石を描画
        for x in range(self.grid):
            for y in range(self.grid):
                if self.board[y][x] == 1:
                    self.canvas.create_oval(x * self.grid_size + self.grid_size // 10, y * self.grid_size + self.grid_size // 10, (x + 1) * self.grid_size - self.grid_size // 10, (y + 1) * self.grid_size - self.grid_size // 10, fill="black")
                if self.board[y][x] == 2:
                    self.canvas.create_oval(x * self.grid_size + self.grid_size // 10, y * self.grid_size + self.grid_size // 10, (x + 1) * self.grid_size - self.grid_size // 10, (y + 1) * self.grid_size - self.grid_size // 10, fill="white")
        # 石を置ける場所を表示
        for x, y in self.valid_moves:
            if self.turn == self.player_num == 1:
                self.canvas.create_oval(x * self.grid_size + self.grid_size // 3, y * self.grid_size + self.grid_size // 3, (x + 1) * self.grid_size - self.grid_size // 3, (y + 1) * self.grid_size - self.grid_size // 3, fill="black", tags="marker")
            elif self.turn == self.player_num == 2:
                self.canvas.create_oval(x * self.grid_size + self.grid_size // 3, y * self.grid_size + self.grid_size // 3, (x + 1) * self.grid_size - self.grid_size // 3, (y + 1) * self.grid_size - self.grid_size // 3, fill="white", tags="marker")
        # 前の手を表示
        if self.prev_move:
            x, y = self.prev_move
            self.canvas.create_oval(x * self.grid_size + self.grid_size // 10, y * self.grid_size + self.grid_size // 10, (x + 1) * self.grid_size - self.grid_size // 10, (y + 1) * self.grid_size - self.grid_size // 10, outline="red", width=3, tags="marker")
        # ゲーム終了時の表示
        if self.gameover:
            self.end()

    def move(self, event):
        x = event.x // (self.board_size // self.grid)
        y = event.y // (self.board_size // self.grid)
        if 0 <= x < self.grid and 0 <= y < self.grid:
            self.sock.sendall((json.dumps({"type" : "move", "x" : x, "y" : y}) + "\n").encode())

    def count(self):
        black = 0
        white = 0
        for x in range(self.grid):
            for y in range(self.grid):
                if self.board[y][x] == 1:
                    black += 1
                if self.board[y][x] == 2:
                    white += 1
        return (black, white)

    def run(self, sock=None):
        self.sock = sock
        self.draw()
        self.root.protocol("WM_DELETE_WINDOW", self.quit) # ウィンドウの閉じるボタンでquitを呼び出す
        self.root.mainloop()

    def quit(self):
        self.sock.sendall((json.dumps({"type": "quit"}) + "\n").encode())
        self.root.destroy()