import sys
import socket
import threading
import json
import time
from othello_logic import OthelloLogic

class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.game = OthelloLogic()
        self.players = []
        self.running = False

    def handle_move(self, conn, player_num, message):
        x = message["x"]
        y = message["y"]
        if player_num != self.game.turn:
            # print(f"プレイヤー{player_num}のターンではありません。")
            return
        if not self.running: # ゲームが開始されていない場合
            return
        if self.game.can_place(x, y):
            self.game.place(x, y)
            # print(f"プレイヤー{player_num}が手を打ちました: ({x}, {y})")
            self.game.turn = (2 if self.game.turn == 1 else 1)
            if self.game.is_board_full():
                self.game.end_game()
            elif self.game.check_pass():
                # print(f"プレイヤー{player_num}がパスしました。")
                self.game.turn = (2 if self.game.turn == 1 else 1)
                if self.game.check_pass():
                    # print("両プレイヤーがパスしたため、ゲームを終了します。")
                    self.game.end_game()
            self.broadcast()
        # else:
        #     print(f"プレイヤー{player_num}の手は無効です: ({x}, {y})")

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
        for i, conn in enumerate(self.players):
            try:
                conn.sendall((json.dumps(game_data) + "\n").encode())
            except socket.error as e:
                print(f"送信エラー: {e}")

class Server:
    def __init__(self, host="0.0.0.0", port=5000):
        self.rooms = {}
        self.conn_to_room = {} # 接続から部屋番号を引くための辞書
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

            # プレイヤー接続待ち
            while True:
                conn, addr = self.sock.accept()
                # 接続の処理
                self.clients.append(conn)
                print(f"プレイヤー{len(self.clients)} ({addr[0]}:{addr[1]})が接続しました。")
                # 各プレイヤーの接続を別スレッドで処理
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, len(self.clients)),
                    daemon=True
                )
                client_thread.start()

        except socket.error as e:
            print(f"サーバーエラー: {e}")

    def handle_client(self, conn, client_id):
        player_num = 0
        message = {}
        try:
            buffer = ""
            while True:
                # ゲームが終了している場合、ループを抜ける(試合が終わったらそれで終わり)
                # if self.conn_to_room[conn] is not None:
                #     room_id = self.conn_to_room[conn]
                #     if not self.rooms[room_id].game or self.rooms[room_id].game.gameover:
                #         break
                buffer += conn.recv(1024).decode()
                # "\n"で区切られたメッセージを処理
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        message = json.loads(line)
                        print(f"プレイヤー{client_id}から受信:", message)

                if message["type"] == "create_room":
                    # 二重作成防止処理
                    if conn in self.conn_to_room:
                        continue
                    room_id = len(self.rooms) + 1
                    self.rooms[room_id] = Room(room_id)
                    print(f"部屋{room_id}を作成しました。")
                    self.rooms[room_id].players.append(conn)
                    self.conn_to_room[conn] = room_id
                    print(f"プレイヤー{client_id}が部屋{room_id}に参加しました。")
                    player_num = len(self.rooms[room_id].players)
                    conn.send((json.dumps({
                        "type": "assign",
                        "player": player_num,
                        "room": room_id
                    }) + "\n").encode())

                elif message["type"] == "join_room":
                    room_id = int(message["room"])
                    # 二重参加防止処理
                    if conn in self.rooms[room_id].players:
                        continue
                    self.rooms[room_id].players.append(conn)
                    self.conn_to_room[conn] = room_id
                    # 部屋が存在しない場合の例外処理
                    # if room_id not in self.rooms:
                    #     conn.send((json.dumps({
                    #         "type": "error",
                    #         "message": "部屋が存在しません。"
                    #     }) + "\n").encode())
                    print(f"プレイヤー{client_id}が部屋{room_id}に参加しました。")
                    # プレイヤー番号を割り当て
                    player_num = len(self.rooms[room_id].players)
                    # 最初に接続したプレイヤーが1(黒)、次が2(白)
                    conn.send((json.dumps({
                        "type": "assign",
                        "player": player_num,
                        "room": room_id
                    }) + "\n").encode())
                    if len(self.rooms[room_id].players) == 2:
                        print(f"部屋{room_id}の両方のプレイヤーが接続しました。ゲームを開始します。")
                        self.rooms[room_id].running = True
                        # 初期状態を送信
                        self.rooms[room_id].broadcast()

                elif message["type"] == "list_rooms":
                    room_list = [{"id": rid, "players": len(room.players)} for rid, room in self.rooms.items()]
                    conn.send((json.dumps({
                        "type": "room_list",
                        "rooms": room_list
                    }) + "\n").encode())

                elif message["type"] == "move":
                    room_id = self.conn_to_room.get(conn)
                    self.rooms[room_id].handle_move(conn, player_num, message)

        except Exception as e:
            print(f"プレイヤー{client_id}エラー: {e}")
        finally:
            conn.close()
            print(f"プレイヤー{client_id}が切断しました")


if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    port = 5000 # デフォルトのポート番号

server = Server(port=port)
server.start_server()