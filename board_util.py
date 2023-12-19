"""
board_util.py
Utility functions for Go board.
"""

import numpy as np
import random
from typing import List
from board_base import GO_COLOR, GO_POINT, PASS
from board import GoBoard

class GoBoardUtil(object):
    @staticmethod
    def generate_legal_moves(board: GoBoard, color: GO_COLOR) -> List:
        """
        generate a list of all legal moves on the board.
        Does not include the Pass move.

        Arguments
        ---------
        board:
            a GoBoard
        color:
            the color to generate the move for.
        """
        moves: np.ndarray[GO_POINT] = board.get_empty_points()
        # TODO use generator instead.
        legal_moves: List[GO_POINT] = []
        # TODO use generator instead.
        for move in moves:
            if board.is_legal(move, color):
                legal_moves.append(move)
        return legal_moves

    @staticmethod
    def generate_random_move(board: GoBoard, color: GO_COLOR, 
                             use_eye_filter: bool) -> GO_POINT:
        """
        Generate a random move.
        Return PASS if no move found

        Arguments
        ---------
        board : np.array
            a 1-d array representing the board
        color : BLACK, WHITE
            the color to generate the move for.
        """
        moves: np.ndarray[GO_POINT] = board.get_empty_points()
        np.random.shuffle(moves)
        for move in moves:
            legal: bool = not (
                use_eye_filter and board.is_eye(move, color)
            ) and board.is_legal(move, color)
            if legal:
                return move
        return PASS

    @staticmethod
    def generate_random_moves(board: GoBoard, use_eye_filter: bool) -> List:
        """
        Return a list of random (legal) moves with eye-filtering.
        """
        empty_points: np.ndarray[GO_POINT] = board.get_empty_points()
        color: GO_COLOR = board.current_player
        moves: List[GO_POINT] = []
        for move in empty_points:
            legal: bool = \
                not (
                    use_eye_filter and board.is_eye(move, color)
                ) and board.is_legal(move, color)
            if legal:
                moves.append(move)
        return moves

    @staticmethod
    def get_twoD_board(go_board: GoBoard) -> np.ndarray:
        """
        Return: numpy array
        a two dimensional numpy array with the goboard.
        Shows stones and empty points as encoded in board_base.py.
        Result is not padded with BORDER points.
        Rows 1..size of goboard are copied into rows 0..size - 1 of board2d
        Then the board is flipped up-down to be consistent with the
        coordinate system in GoGui (row 1 at the bottom).
        """
        size: int = go_board.size
        board2d: np.ndarray[GO_POINT] = np.zeros((size, size), dtype=GO_POINT)
        for row in range(size):
            start: int = go_board.row_start(row + 1)
            board2d[row, :] = go_board.board[start : start + size]
        board2d = np.flipud(board2d)
        return board2d
