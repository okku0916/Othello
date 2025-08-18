class OthelloLogic():
    def __init__(self):
        self.board_size = 600
        self.grid = 8
        self.grid_size = self.board_size // self.grid
        self.board = [[0 for i in range(self.grid)] for j in range(self.grid)]
        for x in range(2):
            for y in range(2):
                self.board[y + self.grid // 2 - 1][x + self.grid // 2 - 1] = (x + y) % 2 + 1

        self.prev_move = None  # 前の手を記録する
        self.gameover = False
        self.turn = 1  # 1が黒、2が白

    def is_board_full(self):
        for x in range(self.grid):
            for y in range(self.grid):
                if self.board[y][x] == 0:
                    return False
        return True

    def check_pass(self):
        for x in range(self.grid):
            for y in range(self.grid):
                if self.can_place(x, y):
                    return False
        return True

    def can_place(self, x, y):
        if self.board[y][x] != 0:
            return False
        for dx in range(-1, 2):  # 周囲のマスを調べる
            for dy in range(-1, 2):
                nx = x + dx
                ny = y + dy
                if 0 <= nx <= self.grid - 1 and 0 <= ny <= self.grid - 1:
                    while self.board[ny][nx] == (2 if self.turn == 1 else 1):  # 相手の石が続いている間
                        nx += dx
                        ny += dy
                        if nx < 0 or nx >= self.grid or ny < 0 or ny >= self.grid:  # 盤面外に出たらbreak
                            break
                        if self.board[ny][nx] == self.turn:  # 自分の石があったら置ける
                            return True

    def place(self, x, y):
        self.board[y][x] = self.turn
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nx = x + dx
                ny = y + dy
                if 0 <= nx <= self.grid - 1 and 0 <= ny <= self.grid - 1:
                    flip_list = []
                    while self.board[ny][nx] == (2 if self.turn == 1 else 1):
                        flip_list.append((nx, ny))
                        nx += dx
                        ny += dy
                        if nx < 0 or nx >= self.grid or ny < 0 or ny >= self.grid:
                            break
                        if self.board[ny][nx] == self.turn:
                            for flip in flip_list:
                                self.board[flip[1]][flip[0]] = self.turn
                            break
        self.prev_move = (x, y)

    def end_game(self):
        self.gameover = True