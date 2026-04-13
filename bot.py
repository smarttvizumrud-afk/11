import os
import io
import chess
import chess.pgn
import requests
import json
import time
import random
from threading import Thread
from flask import Flask

# --- 1. ФЕЙКОВЫЙ СЕРВЕР ДЛЯ RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Бот Леонид Жив! Пингуй меня, чтобы я не спал."

def run_web():
    # Порт 10000 — стандарт для Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. НАСТРОЙКИ БОТА ---
TOKEN = "lip_QfPG2iGVBtUKKNWYVrN1" 
BOT_ID = "leonidnim"
SOURCE_ACC = "rehbwf" 
headers = {"Authorization": f"Bearer {TOKEN}"}

class LeonidBot:
    def __init__(self):
        self.book = {}
        self.setup()

    def setup(self):
        print("📥 Загрузка базы мастера...")
        try:
            res = requests.get(f"https://lichess.org/api/games/user/{SOURCE_ACC}?max=400")
            if res.status_code == 200:
                pgn_data = io.StringIO(res.text)
                while True:
                    game = chess.pgn.read_game(pgn_data)
                    if not game: break
                    board = game.board()
                    for move in game.mainline_moves():
                        fen = board.fen().split()[0]
                        if fen not in self.book: self.book[fen] = []
                        self.book[fen].append(move.uci())
                        board.push(move)
                print(f"✅ База готова!")
        except:
            print("⚠️ Ошибка базы.")

    def get_move(self, board):
        fen = board.fen().split()[0]
        if fen in self.book:
            return random.choice(self.book[fen])
        # Если ход не в базе, делаем случайный ход (так как Stockfish на Free Render не завести)
        return random.choice(list(board.legal_moves)).uci()

def start_bot():
    bot = LeonidBot()
    print("🚀 Leonidnim Online и готов к игре!")
    while True:
        try:
            r = requests.get("https://lichess.org/api/stream/event", headers=headers, stream=True, timeout=15)
            for line in r.iter_lines():
                if not line: continue
                event = json.loads(line.decode('utf-8'))
                
                if event['type'] == 'challenge':
                    requests.post(f"https://lichess.org/api/challenge/{event['challenge']['id']}/accept", headers=headers)
                
                elif event['type'] == 'gameStart':
                    game_id = event['game']['id']
                    g_res = requests.get(f"https://lichess.org/api/bot/game/stream/{game_id}", headers=headers, stream=True)
                    my_color = None
                    
                    for g_line in g_res.iter_lines():
                        if not g_line: continue
                        g_data = json.loads(g_line.decode('utf-8'))
                        
                        if g_data.get('type') == 'gameFull':
                            white_id = g_data['white'].get('id', '').lower()
                            my_color = chess.WHITE if white_id == BOT_ID.lower() else chess.BLACK
                        
                        state = g_data if g_data.get('type') == 'gameState' else g_data.get('state', {})
                        moves = state.get('moves', "").split()
                        board = chess.Board()
                        for m in moves: board.push_uci(m)
                        
                        if not board.is_game_over() and board.turn == my_color:
                            move = bot.get_move(board)
                            requests.post(f"https://lichess.org/api/bot/game/{game_id}/move/{move}", headers=headers)
                        elif board.is_game_over():
                            break
        except:
            time.sleep(5)

# --- 3. ЗАПУСК ---
if __name__ == "__main__":
    # Запускаем сайт-обманку в отдельном потоке
    server_thread = Thread(target=run_web)
    server_thread.daemon = True
    server_thread.start()
    
    # Запускаем самого бота
    start_bot()
