import sys
import socket
import threading
import json
import time
from othello_logic import OthelloLogic

class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        # self.game = OthelloLogic()
        self.players = [None, None]
        self.status = "waiting" # waiting, playing, paused
        self.hosts = [False, False]

    def handle_move(self, conn, player_num, message):
        x = message["x"]
        y = message["y"]
        if player_num != self.game.turn:
            # print(f"プレイヤー{player_num}のターンではありません。")
            return
        if self.status != "playing": # ゲームが開始されていない場合
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
            conn.sendall((json.dumps(game_data) + "\n").encode())

    def start_game(self):
        self.game = OthelloLogic()
        self.game.turn = 1
        self.status = "playing"
        for i, conn in enumerate(self.players):
            conn.sendall((json.dumps({"type": "start", "game": "othello"}) + "\n").encode())
        self.broadcast()

    def rematch(self):
        self.game = OthelloLogic()
        self.game.turn = 1
        self.status = "playing"
        for i, conn in enumerate(self.players):
            conn.sendall((json.dumps({"type": "rematch"}) + "\n").encode())
        self.broadcast()

class Server:
    def __init__(self, host="0.0.0.0", port=5000):
        self.rooms = {}
        self.conn_to_room = {} # 接続から部屋番号を引くための辞書
        self.host = host
        self.port = port
        self.sock = None
        self.clients = [] # 接続されたクライアントのリスト

    def start_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            self.sock.listen(16)
            print(f"オセロサーバーが開始されました。{self.host}:{self.port}")

            # プレイヤー接続待ち
            while True:
                conn, addr = self.sock.accept()
                self.clients.append(conn)
                print(f"クライアント{len(self.clients)} ({addr[0]}:{addr[1]})が接続しました。")
                # 各プレイヤーの接続を別スレッドで処理
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, len(self.clients)),
                    daemon=True).start()

        except socket.error as e:
            print(f"サーバーエラー: {e}")

    def handle_client(self, conn, client_id):
        player_num = 0
        message = {}
        try:
            buffer = ""
            while True:
                buffer += conn.recv(1024).decode()
                # "\n"で区切られたメッセージを処理
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        message = json.loads(line)
                        # print(f"クライアント{client_id}から受信:", message)

                if message["type"] == "create_room":
                    # 二重作成防止処理
                    if conn in self.conn_to_room:
                        continue
                    room_id = len(self.rooms) + 1
                    self.rooms[room_id] = Room(room_id) # 新しい部屋を作成
                    print(f"部屋{room_id}を作成しました。")
                    player_num = 1  # 作成者は常に1(黒)
                    self.rooms[room_id].hosts[player_num-1] = True # 作成者をホストに設定
                    self.rooms[room_id].players[player_num-1] = conn # 作成者を部屋に追加
                    self.conn_to_room[conn] = room_id # 接続と部屋を紐付け
                    print(f"クライアント{client_id}が部屋{room_id}に参加しました。")
                    conn.send((json.dumps({
                        "type": "assign",
                        "player": 1,
                        "room": room_id,
                        "host": True,
                        "status": self.rooms[room_id].status
                    }) + "\n").encode())

                elif message["type"] == "join_room":
                    room_id = int(message["room"])
                    # 部屋が存在するか確認
                    if room_id not in self.rooms:
                        conn.send((json.dumps({
                            "type": "error",
                            "message": "指定された部屋は存在しません。"
                        }) + "\n").encode())
                        continue
                    # 部屋が満員か確認
                    if all(p is not None for p in self.rooms[room_id].players):
                        conn.send((json.dumps({
                            "type": "error",
                            "message": "指定された部屋は満員です。"
                        }) + "\n").encode())
                        continue
                    # 二重参加防止処理
                    if conn in self.rooms[room_id].players:
                        continue
                    # いない方のプレイヤー番号を割り当てる
                    for p in self.rooms[room_id].players:
                        if p is None:
                            player_num = self.rooms[room_id].players.index(p) + 1
                            break
                    self.rooms[room_id].players[player_num-1] = conn # 参加者を部屋に追加
                    self.conn_to_room[conn] = room_id # 接続と部屋を紐付け
                    print(f"クライアント{client_id}が部屋{room_id}に参加しました。")
                    conn.send((json.dumps({
                        "type": "assign",
                        "player": player_num,
                        "room": room_id,
                        "host": self.rooms[room_id].hosts[player_num-1],
                        "status": self.rooms[room_id].status
                    }) + "\n").encode())
                    # 中断中の場合はゲーム再開
                    if self.rooms[room_id].status == "paused":
                        print(f"部屋{room_id}でゲームが再開されました。")
                        self.rooms[room_id].status = "playing"

                elif message["type"] == "start_game":
                    room_id = self.conn_to_room.get(conn)
                    if room_id is None:
                        continue
                    if not self.rooms[room_id].hosts[player_num-1]:
                        # ホストでない場合は無視
                        continue
                    if self.rooms[room_id].status == "playing":
                        # すでにゲームが開始されている場合は無視
                        continue
                    if all(p is not None for p in self.rooms[room_id].players):
                        print(f"部屋{room_id}でゲームが開始されました。")
                        self.rooms[room_id].start_game()
                    else:
                        conn.send((json.dumps({
                            "type": "error",
                            "message": "プレイヤーが揃っていません。"
                        }) + "\n").encode())

                elif message["type"] == "list_rooms":
                    room_list = [{"id": rid, "players": len([p for p in room.players if p is not None])} for rid, room in self.rooms.items()]
                    conn.send((json.dumps({
                        "type": "room_list",
                        "rooms": room_list
                    }) + "\n").encode())

                elif message["type"] == "move":
                    room_id = self.conn_to_room.get(conn)
                    self.rooms[room_id].handle_move(conn, player_num, message)

                elif message["type"] == "quit":
                    room_id = self.conn_to_room.get(conn)
                    print(f"クライアント{client_id}が部屋{room_id}から退出しました。")
                    if self.rooms[room_id].status == "playing":
                        self.rooms[room_id].status = "paused"
                    self.rooms[room_id].players[player_num-1] = None
                    # ホスト権限の移譲
                    self.rooms[room_id].hosts[player_num-1] = False
                    num = player_num - 1
                    for i in range(len(self.rooms[room_id].players)):
                        num = (num + 1) % len(self.rooms[room_id].players)
                        if self.rooms[room_id].players[num] is not None:
                            self.rooms[room_id].hosts[num] = True
                            self.rooms[room_id].players[num].sendall((json.dumps({
                                "type": "assign",
                                "player": num + 1,
                                "room": room_id,
                                "host": True,
                                "status": self.rooms[room_id].status
                            }) + "\n").encode())
                            break

                    # プレイヤーが0人になったら部屋を削除
                    if all(p is None for p in self.rooms[room_id].players):
                        print(f"部屋{room_id}を削除しました。")
                        del self.rooms[room_id]
                    del self.conn_to_room[conn]

                elif message["type"] == "rematch":
                    room_id = self.conn_to_room.get(conn)
                    room = self.rooms[room_id]
                    if all(p is not None for p in room.players):
                        print(f"部屋{room_id}で再試合が開始されました。")
                        room.rematch()

        except BrokenPipeError:
            print(f"クライアント{client_id}が切断されました。")
        except ConnectionResetError:
            print(f"クライアント{client_id}が切断されました。")
        except Exception as e:
            print(f"クライアント{client_id}エラー: {e}")
        finally:
            conn.close()


if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    port = 5000 # デフォルトのポート番号

server = Server(port=port)
server.start_server()