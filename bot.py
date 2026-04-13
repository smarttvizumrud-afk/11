import os, io, chess, chess.pgn, chess.engine, requests, json, time, random
from threading import Thread
from flask import Flask # Добавили маленькую библиотеку для "будильника"

# --- 1. МИНИ-СЕРВЕР ДЛЯ БУДИЛЬНИКА ---
app = Flask('')
@app.route('/')
def home():
    return "Бот Леонид живет здесь!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- 2. КОД БОТА ---
TOKEN = "lip_QfPG2iGVBtUKKNWYVrN1" 
BOT_ID = "leonidnim"
SOURCE_ACC = "rehbwf" 
headers = {"Authorization": f"Bearer {TOKEN}"}

class LeonidBot:
    def __init__(self):
        self.book = {}
        self.engine = None
        self.setup()

    def setup(self):
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
        except: pass
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        self.engine.configure({"Skill Level": 20})

    def get_move(self, board, time_limit):
        fen = board.fen().split()[0]
        if fen in self.book: return random.choice(self.book[fen])
        return self.engine.play(board, chess.engine.Limit(time=max(0.1, time_limit/25))).move.uci()

def start_bot():
    bot = LeonidBot()
    print("🚀 Leonidnim Online!")
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
                            my_time_ms = state.get('wtime' if my_color == chess.WHITE else 'btime', 10000)
                            move = bot.get_move(board, float(my_time_ms)/1000)
                            requests.post(f"https://lichess.org/api/bot/game/{game_id}/move/{move}", headers=headers)
                        elif board.is_game_over(): break
        except: time.sleep(5)

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    Thread(target=run_web).start()
    # Запускаем бота
    start_bot()
