import tkinter as tk
import json

class ClientViewer:
    def __init__(self, on_action, socket_close):
        # ゲームの状態
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
        self.on_action = on_action # ユーザーアクションのコールバック関数(sendだけとは限らないからこの名前)
        self.socket_close = socket_close # ソケットを閉じる関数
        self.is_host = False # ホストかどうか

        # GUI要素
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)  # ウィンドウの閉じるボタンでquitを呼び出す
        self.room_id_text = None
        self.canvas = None
        self.score_label = None
        self.result_label = None
        self.rematch_button = None

    # ゲーム終了時の処理
    def end(self):
        black, white = self.count()
        if black > white:
            self.result_text = tk.Label(self.root, text=f"BLACK WIN! {black} vs {white}", font=("Arial", 40), fg="black", bg="white")
            self.result_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        elif black < white:
            self.result_text = tk.Label(self.root, text=f"WHITE WIN! {black} vs {white}", font=("Arial", 40), fg="white", bg="black")
            self.result_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self.result_text = tk.Label(self.root, text=f"DRAW! {black} vs {white}", font=("Arial", 40), fg="black", bg="white")
            self.result_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        if self.is_host:
            self.rematch_button = tk.Button(self.root, text="Rematch", font=("Arial", 32), fg="red", command=self.rematch)
            self.rematch_button.place(relx=0, rely=0, anchor=tk.NW)

    # 毎回の画面の描画処理
    def draw(self):
        self.canvas.delete("marker") # 前の手のマーカーを消す
        black, white = self.count()
        self.score_label.config(text=f"Black: {black}  White: {white}")
        # 石を描画
        for x in range(self.grid):
            for y in range(self.grid):
                if self.board[y][x] == 1:
                    self.canvas.create_oval(x * self.grid_size + self.grid_size // 10, y * self.grid_size + self.grid_size // 10, (x + 1) * self.grid_size - self.grid_size // 10, (y + 1) * self.grid_size - self.grid_size // 10, fill="black", tags="stone")
                if self.board[y][x] == 2:
                    self.canvas.create_oval(x * self.grid_size + self.grid_size // 10, y * self.grid_size + self.grid_size // 10, (x + 1) * self.grid_size - self.grid_size // 10, (y + 1) * self.grid_size - self.grid_size // 10, fill="white", tags="stone")
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

    # 石を置いた時の処理
    def move(self, event):
        x = event.x // (self.board_size // self.grid)
        y = event.y // (self.board_size // self.grid)
        if 0 <= x < self.grid and 0 <= y < self.grid:
            self.on_action({"type" : "move", "x" : x, "y" : y})

    # 石の数を数える
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

    # ゲーム初回実行時の処理
    def run(self):
        self.create_game_screen()
        self.draw()

    # 終了時の処理
    def quit(self):
        if self.root.title() == "Othello":
            self.on_action({"type": "quit"})
            self.create_lobby_screen()
        elif self.root.title() == "Room":
            self.on_action({"type": "quit"})
            self.create_lobby_screen()
        else:
            self.socket_close()
            self.root.destroy()

    # 再試合のリクエスト
    def rematch(self):
        self.on_action({"type": "rematch"})

    # 部屋更新のリクエスト
    def request_room_list(self):
        self.on_action({"type": "list_rooms"})

    # リマッチ時の画面リセット
    def reset_game(self):
        self.canvas.delete("stone")
        self.result_text.destroy()
        self.rematch_button.destroy() if self.rematch_button else None

    # ロビー画面の作成
    def create_lobby_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.title("Lobby")
        self.root.geometry("400x400")
        self.room_listbox = tk.Listbox(self.root)
        self.room_listbox.pack()
        tk.Button(self.root, text="更新", command=self.request_room_list).pack()
        tk.Button(self.root, text="参加", command=self.join_room, width=7).pack()
        tk.Button(self.root, text="部屋作成", command=self.create_room, width=7).pack()
        self.request_room_list()

    # 部屋画面の作成
    def create_room_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.title("Room")
        self.root.geometry("400x400")
        tk.Label(self.root, text=f"Room ID: {self.room_id}", font=("Arial", 16)).pack()
        if self.is_host:
            tk.Label(self.root, text="ゲーム選択", font=("Arial", 16)).pack()
            self.game_listbox = tk.Listbox(self.root)
            self.game_listbox.pack()
            self.game_listbox.insert(tk.END, "オセロ")
            tk.Button(self.root, text="開始", command=lambda: self.on_action({"type": "start_game", "game": "othello"}), width=7).pack()
        else:
            tk.Label(self.root, text="ホストがゲームを選択するのを待っています...", font=("Arial", 16)).pack()
        tk.Button(self.root, text="Quit", command=self.quit, width=7).pack()

    # ゲーム画面の作成
    def create_game_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.geometry(f"{self.board_size}x{self.board_size + 200}")
        self.root.title("Othello")
        # ウィジェットの配置
        tk.Label(self.root, text="Simple Othello", font=("Arial", 32)).pack()
        self.room_id_text = tk.Label(self.root, text=f"Room ID: {self.room_id}", font=("Arial", 24))
        self.room_id_text.pack()
        self.score_label = tk.Label(self.root, text=f"Black: 2  White: 2", font=("Arial", 24))
        self.score_label.pack()
        self.result_label = None
        self.rematch_button = None
        self.canvas = tk.Canvas(self.root, width=self.board_size, height=self.board_size, bg="green")
        # グリッド線を描画
        for i in range(self.grid+1):
            self.canvas.create_line(0, i * self.grid_size, self.board_size, i * self.grid_size, fill="black")
            self.canvas.create_line(i * self.grid_size, 0, i * self.grid_size, self.board_size, fill="black")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.move)
        tk.Button(self.root, text="Quit", font=("Arial", 32), command=self.quit).place(relx=1.0, rely=0.0, anchor=tk.NE)

    # 部屋リストの更新
    def update_room_list(self, rooms):
        self.room_listbox.delete(0, tk.END)
        for room in rooms:
            self.room_listbox.insert(tk.END, f"{room['id']}: {room['players']}/2")

    # 部屋に参加する
    def join_room(self):
        selected = self.room_listbox.get(tk.ACTIVE)
        if selected:
            if selected.split(":")[1].strip().startswith("2"):
                print("部屋が満員です。")
                return
            room_id = selected.split(":")[0]
            self.on_action({"type": "join_room", "room": room_id})

    # 部屋を作成する
    def create_room(self):
        self.on_action({"type": "create_room"})