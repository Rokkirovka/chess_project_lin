import datetime
from random import choice

import chess.engine
from chess import Move, parse_square
from flask import Flask, render_template, request, redirect, jsonify, session
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask_socketio import SocketIO, emit
from flask_restful import Api
from data import chess_resources
from data.engine import engine_analysis, engine_move

from data import db_session
from data.chess_to_html import ImprovedBoard
from data.games import Game, EngineGame
from data.rating_calculator import rating_calculation
from data.users import User
from forms.user import RegisterForm, GameForm, LoginForm, GameEngineForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
api = Api(app)
login_manager = LoginManager()
login_manager.init_app(app)
socketio = SocketIO(app)
api.add_resource(chess_resources.AnalysisResource, '/api/analysis', endpoint='analysis')
api.add_resource(chess_resources.UserResource, '/api/user/<int:user_id>')
api.add_resource(chess_resources.UserListResource, '/api/users')
api.add_resource(chess_resources.GameResource, '/api/game/<int:game_id>')
api.add_resource(chess_resources.GameListResource, '/api/games')


def main():
    db_session.global_init('db/chess.db')
    app.run(host='0.0.0.0', port=5000)


@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/create_game', methods=['GET', 'POST'])
@login_required
def new_game():
    db_sess = db_session.create_session()
    user = db_sess.get(User, current_user.id)
    game = Game()
    color = choice(['1', '2'])
    if color == '1':
        game.white_player = user.id
    else:
        game.black_player = user.id
    game.fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    game.is_finished = False
    game.moves = ''
    game.type = 'friend'
    db_sess.add(game)
    db_sess.commit()
    game_id = str(game.id)
    db_sess.close()
    return redirect('/game/' + game_id)


@app.route('/fast_game', methods=['GET', 'POST'])
@login_required
def fast_game():
    db_sess = db_session.create_session()
    user = db_sess.get(User, current_user.id)
    game = db_sess.query(Game).filter(
        ((Game.black_player == int(user.id)) | (Game.white_player == int(user.id))) & (Game.type == 'fast')).filter(
        (Game.black_player == None) | (Game.white_player == None)).first()
    if not game:
        games = db_sess.query(Game).filter(
            ((Game.black_player == None) | (Game.white_player == None)) & (Game.type == 'fast')).all()
        if games:
            game = choice(games)
            print(game.white_player, game.black_player)
            if game.white_player is None:
                game.white_player = user.id
            else:
                game.black_player = user.id
            db_sess.commit()
            socketio.emit('reload')
        else:
            game = Game()
            color = choice(['1', '2'])
            if color == '1':
                game.white_player = user.id
            else:
                game.black_player = user.id
            game.fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
            game.is_finished = False
            game.moves = ''
            game.type = 'fast'
            db_sess.add(game)
        db_sess.commit()
    game_id = str(game.id)
    db_sess.close()
    return redirect('/game/' + game_id)


@app.route('/create_engine_game', methods=['GET', 'POST'])
@login_required
def new_engine_game():
    form = GameEngineForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        old_game = db_sess.query(EngineGame).filter(EngineGame.player == int(current_user.id)).first()
        if old_game:
            db_sess.delete(old_game)
        game = EngineGame()
        if form.color.data == '3':
            color = choice(['white', 'black'])
        else:
            color = form.color.data
        board = ImprovedBoard()
        game.level = form.level.data
        if color == 'black':
            board.push(engine_move(board.fen(), game.level))
        db_sess.add(game)
        game.fen = board.fen()
        game.is_finished = False
        game.moves = ' '.join(move.uci() for move in board.move_stack)
        game.color = color
        game.player = current_user.id
        db_sess.commit()
        db_sess.close()
        return redirect(f'/engine_game/{current_user.id}')
    return render_template('create_engine_game.html', form=form)


