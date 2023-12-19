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
class CustomTreeNode:
    def __init__(self, color: GO_COLOR) -> None:
        self.move: GO_POINT = NO_POINT
        self.color: GO_COLOR = color
        self.n_visits: int = 0
        self.n_opponent_wins: float = 0
        self.h_value: int = None
        self.parent: 'CustomTreeNode' = self
        self.children: Dict[GO_POINT, 'CustomTreeNode'] = {}
        self.exp: bool = False
    def backpropagate(self, winner: GO_COLOR) -> None:
        """
        Backpropagate the result of the game up the tree.
        """
        node = self
        while node is not None and not node.is_root():
            node.update(winner)
            node = node.parent

    def is_fully_expanded(self) -> bool:
        """
        Check if all possible children are expanded.
        """
        return len(self.children) == len(self.parent.children)

    def simulate(self, board: GoBoard) -> GO_COLOR:
        """
        Simulate a random playout from the current node's board state.
        Returns the color of the winning player.
        """
        temp_board = board.copy()
        current_color = self.color
        while not temp_board.is_game_over():
            moves = temp_board.get_legal_moves(current_color)
            if moves:
                move = choice(moves)
                temp_board.play_move(move, current_color)
            else:
                temp_board.play_move(PASS, current_color)
            current_color = get_opponent(current_color)
        return temp_board.get_winner()

    def best_move(self) -> GO_POINT:
        """
        Return the move associated with the child having the highest win rate.
        """
        best_winrate = -1
        best_move = NO_POINT
        for move, child in self.children.items():
            winrate = child.n_opponent_wins / child.n_visits if child.n_visits > 0 else 0
            if winrate > best_winrate:
                best_winrate = winrate
                best_move = move
        return best_move

    def tree_size(self) -> int:
        """
        Returns the size of the subtree rooted at this node.
        """
        size = 1  # Count this node
        for child in self.children.values():
            size += child.tree_size()
        return size
    def set_parent(self, parent: 'CustomTreeNode') -> None:
        self.parent: 'CustomTreeNode' = parent

    def expdf(self, board: GoBoard, color: GO_COLOR) -> None:
        opp_color = get_opponent(board.current_player)
        moves = board.get_empty_points()
        for move in moves:
            node = CustomTreeNode(opp_color)
            node.move = move
            node.set_parent(self)
            self.children[move] = node
        self.exp = True
    
    def select_in_tree(self, exploration: float, heuristic_weight: float, board: GoBoard) -> Tuple[GO_POINT, 'CustomTreeNode']:
        selected_child = None
        uct_value = -1
        for move, child in self.children.items():
            if child.n_visits == 0:
                return child.move, child
            if child.h_value is None:
                child.h_value = board.cc_heur(child.move, child.color)
            current_uct_value = self.uct_custom(child.n_opponent_wins, child.n_visits, self.n_visits, exploration, child.h_value, heuristic_weight)
            if current_uct_value > uct_value:
                uct_value = current_uct_value
                selected_child = child
        return selected_child.move, selected_child
    
    def select_best_child(self) -> Tuple[GO_POINT, 'CustomTreeNode']:
        max_visits = -1
        best_child = None
        for move, child in self.children.items():
            if child.n_visits > max_visits:
                max_visits = child.n_visits
                best_child = child
        return best_child.move, best_child
    
    def update(self, winner: GO_COLOR) -> None:
        self.n_opponent_wins += self.color != winner
        self.n_opponent_wins -= (winner == 0) / 2
        self.n_visits += 1
        if not self.is_root():
            self.parent.update(winner)
    
    def is_leaf(self) -> bool:
        return len(self.children) == 0
    
    def is_root(self) -> bool:
        return self.parent == self
    
    def __str__(self) -> str:
        return f"Move: {self.move}, Color: {self.color}, Wins: {self.n_opponent_wins}, Visits: {self.n_visits}"
    
    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def uct_custom(child_wins: int, child_visits: int, parent_visits: int, exploration: float, heuristic: float, heuristic_weight: float) -> float:
        return child_wins / child_visits + exploration * sqrt(log(parent_visits) / child_visits) + ((heuristic_weight / (child_visits + 1)) * heuristic)
