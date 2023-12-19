#!/usr/bin/python3
# Set the path to your python3 above

"""
Go0 random Go player
Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller
"""
from gtp_connection import GtpConnection
from board_base import DEFAULT_SIZE, GO_POINT, GO_COLOR, opponent
from board import GoBoard
from board_util import GoBoardUtil
from board_base import EMPTY, BLACK, WHITE, PASS
from engine import GoEngine

import numpy as np


def undo(board, move):
    board.board[move] = EMPTY
    board.current_player = opponent(board.current_player)


def play_move(board, move, color):
    board.play_move(move, color)


def game_result(board):
    result1 = board.detect_five_in_a_row()
    result2 = EMPTY
    if board.get_captures(BLACK) >= 10:
        result2 = BLACK
    elif board.get_captures(WHITE) >= 10:
        result2 = WHITE

    if (result1 == BLACK) or (result2 == BLACK):
        return BLACK
    elif (result1 == WHITE) or (result2 == WHITE):
        return WHITE
    elif board.get_empty_points().size == 0:
        return PASS
    return None


class NinukiFlatMC(GoEngine):
    def __init__(self, num_simulations=10):
        """
        Ninuki player that selects move by Flat Monte Carlo Search.
        Resigns only at the end of game.
        """
        GoEngine.__init__(self, "NinukiFlatMC", 1.0)
        # self.name = "NinukiFlatMC"
        # self.version = 1.0
        self.simulations_per_move = num_simulations
        self.best_move = None
        self.move = None

    def simulate(self, originalboard, toPlay):
        """
        Run a simulated game for a given starting move.
        """
        sims = []
        stats = [0] * 3
        res = game_result(originalboard)
        for _ in range(self.simulations_per_move):
            sim = 10
            res = game_result(originalboard)
            board = originalboard.copy()
            while res is None:
                move = GoBoardUtil.generate_random_move(
                    board, board.current_player, False)
                play_move(board, move, board.current_player)
                res = game_result(board)
                sim += 1
            stats[res] += 1
            sims.append(sim)
        sim = np.mean(sims)
        eval = (stats[toPlay] + 0.5 * stats[EMPTY]) / sim
        return eval

    def get_random_move(self, original_board, color):
        moves = GoBoardUtil.generate_legal_moves(original_board, color)
        return moves

    def get_move(self, original_board, color):
        """
        Genmove function using one-ply MC search.
        """
        moves = GoBoardUtil.generate_legal_moves(original_board, color)
        numMoves = len(moves)
        score = [0] * numMoves
        for i in range(numMoves):
            board = original_board.copy()
            play_move(board, moves[i], color)
            res = game_result(board)
            if res == color:
                score[i] = 1
            elif res == opponent(color):
                score[i] = 0
            else:
                score[i] = self.simulate(board, color)
            board = original_board.copy()
        bestIndex = np.argmax(score)
        best = moves[bestIndex]
        return best

    def get_win(self, original_board, color):
        moves = GoBoardUtil.generate_legal_moves(original_board, color)
        numMoves = len(moves)
        moves1 = []
        for i in range(numMoves):
            board = original_board.copy()
            play_move(board, moves[i], color)
            res = game_result(board)
            if res == color:
                moves1.append(moves[i])
            board = original_board.copy()
        return moves1

    def get_blockwin(self, original_board, color):
        moves = GoBoardUtil.generate_legal_moves(original_board, color)
        
        oppwin = []
        numMoves = len(moves)
        color1 = opponent(color)
        moves1 = []
        for i in range(numMoves):
            board = original_board.copy()
            play_move(board, moves[i], color1)
            res = game_result(board)
            if res == opponent(color):
                moves1.append(moves[i])
                oppwin.append(moves[i])
            if board.get_captures(color1) + original_board.get_captures(color1) >= 10:
                moves1.append(moves[i])

        for i in range(numMoves):
            board = original_board.copy()
            play_move(board, moves[i], color)
            board1 = board.copy()
            for move in oppwin:
                board1 = board.copy()
                play_move(board1, move, color1)
                res = game_result(board1)
                if res != opponent(color) and moves[i] not in moves1:
                    moves1.append(moves[i])
                
            board = original_board.copy()
        return moves1
    
    def get_capture(self, original_board, color):
        moves = GoBoardUtil.generate_legal_moves(original_board, color)
        numMoves = len(moves)
        moves1 = []
        for i in range(numMoves):
            board = original_board.copy()
            play_move(board, moves[i], color)
            if board.get_captures(color) > original_board.get_captures(color):
                moves1.append(moves[i])
            board = original_board.copy()
        return moves1

    def get_openfour(self, original_board, color):
        board = original_board.copy()
        res = board.detect_open_four()

        final_res = []
        for arr in res:
            for tup in arr:
                if tup[0] == color:
                    final_res.append(tup[1])

        if final_res:
            return final_res
        
        return None
    
    def random_policy(self, board, color):
        return GoBoardUtil.generate_legal_moves(board, color)


def run() -> None:
    """
    start the gtp connection and wait for commands.
    """
    board: GoBoard = GoBoard(DEFAULT_SIZE)
    con: GtpConnection = GtpConnection(NinukiFlatMC(), board)
    con.start_connection()


if __name__ == "__main__":
    run()