@app.route('/engine_game/<int:user_id>')
@login_required
def play_engine_game(user_id):
    db_sess = db_session.create_session()

    game = db_sess.query(EngineGame).filter(EngineGame.player == int(user_id)).first()
    if not game:
        return redirect('/create_engine_game')
    board = get_board_game(game)
    player = db_sess.get(User, game.player)
    color = game.color
    if color == 'white':
        white_player = player
        black_player = None
    else:
        white_player = None
        black_player = player
    if request.is_json:
        if current_user.id == user_id:
            if color == 'white' and board.turn or color == 'black' and not board.turn:
                if request.args.get('type') == 'cell':
                    cell = request.args.get('cell')
                    if board.color_at(parse_square(cell)) == board.turn:
                        cur = cell
                    else:
                        cur = None
                else:
                    cur = board.make_move(request.args.get('move'))
                    update_game(game, *check_position(board.fen(), white_player, black_player), white_player, black_player)
                    args = board.get_board_for_json()
                    args['path'] = request.path
                    socketio.emit('update_board', args)
                    if color == 'white' and not board.turn or color == 'black' and board.turn and not game.is_finished:
                        en_move = engine_move(board.fen(), game.level)
                        if en_move is not None:
                            board.push(en_move)
                    update_game(game, *check_position(board.fen(), white_player, black_player), white_player, black_player)
                    game.fen = board.fen()
                    game.moves = ' '.join(move.uci() for move in board.move_stack)
                    db_sess.commit()
                    db_sess.close()
                    args = board.get_board_for_json()
                    args['path'] = request.path
                    socketio.emit('update_board', args)
                return jsonify(board.get_board_for_json(selected=cur))
            return jsonify(board.get_board_for_json())
        return jsonify(board.get_board_for_json())
    lst = board.get_board_for_json()['board']
    if current_user.id == user_id:
        role = color
    else:
        role = 'spectator'
    db_sess.close()
    return render_template('game.html', board=lst, role=role,
                           white_player=white_player, black_player=black_player, end_game=game.is_finished,
                           result=game.result, reason=game.reason, turn=board.turn, type='engine', url=request.url)


@app.route('/game/<int:game_id>')
def play_game(game_id):
    db_sess = db_session.create_session()

    game = db_sess.get(Game, game_id)
    if current_user.is_authenticated:
        if game.white_player is None and game.black_player != current_user.id or game.black_player is None and game.white_player != current_user.id:
            if game.white_player is None:
                game.white_player = current_user.id
            else:
                game.black_player = current_user.id
            db_sess.commit()
            socketio.emit('reload')
    board = get_board_game(game)
    white_player = db_sess.get(User, game.white_player)
    black_player = db_sess.get(User, game.black_player)
    if request.is_json:
        if current_user == white_player and board.turn or current_user == black_player and not board.turn:
            if request.args.get('type') == 'cell':
                cell = request.args.get('cell')
                if board.color_at(parse_square(cell)) == board.turn:
                    cur = cell
                else:
                    cur = None
            else:
                cur = board.make_move(request.args.get('move'))
                update_game(game, *check_position(board.fen(), white_player, black_player), white_player, black_player)
                args = board.get_board_for_json()
                args['path'] = request.path
                args['is_finished'] = game.is_finished
                socketio.emit('update_board', args)
                game.fen = board.fen()
                game.moves = ' '.join(move.uci() for move in board.move_stack)
                db_sess.commit()
            dct = board.get_board_for_json(selected=cur)
            dct['is_finished'] = game.is_finished
            dct['reason'] = game.reason
            dct['result'] = game.result
            db_sess.close()
            return jsonify(dct)
        return jsonify(board.get_board_for_json())
    lst = board.get_board_for_json()['board']
    if current_user.is_authenticated:
        if current_user.id == game.white_player:
            role = 'white'
        elif current_user.id == game.black_player:
            role = 'black'
        else:
            role = 'spectator'
    else:
        role = 'spectator'
    db_sess.close()
    return render_template('game.html', board=lst, role=role,
                           white_player=white_player, black_player=black_player, end_game=game.is_finished,
                           result=game.result, reason=game.reason, turn=board.turn, type=game.type, url=request.url, id=game.id)


