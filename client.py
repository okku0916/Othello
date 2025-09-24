import socket
import sys
import threading
import json
from client_viewer import ClientViewer


class Client:
    def __init__(self, host="localhost", port=5000):
        self.client_socket = None
        self.host = host
        self.port = port
        self.viewer = None # クライアントビューアのインスタンス
        self.player_num = None  # プレイヤー番号を保持


    def start_client(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            print(f"サーバー {self.host}:{self.port} に接続しました。")

            # サーバーからのメッセージを受信するスレッドを開始
            receive = threading.Thread(target=self.receive_messages, daemon=True)
            receive.start()

            # ロビー画面を表示
            self.viewer = ClientViewer(self.send_message, self.close) # コールバック関数を渡す(ログを見るときはself.send_messageをprint関数に変えるなどの使い方ができる)
            self.viewer.create_lobby_screen()
            self.viewer.root.mainloop()


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
            self.player_num = message["player"]
            self.viewer.player_num = self.player_num
            self.viewer.is_host = message["host"]
            room_id = message["room"]
            self.viewer.room_id = room_id
            print(f"部屋 {room_id} に参加しました。")
            if message["status"] == "paused": # 中断中の場合
                self.viewer.root.after(0, self.viewer.run) # メインスレッドでゲーム開始
            else:
                self.viewer.root.after(0, self.viewer.create_room_screen) # メインスレッドで部屋画面へ

        if message["type"] == "start":
            if message["game"] == "othello":
                self.viewer.root.after(0, self.viewer.run) # メインスレッドでゲーム開始

        # オセロの状態更新
        elif message["type"] == "state":
            self.viewer.board = message["board"]
            self.viewer.turn = message["turn"]
            self.viewer.prev_move = message["prev_move"]
            self.viewer.valid_moves = message["valid_moves"]
            self.viewer.gameover = message["gameover"]
            self.viewer.root.after(0, self.viewer.draw) # メインスレッドで描画

        # 部屋リストの更新
        elif message["type"] == "room_list":
            self.viewer.update_room_list(message["rooms"])

        elif message["type"] == "rematch":
            self.viewer.reset_game()

        # エラーメッセージの表示
        elif message["type"] == "error":
            print("エラー:", message["message"])

    def send_message(self, data):
        self.client_socket.sendall((json.dumps(data) + "\n").encode())

    def close(self):
        if self.client_socket:
            self.client_socket.close()


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