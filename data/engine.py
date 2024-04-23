from data.chess_to_html import ImprovedBoard
import chess
import chess.engine
from data import db_session
from data.analyzes import Analysis


def engine_move(fen, level):
    board = ImprovedBoard(fen)
    engine = chess.engine.SimpleEngine.popen_uci("data/stockfish/stockfish-ubuntu-x86-64-avx2")
    engine.configure({"Skill Level": level})
    result = engine.play(board, chess.engine.Limit(time=0.3))
    engine.quit()
    return result.move


def engine_analysis(fen, time=0.1, depth=5):
    db_sess = db_session.create_session()
    analysis = db_sess.query(Analysis).filter(Analysis.fen == str(fen)).first()
    if not analysis:
        board = ImprovedBoard(fen)
        engine = chess.engine.SimpleEngine.popen_uci("data/stockfish/stockfish-ubuntu-x86-64-avx2")
        info = engine.analyse(board, chess.engine.Limit(time=time, depth=depth))
        engine.quit()
        analysis = Analysis()
        analysis.fen = fen
        analysis.score = info['score'].white().__str__()
        if 'pv' in info:
            analysis.best_move = info['pv'][0].__str__()
        else:
            analysis.best_move = None
        db_sess.add(analysis)
        db_sess.commit()
    score = analysis.score
    db_sess.close()
    if '#' in score:
        if '-' in str(score):
            rate = 100
        else:
            rate = 0
    else:
        rate = round((3000 - int(score)) / 60, 2)
    return rate, score
