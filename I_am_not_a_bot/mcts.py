from board_base import opponent as get_opponent, BLACK, WHITE, PASS, GO_COLOR, GO_POINT, NO_POINT, coord_to_point
from board import GoBoard
from board_util import GoBoardUtil
from gtp_connection import point_to_coord, format_point
import numpy as np
import os, sys
from typing import Dict, Tuple
import time
from math import sqrt, log
from random import choice
from tree import CustomTreeNode

class CustomMCTS:
    def __init__(self) -> None:
        self.root: 'CustomTreeNode' = CustomTreeNode(BLACK)
        self.root.set_parent(self.root)
        self.toplay: GO_COLOR = BLACK

    def backpropagate(self, node: 'CustomTreeNode', winner: GO_COLOR) -> None:
        while node != self.root:
            node.update(winner)
            node = node.parent

    def expand(self, node: 'CustomTreeNode', board: GoBoard) -> None:
        moves = board.get_legal_moves(node.color)
        for move in moves:
            if move not in node.children:
                new_node = CustomTreeNode(get_opponent(node.color))
                new_node.set_parent(node)
                node.children[move] = new_node

    def best_move(self) -> GO_POINT:
        best_win_ratio = -1.0
        best_move = None
        for move, child in self.root.children.items():
            win_ratio = child.win_count / child.visit_count if child.visit_count > 0 else 0
            if win_ratio > best_win_ratio:
                best_win_ratio = win_ratio
                best_move = move
        return best_move
    
    def rollout(self, board: GoBoard, color: GO_COLOR) -> GO_COLOR:
        while True:
            terminal, winner = board.EndGame()
            if terminal:
                return winner   
            moves: np.ndarray[GO_POINT] = board.get_empty_points()
            move = choice(moves)
            board.play_move(move, board.current_player)
    
    def get_move(self,board: GoBoard,color: GO_COLOR,time_limit: int,exp: float,hw: float) -> GO_POINT:
        self.solve_start_time = time.time()
        if self.toplay != color:
            sys.stderr.write("Tree is for the wrong color to play. Deleting.\n")
            sys.stderr.flush()
            self.toplay = color
            self.root = CustomTreeNode(color)
        self.exploration = exp
        self.heuristic_weight = hw
        if not self.root.exp:
            self.root.expdf(board, color)
        while time.time() - self.solve_start_time < (time_limit - 0.03):
            copied_board = board.copy()
            self.search(copied_board, color)

        best_move, best_child = self.root.select_best_child()
        return best_move
    def search(self, board: GoBoard, color: GO_COLOR) -> None:
        node = self.root
        if not node.exp:
            node.expdf(board, color)
        while not node.is_leaf():
            move, next_node = node.select_in_tree(self.exploration, self.heuristic_weight, board)
            x = board.play_move(move, color)
            color = get_opponent(color)
            node = next_node
        if not node.exp:
            node.expdf(board, color)
        
        winner = self.rollout(board, color)
        node.update(winner)
    def update_with_move(self, last_move: GO_POINT) -> None:
        if last_move in self.root.children:
            self.root = self.root.children[last_move]
        else:
            self.root = CustomTreeNode(get_opponent(self.toplay))
        self.root.parent = self.root
        self.toplay = get_opponent(self.toplay)
    
    def reset_tree(self) -> None:
        self.root = CustomTreeNode(self.toplay)
        self.root.set_parent(self.root)

    def get_toplay(self) -> GO_COLOR:
        return self.toplay
    
    def get_root(self) -> 'CustomTreeNode':
        return self.root
    
    def get_exploration(self) -> float:
        return self.exploration
    
    def get_heuristic_weight(self) -> float:
        return self.heuristic_weight
    
    def set_exploration(self, exploration: float) -> None:
        self.exploration = exploration

    def set_heuristic_weight(self, heuristic_weight: float) -> None:
        self.heuristic_weight = heuristic_weight
