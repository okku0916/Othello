import pygame
import json

class ClientViewer:
    def __init__(self):
        self.board_size = 600
        self.grid = 8
        self.grid_size = self.board_size // self.grid
        self.board = [[0 for i in range(self.grid)] for j in range(self.grid)]
        self.prev_move = None  # 前の手を記録する
        self.valid_moves = []  # 置ける場所のリスト
        self.gameover = False
        self.player_num = None  # プレイヤー番号を保持
        self.turn = 1  # 1が黒、2が白
        self.room_id = None  # 部屋番号を保持

        pygame.init()
        self.win = pygame.display.set_mode((600, 700))
        pygame.display.set_caption("オセロ")

    def end(self, win):
        black, white = self.count()
        if black > white:
            font = pygame.font.Font(None, 100)
            text = font.render("BLACK WIN!", True, (0, 0, 0), (255, 255, 255))
            text_rect = text.get_rect(center=(self.board_size // 2, self.board_size // 2))
            win.blit(text, text_rect)
        elif black < white:
            font = pygame.font.Font(None, 100)
            text = font.render("WHITE WIN!", True, (255, 255, 255), (0, 0, 0))
            text_rect = text.get_rect(center=(self.board_size // 2, self.board_size // 2))
            win.blit(text, text_rect)
        else:
            font = pygame.font.Font(None, 100)
            text = font.render("DRAW!", True, (0, 0, 0), (255, 255, 255))
            text_rect = text.get_rect(center=(self.board_size // 2, self.board_size // 2))
            win.blit(text, text_rect)

    def draw(self, win):
        win.fill((255, 255, 255)) # 背景リセット
        # 緑色背景を描画
        pygame.draw.rect(win, (0, 128, 0), (0, 0, self.board_size, self.board_size))
        # グリッド線を描画
        for i in range(self.grid+1):
            pygame.draw.line(win, (0, 0, 0), (0, i * self.grid_size), (self.board_size, i * self.grid_size))
            pygame.draw.line(win, (0, 0, 0), (i * self.grid_size, 0), (i * self.grid_size, self.board_size))
        # 石を描画
        for x in range(self.grid):
            for y in range(self.grid):
                if self.board[y][x] == 1:
                    pygame.draw.circle(win, (0, 0, 0), (x * self.grid_size + self.grid_size // 2, y * self.grid_size + self.grid_size // 2), self.grid_size // 2.5)
                if self.board[y][x] == 2:
                    pygame.draw.circle(win, (255, 255, 255), (x * self.grid_size + self.grid_size // 2, y * self.grid_size + self.grid_size // 2), self.grid_size // 2.5)
        # 石を置ける場所を表示
        for x, y in self.valid_moves:
            if self.turn == self.player_num == 1:
                pygame.draw.circle(win, (0, 0, 0), (x * self.grid_size + self.grid_size // 2, y * self.grid_size + self.grid_size // 2), self.grid_size // 6)
            elif self.turn == self.player_num == 2:
                pygame.draw.circle(win, (255, 255, 255), (x * self.grid_size + self.grid_size // 2, y * self.grid_size + self.grid_size // 2), self.grid_size // 6)
        # 前の手を表示
        if self.prev_move:
            x, y = self.prev_move
            pygame.draw.circle(win, (255, 0, 0), (x * self.grid_size + self.grid_size // 2, y * self.grid_size + self.grid_size // 2), self.grid_size // 2.5, 3)
        # プレイヤーの色を表示
        font = pygame.font.Font(None, 50)
        if self.player_num == 1:
            player_text = font.render("You are Black", True, (0, 0, 0))
        else:
            player_text = font.render("You are White", True, (0, 0, 0))
        # ターン表示
        if self.turn == 1:
            turn = font.render("Black turn", True, (0, 0, 0))
        else:
            turn = font.render("White turn", True, (0, 0, 0))
        # スコア表示
        font = pygame.font.Font(None, 30)
        score = self.count()
        score_text = font.render(f"Black: {score[0]}  White: {score[1]}", True, (0, 0, 0))
        win.blit(player_text, (10, self.board_size + 10))
        win.blit(score_text, (400, self.board_size + 10))
        win.blit(turn, (10, self.board_size + 50))

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
        self.win.fill((255, 255, 255))
        running = True
        if not self.gameover:
            while running:  # イベントループ
                for e in pygame.event.get():  # イベント取得
                    if e.type == pygame.QUIT:
                        running = False
                    if e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_ESCAPE:
                            running = False
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        x = e.pos[0] // self.grid_size
                        y = e.pos[1] // self.grid_size
                        sock.sendall((json.dumps({"type" : "move", "x" : x, "y" : y}) + "\n").encode())
                self.draw(self.win)
                # ゲーム終了
                if self.gameover:
                    self.end(self.win)
                pygame.display.update()

        pygame.quit()