@app.route('/analysis/<int:game_id>')
def analysis_game(game_id):
    db_sess = db_session.create_session()
    game = db_sess.get(Game, game_id)
    board = get_board_game(game)
    white_player = db_sess.get(User, game.white_player)
    black_player = db_sess.get(User, game.black_player)
    if request.is_json:
        move_number = int(request.args.get('move_number'))
        board_copy = board.copy()
        if move_number != -1:
            for _ in range(len(board_copy.move_stack) - move_number):
                board_copy.pop()
        dct = board.get_board_for_json(move_number=move_number)
        rate, score = engine_analysis(board_copy.fen())
        dct['rate'] = rate
        dct['score'] = str(score)
        db_sess.close()
        return jsonify(dct)
    rate, score = engine_analysis(board.fen())
    moves = [(board.move_stack[x * 2: x * 2 + 2]) for x in range((len(board.move_stack) + 1) // 2)]
    db_sess.close()
    return render_template('analysis_game.html',
                           board=board.get_board_for_json()['board'],
                           white_player=white_player,
                           black_player=black_player,
                           reason=game.reason,
                           result=game.result,
                           moves=moves,
                           score=score,
                           rate=str(rate))


@app.route('/analysis/')
def analysis_position():
    board = ImprovedBoard()
    if request.is_json:
        if request.args.get('board_fen'):
            board = ImprovedBoard(request.args.get('board_fen'))
        if request.args.get('type') == 'cell':
            cell = request.args.get('cell')
            if board.color_at(parse_square(cell)) == board.turn:
                cur = cell
            else:
                cur = None
            dct = board.get_board_for_json(selected=cur)
        else:
            cur = board.make_move(request.args.get('move'))
            rate, score = engine_analysis(board.fen())
            dct = board.get_board_for_json(selected=cur)
            dct['rate'] = rate
            dct['score'] = str(score)
        return jsonify(dct)
    rate, score = engine_analysis(board.fen())
    return render_template('analysis_position.html',
                           board=board.get_board_for_json()['board'],
                           score=score,
                           rate=rate)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(user_id)
    all_games = db_sess.query(Game).filter(((Game.black_player == int(user.id)) |
                                            (Game.white_player == int(user.id))) & (Game.is_finished == 1)).all()
    all_games = {x.id: [x, get_board_game(x).get_board_for_json()] for x in all_games}
    win_games = db_sess.query(Game).filter(((Game.black_player == int(user.id)) & (Game.result == 'Black win')) |
                                           ((Game.white_player == int(user.id)) & (Game.result == 'White win'))).all()
    win_games = {x.id: [x, get_board_game(x).get_board_for_json()] for x in win_games}
    draw_games = db_sess.query(Game).filter(((Game.black_player == int(user.id)) |
                                             (Game.white_player == int(user.id))) & (Game.result == 'Draw')).all()
    draw_games = {x.id: [x, get_board_game(x).get_board_for_json()] for x in draw_games}
    loose_games = db_sess.query(Game).filter(((Game.black_player == int(user.id)) & (Game.result == 'White win')) |
                                             ((Game.white_player == int(user.id)) & (Game.result == 'Black win'))).all()
    loose_games = {x.id: [x, get_board_game(x).get_board_for_json()] for x in loose_games}
    unfinished_games = db_sess.query(Game).filter(((Game.black_player == int(user.id)) |
                                                   (Game.white_player == int(user.id))) & (Game.is_finished == 0)).all()
    unfinished_games = {x.id: [x, get_board_game(x).get_board_for_json()] for x in unfinished_games}
    db_sess.close()
    return render_template('profile.html', user=user,
                           all_games=all_games,
                           win_games=win_games,
                           draw_games=draw_games,
                           loose_games=loose_games,
                           unfinished_games=unfinished_games)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html',
                                   title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter((User.email == str(form.email.data)) |
                                      (User.nick == str(form.nick.data))).first():
            db_sess.close()
            return render_template('register.html',
                                   title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User()
        user.nick = form.nick.data
        user.email = form.email.data
        user.registration_date = datetime.datetime.now()
        user.set_password(form.password.data)
        user.rating = 1500
        db_sess.add(user)
        db_sess.commit()
        login_user(user, remember=True)
        db_sess.close()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == str(form.email.data)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            db_sess.close()
            return redirect("/")
        db_sess.close()
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        db_sess = db_session.create_session()
        nick = request.form['nick'].lower()
        users = db_sess.query(User).filter(User.nick.like(f'%{nick}%')).all()
        db_sess.close()
        return render_template('search.html', users=users)
    return render_template('search.html', users=[])


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    user = db_sess.get(User, user_id)
    db_sess.close()
    return user


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def check_position(fen, white_player=None, black_player=None):
    wr, br = None, None
    is_finished = 1
    board = ImprovedBoard(fen)
    if board.is_checkmate():
        reason = 'Checkmate'
        if board.turn:
            result = 'Black win'
            if white_player is not None and black_player is not None:
                wr = rating_calculation(white_player.rating, black_player.rating, 0)
                br = rating_calculation(black_player.rating, white_player.rating, 1)
        else:
            result = 'White win'
            if white_player is not None and black_player is not None:
                wr = rating_calculation(white_player.rating, black_player.rating, 1)
                br = rating_calculation(black_player.rating, white_player.rating, 0)
    elif board.is_stalemate():
        result = 'Draw'
        reason = 'Stalemate'
        wr = rating_calculation(white_player.rating, black_player.rating, 0.5)
        br = rating_calculation(black_player.rating, white_player.rating, 0.5)
    else:
        reason, is_finished, result = None, 0, None
    return result, reason, is_finished, wr, br


def update_game(game, result, reason, is_finished, wr, br, white_player, black_player):
    if is_finished:
        game.is_finished = 1
        game.result = result
        game.reason = reason
    if wr is not None and br is not None:
        white_player.rating = wr
        black_player.rating = br
    return


def get_board_game(game):
    board = ImprovedBoard()
    moves = game.moves.split()
    for move in moves:
        board.push(chess.Move.from_uci(move))
    return board


if __name__ == '__main__':
    main()
