import socket
import sys
import threading
import json
import time
from client_viewer import ClientViewer


class Client:
    def __init__(self, host='localhost', port=5000):
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

            # メインスレッドではクライアントビューアを実行
            self.viewer = ClientViewer()
            self.viewer.run(self.client_socket)

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
                        print("受信:", message)
                        self.handle_message(message)
        except Exception as e:
            print(f"受信エラー: {e}")
        finally:
            self.client_socket.close()
            print("サーバーとの接続が切断されました。")

    def handle_message(self, message):
        if message['type'] == 'assign':
            self.player_num = message['player']
            # クライアントビューアが初期化されるのを待つ
            while self.viewer is None:
                time.sleep(0.1)
            self.viewer.player_num = self.player_num
        elif message["type"] == "state":
            self.viewer.board = message["board"]
            self.viewer.turn = message["turn"]
            self.viewer.prev_move = message["prev_move"]
            self.viewer.valid_moves = message["valid_moves"]
            self.viewer.gameover = message["gameover"]



if len(sys.argv) > 1:
    host = sys.argv[1]
else:
    host = 'localhost'
if len(sys.argv) > 2:
    port = int(sys.argv[2])
else:
    port = 5000
client = Client(host, port)
client.start_client()