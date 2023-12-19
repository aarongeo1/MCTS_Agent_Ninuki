"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller.
Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
import traceback
import numpy as np
import threading
import re
import time

from sys import stdin, stdout, stderr
from typing import Any, Callable, Dict, List, Tuple
from cmath import inf
from board_base import (
    BLACK,
    WHITE,
    EMPTY,
    BORDER,
    GO_COLOR, GO_POINT,
    PASS,
    MAXSIZE,
    coord_to_point,
    opponent,
    CUR
)
from board import GoBoard
from board_util import GoBoardUtil
from engine import GoEngine


class GtpConnection:
    def __init__(self, go_engine: GoEngine, board: GoBoard, debug_mode: bool = False) -> None:
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self.transposition_table: Dict[str, Tuple[float, str]] = {}
        self.time = 1
        self.time_copy = 1
        self.thread_active = False
        self.solve_value = ''
        self.board_copy = None
        self.board_copy2 = None
        self.timer_thread = None
        self.timer_thread_1 = None
        self.legal_moves = []
        self.board_color = None

        self._debug_mode: bool = debug_mode
        self.go_engine = go_engine
        self.board: GoBoard = board
        self.commands: Dict[str, Callable[[List[str]], None]] = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-rules_captured_count": self.gogui_rules_captured_count_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd,
            "timelimit": self.timelimit_cmd,
            "solve": self.solve_cmd
        }
        # Initialize Zobrist hash table
        # self.zobrist_hash_table = [[
        #     [np.random.randint(0, 2**32)
        #      for _ in range(self.board.size * self.board.size)]
        #     for _ in range(2)
        # ] for _ in range(self.board.size)]
        new_size = self.board.size + 1  # Replace this with your desired size
        self.zobrist_hash_table = [
            [
                [np.random.randint(0, 2**63-1, dtype=np.int64)
                 for _ in range(new_size * new_size)]
                for _ in range(2)
            ]
            for _ in range(new_size)
        ]

        # Initialize the hash value
        self.current_hash = 0

        # argmap is used for argument checking
        # values: (required number of arguments,
        #          error message on argnum failure)
        self.argmap: Dict[str, Tuple[int, str]] = {
            "boardsize": (1, "Usage: boardsize INT"),
            "komi": (1, "Usage: komi FLOAT"),
            "known_command": (1, "Usage: known_command CMD_NAME"),
            "genmove": (1, "Usage: genmove {w,b}"),
            "play": (2, "Usage: play {b,w} MOVE"),
            "legal_moves": (1, "Usage: legal_moves {w,b}"),
        }

    def write(self, data: str) -> None:
        stdout.write(data)

    def flush(self) -> None:
        stdout.flush()

    def start_connection(self) -> None:
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command: str) -> None:
        """
        Parse command string and execute it
        """
        if len(command.strip(" \r\t")) == 0:
            return
        if command[0] == "#":
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements: List[str] = command.split()
        if not elements:
            return
        command_name: str = elements[0]
        args: List[str] = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".format(
                    traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error("Unknown command")
            stdout.flush()

    def has_arg_error(self, cmd: str, argnum: int) -> bool:
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg: str) -> None:
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg: str) -> None:
        """ Send error msg to stdout """
        stdout.write("? {}\n\n".format(error_msg))
        stdout.flush()

    def respond(self, response: str = "") -> None:
        """ Send response to stdout """
        stdout.write("= {}\n\n".format(response))
        stdout.flush()

    def reset(self, size: int) -> None:
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self) -> str:
        return str(GoBoardUtil.get_twoD_board(self.board))

    def protocol_version_cmd(self, args: List[str]) -> None:
        """ Return the GTP protocol version being used (always 2) """
        self.respond("2")

    def quit_cmd(self, args: List[str]) -> None:
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args: List[str]) -> None:
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args: List[str]) -> None:
        """ Return the version of the  Go engine """
        self.respond(str(self.go_engine.version))

    def clear_board_cmd(self, args: List[str]) -> None:
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args: List[str]) -> None:
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args: List[str]) -> None:
        self.respond("\n" + self.board2d())

    def komi_cmd(self, args: List[str]) -> None:
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args: List[str]) -> None:
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args: List[str]) -> None:
        """ list all supported GTP commands """
        self.respond(" ".join(list(self.commands.keys())))

    def legal_moves_cmd(self, args: List[str]) -> None:
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color: str = args[0].lower()
        color: GO_COLOR = color_to_int(board_color)
        moves: List[GO_POINT] = GoBoardUtil.generate_legal_moves(
            self.board, color)
        gtp_moves: List[str] = []
        for move in moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))

    """
    ==========================================================================
    Assignment 2 - game-specific commands start here
    ==========================================================================
    """
    """
    ==========================================================================
    Assignment 2 - commands we already implemented for you
    ==========================================================================
    """

    def gogui_analyze_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    def gogui_rules_game_id_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond("Ninuki")

    def gogui_rules_board_size_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond(str(self.board.size))

    def gogui_rules_side_to_move_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                # str += '.'
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)

    def gogui_rules_final_result_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        result1 = self.board.detect_five_in_a_row()
        result2 = EMPTY
        if self.board.get_captures(BLACK) >= 10:
            result2 = BLACK
        elif self.board.get_captures(WHITE) >= 10:
            result2 = WHITE

        if (result1 == BLACK) or (result2 == BLACK):
            self.respond("black")
        elif (result1 == WHITE) or (result2 == WHITE):
            self.respond("white")
        elif self.board.get_empty_points().size == 0:
            self.respond("draw")
        else:
            self.respond("unknown")
        return

    def gogui_rules_legal_moves_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        if (self.board.detect_five_in_a_row() != EMPTY) or \
            (self.board.get_captures(BLACK) >= 10) or \
                (self.board.get_captures(WHITE) >= 10):
            self.respond("")
            return
        legal_moves = self.board.get_empty_points()
        gtp_moves: List[str] = []
        for move in legal_moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def play_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            if board_color not in ['b', 'w', 'e']:
                self.respond('illegal move: "{} {}" wrong color'.format(
                    board_color, board_move))
                return
            coord = move_to_coord(args[1], self.board.size)
            move = coord_to_point(coord[0], coord[1], self.board.size)

            color = color_to_int(board_color)
            CUR = opponent(color)
            if not self.board.play_move(move, color):
                # self.respond("Illegal Move: {}".format(board_move))
                self.respond('illegal move: "{} {}" occupied'.format(
                    board_color, board_move))
                return
            else:
                # self.board.try_captures(coord, color)
                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            if len(args) > 2 and args[2] == 'print_move':
                move_as_string = format_point(coord)
                self.respond(move_as_string.lower())
            else:
                self.respond()
        except Exception as e:
            self.respond('illegal move: "{} {}" {}'.format(
                args[0], args[1], str(e)))
        return

    def gogui_rules_captured_count_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond(str(self.board.get_captures(WHITE)) +
                     ' '+str(self.board.get_captures(BLACK)))

    """
    ==========================================================================
    Assignment 2 - game-specific commands you have to implement or modify
    ==========================================================================
    """
    def timer_countdown(self):
        if not self.solve_value:
            self.board = self.board_copy
            rng = np.random.default_rng()
            choice = rng.choice(len(self.legal_moves))
            move = self.legal_moves[choice]
            move_coord = point_to_coord(move, self.board.size)
            move_as_string = format_point(move_coord)
            self.timer_thread.cancel()
            self.play_cmd([self.board_color, move_as_string, 'print_move'])

        else:
            # print("not random")
            self.timer_thread.cancel()
            self.play_cmd([self.board_color, self.solve_value, 'print_move'])
        
        self.thread_active = False
        self.start_connection()
        return


    def genmove_cmd(self, args: List[str]) -> None:
        """ 
        Modify this function for Assignment 2.
        """
        self.solve_value = False
        # Timer implementation
        self.timer_thread = threading.Timer(self.time, self.timer_countdown)
        
        self.board_color = args[0].lower()
        # color = color_to_int(self.board_color)
        self.legal_moves = self.board.get_empty_points()
        self.board_copy = self.board.copy()
        
        self.timer_thread.start()
        self.thread_active = True
        self.solve_cmd(args)
        self.thread_active = False
        # self.board = board
        return


    def timelimit_cmd(self, args: List[str]) -> None:
        """ Implement this function for Assignment 2 """
        time = int(args[0])
        if time < 1 or time > 100:
            self.respond(
                "Time limit should be in the range 1 <= seconds <= 100")
            return

        else:
            self.time = time
            self.respond()

    def ninuki_legal_moves_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        if (self.board.detect_five_in_a_row() != EMPTY) or \
            (self.board.get_captures(BLACK) >= 10) or \
                (self.board.get_captures(WHITE) >= 10):
            self.respond("")
            return
        legal_moves = self.board.get_empty_points()
        gtp_moves: List[str] = []
        for move in legal_moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = sorted(gtp_moves)
        return (sorted_moves)

    # def order_mm_moves(self, turn):
    #     sorted_moves = []
    #     self.ninuki_legal_moves_cmd([turn])
    #     bc = self.board.get_captures(BLACK)
    #     wc = self.board.get_captures(WHITE)
    #     saved_board = self.board.copy()
    #     for m in self.ninuki_legal_moves_cmd([turn]):
    #         self.play_move([turn, m])
    #         if self.endOfGame():
    #             sorted_moves.insert(0, m)
    #         else:
    #             sorted_moves.append(m)
    #         self.undo_move(saved_board, bc, wc)
    #     return sorted_moves

    def order_mm_moves(self, turn):
        sorted_moves = []
        self.ninuki_legal_moves_cmd([turn])
        bc = self.board.get_captures(BLACK)
        wc = self.board.get_captures(WHITE)
        saved_board = self.board.board.copy()
        for m in self.ninuki_legal_moves_cmd([turn]):
            self.play_move([turn, m])
            if self.endOfGame():
                sorted_moves.insert(0, m)
            else:
                sorted_moves.append(m)
            self.play_move(["e", m])
        return sorted_moves

    def solved_timer(self):
        if not self.solve_value:
            self.respond("unknown")
            self.board = self.board_copy2
        self.timer_thread_1.cancel()
        self.start_connection()
        return

    def solve_cmd(self, args: List[str]) -> None:
        """ Implement this function for Assignment 2 """
        self.start_time = time.time()

        # self.transposition_table.clear()  # Clear the transposition table for a new search
        self.board_copy2 = self.board.copy()
        
        self.timer_thread_1 = None
        if not self.thread_active:
            self.timer_thread_1 = threading.Timer(self.time, self.solved_timer)
            self.timer_thread_1.start()
        self.solve_value = False

        best = -inf
        if self.board.current_player == BLACK:
            turn = "b"
        else:
            turn = "w"
        alpha = -inf
        beta = inf

        # saved_board = self.board.copy()
        board_hash = self.board2d_hash()

        for m in self.order_mm_moves(turn):
            self.play_move([turn,m])
            if self.endOfGame():
                self.play_move(["e", m])
                if not args:    # if call not from genmove
                    self.respond(turn)
                self.solve_value = m.lower()
                return 

            if self.board.current_player == BLACK:
                turn = "b"
            else:
                turn = "w"
            value = self.minimaxAND(alpha, beta)
            if value > best:
                best = value
                best_move = m

            alpha = max(alpha,best)
            self.play_move(["e", m])

            if beta <= alpha:
                break
            if time.time() - self.start_time > self.time - 0.2:
                return best
        self.board = self.board_copy2
        if best > 0:
            if self.board.current_player == BLACK:
                WIN = "b"
            else:
                WIN = "w"

            if not args:      # not called from genmove
                self.respond(WIN + " " + best_move.lower())
            self.solve_value = best_move.lower()
            

        elif best < 0:
            if self.board.current_player == BLACK:
                WIN = "w"
            else:
                WIN = "b"

            if not args:
                self.respond(WIN)
            self.solve_value = best_move.lower()

        else:
            if not args: 
                self.respond("draw " + best_move.lower())
            self.solve_value = best_move.lower()
            
        self.transposition_table[board_hash] = (best, best_move)
        return

    def board2d_hash(self) -> str:
        # board_str = self.board2d()
        # print(board_str)
        # return hashlib.md5(board_str.encode()).hexdigest()
        return str(self.current_hash)

    def update_hash(self, move: GO_POINT, color: GO_COLOR):
        row, col = point_to_coord(move, self.board.size)
        index = row * self.board.size + col
        if color == BLACK:
            self.current_hash ^= self.zobrist_hash_table[row][0][index]
        elif color == WHITE:
            self.current_hash ^= self.zobrist_hash_table[row][1][index]


    def endOfGame(self):

        if self.board.detect_five_in_a_row() != EMPTY:

            return True
        if self.board.get_captures(BLACK) >= 10 or self.board.get_captures(WHITE) >= 10:

            return True
        if self.board.get_empty_points().size == 0:

            return True
        return False

    def staticallyEvaluate(self):
        opp = opponent(self.board.current_player)
        CUR = self.board.current_player
        result1 = self.board.detect_five_in_a_row()
        result2 = EMPTY
        if self.board.get_captures(CUR) >= 10:
            result2 = CUR
        elif self.board.get_captures(opp) >= 10:
            result2 = opp
        points = 0
        if (result1 == CUR):
            return self.board.get_empty_points().size*1
        elif (result2 == CUR):
            return self.board.get_captures(CUR)*100
        elif (result1 == opp):
            return self.board.get_empty_points().size*-1
        elif (result2 == opp):
            return self.board.get_captures(opp)*-100
        else:
            # If the game is still ongoing and not a clear win or draw, return a value
            return 0  # You can adjust this value as needed

    def play_move(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            if board_color not in ['b', 'w', "e"]:
                self.respond('illegal move: "{} {}" wrong color'.format(
                    board_color, board_move))
                return

            coord = move_to_coord(args[1], self.board.size)
            move = coord_to_point(coord[0], coord[1], self.board.size)

            color = color_to_int(board_color)
            self.update_hash(move, color)

            if not self.board.play_move(move, color):
                # self.respond("Illegal Move: {}".format(board_move))
                self.respond('illegal move: "{} {}" occupied'.format(
                    board_color, board_move))
                return
            else:

                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            
            if len(args) > 2 and args[2] == 'print_move':
                move_as_string = format_point(coord)
                self.respond(move_as_string.lower())
    
        except Exception as e:
            self.respond('illegal move: "{} {}" {}'.format(

                args[0], args[1], str(e)))

    def undo_move(self, saved_board, black_captures, white_captures):
        """
        Undo the move by restoring the board and capture counts to their previous state.
        """
        self.board = saved_board.copy()
        self.board.black_captures = black_captures
        self.board.white_captures = white_captures


    # def undo_move(self, saved_board, black_captures, white_captures):
    #     """
    #     Undo the move by restoring the board and capture counts to their previous state.
    #     """
    #     self.board = saved_board.copy()
    #     self.board.black_captures = black_captures
    #     self.board.white_captures = white_captures
            

    def minimaxOR(self, alpha=-inf, beta=inf):
        board_hash = self.board2d_hash()
        best_move = None
        # print(board_hash)
        if board_hash in self.transposition_table:
            # print("transposition found OR")
            cached_score, best_move = self.transposition_table[board_hash]
            # print(cached_score)
            # print("OR cache score" + str(cached_score)+"inserted")

            return cached_score
        if self.endOfGame():
            return self.staticallyEvaluate()

        best = -inf
        if self.board.current_player == BLACK:
            turn = "b"
        else:
            turn = "w"
        # print(turn)
        # print(self.ninuki_legal_moves_cmd([turn]))
        for m in self.ninuki_legal_moves_cmd([turn]):
            self.play_move([turn, m])
            value = self.minimaxAND(alpha, beta)
            # best = max(best, value)

            if value > best:
                best = value
                best_move = m
            # Update alpha
            alpha = max(alpha, best)
            self.play_move(["e", m])

            # Prune if beta <= alpha
            if beta <= alpha:
                break
            if time.time() - self.start_time > self.time - 0.2:
                return best

        # Note: No best move for OR nodes
        self.transposition_table[board_hash] = (best, best_move)
        # print(self.transposition_table[board_hash])
        return best

    def minimaxAND(self, alpha=-inf, beta=inf):


        board_hash = self.board2d_hash()
        best_move = None
        # print(board_hash)
        if board_hash in self.transposition_table:
            cached_score, best_move = self.transposition_table[board_hash]
            # print("AND cache score" + str(cached_score)+"inserted")
            return cached_score


        if self.endOfGame():
            return self.staticallyEvaluate()

        best = inf

        if self.board.current_player == BLACK:
            turn = "b"
        else:
            turn = "w"
        # print(turn)
        # print(self.ninuki_legal_moves_cmd([turn]))
        for m in self.ninuki_legal_moves_cmd([turn]):

            self.play_move([turn, m])

            value = self.minimaxOR(alpha, beta)

            # best = min(best, value)
            if value < best:
                best = value
                best_move = m

            # Update beta
            beta = min(beta, best)
            self.play_move(["e", m])
            # print(self.ninuki_legal_moves_cmd([turn]))

            # Prune if beta <= alpha
            if beta <= alpha:
                break
            if time.time() - self.start_time > self.time - 0.2:
                return best

        self.transposition_table[board_hash] = (best, best_move)
        # print(self.transposition_table[board_hash])
        return best

    """
    ==========================================================================
    Assignment 2 - game-specific commands end here
    ==========================================================================
    """


def point_to_coord(point: GO_POINT, boardsize: int) -> Tuple[int, int]:
    """
    Transform point given as board array index 
    to (row, col) coordinate representation.
    Special case: PASS is transformed to (PASS,PASS)
    """
    if point == PASS:
        return (PASS, PASS)
    else:
        NS = boardsize + 1
        return divmod(point, NS)


def format_point(move: Tuple[int, int]) -> str:
    """
    Return move coordinates as a string such as 'A1', or 'PASS'.
    """
    assert MAXSIZE <= 25
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    if move[0] == PASS:
        return "PASS"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        raise ValueError
    return column_letters[col - 1] + str(row)


def move_to_coord(point_str: str, board_size: int) -> Tuple[int, int]:
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return (PASS, PASS)
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("wrong coordinate")
    if not (col <= board_size and row <= board_size):
        raise ValueError("wrong coordinate")
    return row, col


def color_to_int(c: str) -> int:
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}
    return color_to_int[c]
