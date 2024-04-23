from chess import Board, square_name, square_file, square_rank, Piece, Move, parse_square

pieces = {Piece.from_symbol('r'): '♜',
          Piece.from_symbol('n'): '♞',
          Piece.from_symbol('b'): '♝',
          Piece.from_symbol('q'): '♛',
          Piece.from_symbol('k'): '♚',
          Piece.from_symbol('p'): '♟',
          Piece.from_symbol('R'): '♖',
          Piece.from_symbol('N'): '♘',
          Piece.from_symbol('B'): '♗',
          Piece.from_symbol('Q'): '♕',
          Piece.from_symbol('K'): '♔',
          Piece.from_symbol('P'): '♙',
          None: ''}

colors = {'light': '#e9eef2',
          'dark': ' #8ca2ad',
          'light-red': '#507b65',
          'dark-red': '#789b81',
          'light-green': '#c3d888',
          'light-purple': '#876c99'}


class ImprovedBoard(Board):
    def make_move(self, move):
        current = None
        if move[:2] == move[2:]:
            current = None
        elif self.color_at(parse_square(move[2:])) == self.turn:
            current = move[2:]
        if move[:2] != move[2:] and 'null' not in move:
            if (move[1] == '7' and move[3] == '8' and pieces[self.piece_at(parse_square(move[:2]))] == '♙'
                    or move[1] == '2' and move[3] == '1' and pieces[self.piece_at(parse_square(move[:2]))] == '♟'):
                move += 'q'
            push_move = Move.from_uci(move)
            if self.is_legal(push_move):
                self.push(push_move)
                current = None
        return current

    def get_board_for_json(self, selected=None, move_number=-1):
        board_copy = self.copy()
        if move_number != -1:
            for _ in range(len(board_copy.move_stack) - move_number):
                board_copy.pop()
        json_board = []
        for i in range(64):
            cell = {
                'name': square_name(i),
                'piece': pieces[board_copy.piece_at(i)],
                'color': colors['light'] if (square_file(i) + square_rank(i)) % 2 else colors['dark']
            }
            if board_copy.move_stack:
                if board_copy.move_stack[-1].uci()[2:] == square_name(i) or board_copy.move_stack[-1].uci()[
                                                                            :2] == square_name(i):
                    cell['color'] = colors['light-green']
            if board_copy.piece_at(i) == Piece.from_symbol('K') and board_copy.turn and board_copy.is_check():
                cell['color'] = colors['light-purple']
            if board_copy.piece_at(i) == Piece.from_symbol('k') and not board_copy.turn and board_copy.is_check():
                cell['color'] = colors['light-purple']
            if selected is not None:
                if selected == square_name(i):
                    cell['color'] = colors['dark-red']
                elif board_copy.is_legal(Move.from_uci(selected + square_name(i))) or board_copy.is_legal(
                        Move.from_uci(selected + square_name(i) + 'q')):
                    cell['color'] = colors['light-red']
            json_board.append(cell)
        return {'board': json_board, 'current': selected, 'board_fen': board_copy.fen()}
