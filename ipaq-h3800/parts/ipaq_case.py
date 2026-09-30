from nurb import *


@assembly
def ipaq_case(exploded=0.0):
    """Front, asymmetric back and PCB in their shared fastener datum.

    exploded: Separate the shells along Z for inspecting the board and mating lip.
    """
    gap = float(exploded) / 2
    front = component(Pos(0, 0, gap) * use('front'), 'Front')
    back = component(Pos(0, 0, -gap) * use('back'), 'Back')
    board = component(use('pcb'), 'PCB')
    front.color = Color(0.70, 0.73, 0.76)
    back.color = Color(0.49, 0.54, 0.59)
    board.color = Color(0.13, 0.40, 0.25)
    clearance(front, back)
    clearance(front, board)
    clearance(back, board)
    return front, back, board
