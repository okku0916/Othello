import socket
import sys
import threading
import json
import time
import tkinter as tk
from client_viewer import ClientViewer


class Client:
    def __init__(self, host="localhost", port=5000):
        self.client_socket = None
        self.host = host
        self.port = port
        self.viewer = None # クライアントビューアのインスタンス
        self.player_num = None  # プレイヤー番号を保持


    def request_room_list(self):
        self.client_socket.sendall((json.dumps({"type": "list_rooms"}) + "\n").encode())

    def join_room(self):
        selected = self.room_listbox.get(tk.ACTIVE)
        if selected:
            if selected.split(":")[1].strip().startswith("2"):
                print("部屋が満員です。")
                return
            room_id = selected.split(":")[0]
            self.root.destroy()  # Tkinterを閉じる
            self.client_socket.sendall((json.dumps({"type": "join_room", "room": room_id}) + "\n").encode())
            # メインスレッドではクライアントビューアを実行
            self.viewer = ClientViewer()
            self.viewer.run(self.client_socket)

            # 抜けたらロビーに戻る
            self.lobby()

    def create_room(self):
        self.root.destroy()  # Tkinterを閉じる
        self.client_socket.sendall((json.dumps({"type": "create_room"}) + "\n").encode())
        # メインスレッドではクライアントビューアを実行
        self.viewer = ClientViewer()
        self.viewer.run(self.client_socket)

        self.lobby()

    def lobby(self):
        self.root = tk.Tk()
        self.root.title("ロビー")
        # Tkinterで部屋番号入力のGUIを表示
        self.room_listbox = tk.Listbox(self.root)
        self.room_listbox.pack()
        tk.Button(self.root, text="更新", command=self.request_room_list).pack()
        tk.Button(self.root, text="参加", command=self.join_room).pack()
        tk.Button(self.root, text="部屋作成", command=self.create_room).pack()
        self.root.mainloop()


    def start_client(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            print(f"サーバー {self.host}:{self.port} に接続しました。")

            # サーバーからのメッセージを受信するスレッドを開始
            receive = threading.Thread(target=self.receive_messages, daemon=True)
            receive.start()

            # ロビー画面を表示
            self.lobby()

        except socket.error as e:
            print(f"接続エラー: {e}")
            sys.exit(1)

    def receive_messages(self):
        try:
            buffer = ""
            while True:
                buffer += self.client_socket.recv(1024).decode()
                # "\n"で区切られたメッセージを処理
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        message = json.loads(line)
                        # print("受信:", message)
                        self.handle_message(message)
        except Exception as e:
            print(f"受信エラー: {e}")
        finally:
            self.client_socket.close()
            print("サーバーとの接続が切断されました。")

    def handle_message(self, message):
        # プレイヤー番号と部屋番号の割り当て
        if message["type"] == "assign":
            # クライアントビューアが初期化されるのを待つ
            while self.viewer is None:
                time.sleep(0.1)
            self.player_num = message["player"]
            self.viewer.player_num = self.player_num
            room_id = message["room"]
            self.viewer.room_id = room_id
            print(f"部屋 {room_id} に参加しました。")
        # オセロの状態更新
        elif message["type"] == "state":
            # クライアントビューアが初期化されるのを待つ
            while self.viewer is None:
                time.sleep(0.1)
            self.viewer.board = message["board"]
            self.viewer.turn = message["turn"]
            self.viewer.prev_move = message["prev_move"]
            self.viewer.valid_moves = message["valid_moves"]
            self.viewer.gameover = message["gameover"]
        elif message["type"] == "room_list":
            self.room_listbox.delete(0, tk.END)
            for room in message["rooms"]:
                self.room_listbox.insert(tk.END, f"{room["id"]}: {room["players"]}/2")
        # エラーメッセージの表示
        elif message["type"] == "error":
            print("エラー:", message["message"])



if len(sys.argv) > 1:
    host = sys.argv[1]
else:
    host = "localhost"
if len(sys.argv) > 2:
    port = int(sys.argv[2])
else:
    port = 5000
client = Client(host, port)
client.start_client()