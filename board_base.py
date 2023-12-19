"""
board_base.py
Basic definitions and helper functions for Go board.
This file is imported by board.py.
"""

import numpy as np
import random

"""
Encoding of colors on and off a Go board.
"""
GO_COLOR = int

EMPTY = GO_COLOR(0)
BLACK = GO_COLOR(1)
WHITE = GO_COLOR(2)
BORDER = GO_COLOR(3)


def is_black_white(color: GO_COLOR) -> bool:
    return color == BLACK or color == WHITE

def is_black_white_empty(color: GO_COLOR) -> bool:
    return color == BLACK or color == WHITE or color == EMPTY

def opponent(color: GO_COLOR) -> GO_COLOR:
    return WHITE + BLACK - color

"""
A GO_POINT is a point on a Go board.
It is encoded as a 32-bit integer, using the numpy type.
"""
GO_POINT = np.int32

"""
Encoding of special pass move
"""
PASS: GO_POINT = GO_POINT(-2)

"""
Encoding of "not a real point", used as a marker
"""
NO_POINT: GO_POINT = GO_POINT(-1)

"""
The largest board we allow. 
To support larger boards the coordinate printing in
GtpConnection.format_point needs to be changed.
"""
MAXSIZE: int = 25
DEFAULT_SIZE: int = 5

"""
The number of array elements in a "padded 1D" representation 
of a size x size board.
See the documentation under coord_to_point.
"""
def board_array_size(size: int) -> int:
    return size * size + 3 * (size + 1)

"""
where1d: Helper function for using np.where with 1-d arrays.
The result of np.where is a tuple which contains the indices 
of elements that fulfill the condition.
For 1-d arrays, this is of type Tuple[ndarray].
The [0] indexing is needed to extract the ndarray result from the singleton tuple.
"""
def where1d(condition: np.ndarray) -> np.ndarray:
    return np.where(condition)[0]

def coord_to_point(row: int, col: int, board_size: int) -> GO_POINT:
    """
    Transform two dimensional (row, col) representation to array index.

    Arguments
    ---------
    row, col:
             coordinates of the point, 1-based
             1 <= row, col <= board_size
    
    Map (row, col) coordinates to array index
    Below is an example of numbering points on a 3x3 board.
    Spaces are added for illustration to separate board points 
    from BORDER points.
    There is a one point BORDER between consecutive rows (e.g. point 12).
    
    16   17 18 19   20

    12   13 14 15
    08   09 10 11
    04   05 06 07

    00   01 02 03

    For example, with the mapping of colors to integers above,
    EMPTY = 0, BORDER = 3,
    the empty 3x3 board is encoded like this:

    3  3  3  3  3
    3  0  0  0
    3  0  0  0
    3  0  0  0
    3  3  3  3

    This board is represented by the array
    [3,3,3,3,  3,0,0,0,  3,0,0,0,  3,0,0,0,  3,3,3,3,3]
    """
    assert 1 <= row
    assert row <= board_size
    assert 1 <= col
    assert col <= board_size
    NS = board_size + 1
    return GO_POINT(NS * row + col)

