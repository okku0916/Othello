import sys
import socket
import threading
import json
import time
from othello_logic import OthelloLogic

class Server:
    def __init__(self, host='0.0.0.0', port=5000):
        self.game = None
        self.host = host
        self.port = port
        self.sock = None
        self.clients = []

    def start_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            self.sock.listen(2)  # 最大2クライアントを待ち受け
            print(f"オセロサーバーが開始されました。{self.host}:{self.port}")
            print("2人のプレイヤーが接続するのを待っています...")
            # ゲームロジックのインスタンスを作成
            self.game = OthelloLogic()

            while len(self.clients) < 2:
                conn, addr = self.sock.accept()
                self.clients.append(conn)
                print(f"プレイヤー{len(self.clients)} ({addr[0]}:{addr[1]})が接続しました。")
                # プレイヤー番号を割り当て
                conn.send((json.dumps({
                    'type': 'assign',
                    'player': len(self.clients)
                }) + '\n').encode())
                # 各プレイヤーの接続を別スレッドで処理
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, len(self.clients)),
                    daemon=True
                )
                client_thread.start()
            print("両方のプレイヤーが接続しました。ゲームを開始します。")
            # ゲーム開始のメッセージを各クライアントに送信
            self.broadcast()

            # メインスレッドが終了しないように待機
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("サーバーを終了します")

        except socket.error as e:
            print(f"サーバーエラー: {e}")

    def handle_client(self, conn, player_num):
        try:
            buffer = ""
            while True:
                buffer += conn.recv(1024).decode()
                # "\n"で区切られたメッセージを処理
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        message = json.loads(line)
                        print(f"プレイヤー{player_num}から受信:", message)

                if message["type"] == 'move':
                    self.handle_move(conn, player_num, message)

        except Exception as e:
            print(f"クライアント{player_num}エラー: {e}")
        finally:
            conn.close()
            print(f"プレイヤー{player_num}が切断しました")

    def handle_move(self, conn, player_num, message):
        x = message["x"]
        y = message["y"]
        if player_num != self.game.turn:
            print(f"プレイヤー{player_num}のターンではありません。")
            return
        if self.game.can_place(x, y):
            self.game.place(x, y)
            print(f"プレイヤー{player_num}が手を打ちました: ({x}, {y})")
            self.game.turn = (2 if self.game.turn == 1 else 1)
            if self.game.check_pass():
                print(f"プレイヤー{player_num}がパスしました。")
                self.game.turn = (2 if self.game.turn == 1 else 1)
                if self.game.check_pass():
                    print("両プレイヤーがパスしたため、ゲームを終了します。")
                    self.game.end_game()
            if self.game.is_board_full():
                self.game.end_game()
            self.broadcast()
        else:
            print(f"プレイヤー{player_num}の手は無効です: ({x}, {y})")

    def broadcast(self):
        game_data = {
            "type": "state",
            "board": self.game.board,
            "turn": self.game.turn,
            "prev_move": self.game.prev_move,
            "valid_moves": [
                (x, y) for x in range(self.game.grid) for y in range(self.game.grid) if self.game.can_place(x, y)
            ],
            "gameover": self.game.gameover
        }
        for i, conn in enumerate(self.clients):
            try:
                conn.sendall((json.dumps(game_data) + "\n").encode())
            except socket.error as e:
                print(f"送信エラー: {e}")



if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    port = 5000 # デフォルトのポート番号

server = Server(port=port)
server.start_server()