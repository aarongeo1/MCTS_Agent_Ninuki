from board_base import EMPTY, BLACK, WHITE, PASS
from board_base import GO_POINT, NO_POINT
from board import GoBoard
import random
DEFAULT_KOMI = 6.5


class GoEngine:
    def __init__(self, name: str, version: float) -> None:
        """
        name : name of the player used by the GTP interface
        version : version number used by the GTP interface
        """
        self.name: str = name
        self.version: float = version
        self.komi: float = DEFAULT_KOMI
        self.policy_type = "random"  # Default policy type

    def get_move(self, board: GoBoard, color: int) -> GO_POINT:
        """
        name : name of the player used by the GTP interface
        version : version number used by the GTP interface
        """
        pass

    def get_random_move(self, board: GoBoard, color: int) -> GO_POINT:
        pass

    def get_win(self, board: GoBoard, color: int) -> GO_POINT:
        """
        name : name of the player used by the GTP interface
        version : version number used by the GTP interface
        """
        pass

    def get_blockwin(self, board: GoBoard, color: int) -> GO_POINT:
        """
        name : name of the player used by the GTP interface
        version : version number used by the GTP interface
        """
        pass

    def get_capture(self, board: GoBoard, color: int) -> GO_POINT:
        """
        name : name of the player used by the GTP interface
        version : version number used by the GTP interface
        """
        pass

    def get_openfour(self, board: GoBoard, color: int) -> GO_POINT:
        """
        name : name of the player used by the GTP interface
        version : version number used by the GTP interface
        """
        pass

    def set_policy_type(self, policy_type):
        self.policy_type = policy_type

    def generate_move(self, board):
        if self.policy_type == "random":
            return [self.get_move(board, board.current_player)]
            

        elif self.policy_type == "rule_based":
            move, type = self.rule_based_policy(board)
            return move

    def generate_move_policy(self, board):
        if self.policy_type == "random":
            return self.get_random_move(board, board.current_player), "Random"
        elif self.policy_type == "rule_based":

            move, type = self.rule_based_policy(board)
            return move, type


    def rule_based_policy(self, board):
        # Implement logic for each rule (Win, BlockWin, OpenFour, Capture, Random)
        # Check for Win
        win = self.get_win(board, board.current_player)
        if win:
            return win, "Win"

        lose = self.get_blockwin(board, board.current_player)
        
        if lose:
            return lose, "BlockWin"
        
        openfour = self.get_openfour(board, board.current_player)
        if openfour:
            return openfour, "OpenFour"
        
        capture = self.get_capture(board, board.current_player)
        if capture:
            return capture, "Capture"

        # Default to Random
        return self.get_random_move(board, board.current_player)

    def check_win(self, board):
        # Check for Win
        win_moves = []
        for move in board.get_empty_points():
            if board.detect_five_in_a_row(move, board.current_player):
                win_moves.append(move)
        return win_moves

    def end_of_game(board: GoBoard):
        """
        Return who won 
        """
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
