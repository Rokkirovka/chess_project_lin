from flask import jsonify
from flask_restful import reqparse, Resource
from data import db_session
from data.analyzes import Analysis
from data.engine import engine_analysis
from data.games import Game
from data.users import User


class AnalysisResource(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('fen', type=str)
        parser.add_argument('depth', type=int)
        args = parser.parse_args()
        fen = args['fen']
        depth = args['depth']
        engine_analysis(fen, depth=depth)
        session = db_session.create_session()
        analysis = session.query(Analysis).filter(Analysis.fen == str(fen)).first()
        dct = analysis.to_dict(only=('best_move', 'fen', 'score'))
        session.close()
        return jsonify(dct)


class UserResource(Resource):
    def get(self, user_id):
        session = db_session.create_session()
        user = session.get(User, user_id)
        dct = user.to_dict(only=('id', 'nick', 'rating', 'registration_date'))
        session.close()
        return jsonify(dct)


class UserListResource(Resource):
    def get(self):
        session = db_session.create_session()
        users = session.query(User).all()
        dct = [user.to_dict(only=('id', 'nick', 'rating', 'registration_date')) for user in users]
        session.close()
        return jsonify(dct)


class GameResource(Resource):
    def get(self, game_id):
        session = db_session.create_session()
        game = session.get(Game, game_id)
        dct = game.to_dict()
        session.close()
        return jsonify(dct)


class GameListResource(Resource):
    def get(self):
        session = db_session.create_session()
        games = session.query(Game).all()
        dct = [game.to_dict() for game in games]
        session.close()
        return jsonify(dct)
