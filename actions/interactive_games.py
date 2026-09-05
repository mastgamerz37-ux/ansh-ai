"""
actions/interactive_games.py — Interactive Mini-Games & Widgets (Tic Tac Toe & Live Quiz) for ANSH
"""
from __future__ import annotations

import json
import random
from typing import Dict, Any, Optional

_TIC_TAC_TOE_STATE = {
    "board": [" "] * 9,
    "active": False,
    "user_symbol": "X",
    "ai_symbol": "O"
}

def _render_board(board: list) -> str:
    lines = [
        f" {board[0]} | {board[1]} | {board[2]} ",
        "---+---+---",
        f" {board[3]} | {board[4]} | {board[5]} ",
        "---+---+---",
        f" {board[6]} | {board[7]} | {board[8]} "
    ]
    return "\n".join(lines)

def _check_winner(board: list) -> Optional[str]:
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8), # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8), # cols
        (0, 4, 8), (2, 4, 6)             # diagonals
    ]
    for a, b, c in wins:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    if " " not in board:
        return "DRAW"
    return None

def tic_tac_toe(move: Optional[int] = None, reset: bool = False) -> str:
    global _TIC_TAC_TOE_STATE
    if reset or not _TIC_TAC_TOE_STATE["active"]:
        _TIC_TAC_TOE_STATE["board"] = [" "] * 9
        _TIC_TAC_TOE_STATE["active"] = True
        return (
            "🎮 New Tic Tac Toe Game Started!\n"
            "You are X, I am O. Choose a position (1 to 9):\n\n"
            " 1 | 2 | 3 \n"
            "---+---+---\n"
            " 4 | 5 | 6 \n"
            "---+---+---\n"
            " 7 | 8 | 9 \n\n"
            "Your turn! Where would you like to place your X?"
        )

    board = _TIC_TAC_TOE_STATE["board"]

    # User move
    if move is not None:
        idx = move - 1 if 1 <= move <= 9 else -1
        if idx == -1 or board[idx] != " ":
            return f"Invalid move! Position {move} is already taken or out of range (1-9).\n\n" + _render_board(board)
        board[idx] = _TIC_TAC_TOE_STATE["user_symbol"]

    # Check if user won
    winner = _check_winner(board)
    if winner:
        _TIC_TAC_TOE_STATE["active"] = False
        if winner == "X":
            return f"🎉 Congratulations! You won!\n\n" + _render_board(board)
        elif winner == "DRAW":
            return f"🤝 It's a draw!\n\n" + _render_board(board)

    # AI move
    available = [i for i, v in enumerate(board) if v == " "]
    if available:
        # Simple AI: win or block if possible, else random
        ai_choice = None
        for cand in available:
            board[cand] = "O"
            if _check_winner(board) == "O":
                ai_choice = cand
                break
            board[cand] = " "
        
        if ai_choice is None:
            for cand in available:
                board[cand] = "X"
                if _check_winner(board) == "X":
                    ai_choice = cand
                    board[cand] = " "
                    break
                board[cand] = " "

        if ai_choice is None:
            # Take center or random
            ai_choice = 4 if 4 in available else random.choice(available)

        board[ai_choice] = "O"
        ai_pos = ai_choice + 1

        # Check if AI won
        winner = _check_winner(board)
        if winner:
            _TIC_TAC_TOE_STATE["active"] = False
            if winner == "O":
                return f"🤖 I placed my O at position {ai_pos} and won the game!\n\n" + _render_board(board)
            elif winner == "DRAW":
                return f"🤝 I played at {ai_pos}. It's a draw!\n\n" + _render_board(board)

        return f"I placed my O at position {ai_pos}.\n\n" + _render_board(board) + "\n\nYour turn! Pick a number (1-9):"
    
    _TIC_TAC_TOE_STATE["active"] = False
    return "Game finished.\n\n" + _render_board(board)


def live_quiz(topic: str = "General Tech & AI", difficulty: str = "medium") -> str:
    """
    Generate an engaging interactive trivia quiz question.
    """
    try:
        from core.task_llm import call_task_llm
        prompt = f"""Generate 1 exciting trivia question on the topic: "{topic}" (Difficulty: {difficulty}).
Include 4 multiple-choice options (A, B, C, D) and mention which one is correct.
Format clearly with the question, options, and a spoiler tag for the answer."""
        return call_task_llm(prompt=prompt).strip()
    except Exception as e:
        return f"Quiz Generator Error: {e}"


def interactive_games_action(
    parameters: dict = None,
    player=None,
    speak=None
) -> str:
    """
    parameters:
        game   : 'tic_tac_toe' | 'quiz'
        move   : int 1-9 for tic tac toe
        reset  : bool to reset game
        topic  : topic for quiz
    """
    params = parameters or {}
    game = params.get("game", "tic_tac_toe").lower().strip()

    if "quiz" in game or "trivia" in game:
        topic = params.get("topic", "General Tech & Science")
        return live_quiz(topic=topic)
    else:
        move = params.get("move")
        if move is not None:
            try:
                move = int(move)
            except ValueError:
                move = None
        reset = bool(params.get("reset", False))
        return tic_tac_toe(move=move, reset=reset)
