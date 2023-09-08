import logging
from collections import deque
from typing import Iterable, List

from crew9bot import events as evt
from crew9bot.cards import Card
from crew9bot.player import Player


class MockPlayer(Player):
    """Mock Player with pre-defined moves"""

    moves: deque[Card]
    notices: List[evt.Event]

    def __init__(self, name: str, moves: Iterable[Card] = []) -> None:
        self.name = name
        self.notices = []
        self.moves = deque(moves)

    async def notify(self, gameevent: evt.Event) -> None:
        "Notify player of game events that do not need a response"
        self.notices.append(gameevent)
        logging.info("Player {self.name} recieved {gameevent}")

        if isinstance(gameevent, evt.YourTurn):
            valid_moves = gameevent.valid_moves
            callback = gameevent.callback

            if self.moves:
                move = self.moves.popleft()
            else:
                move = valid_moves[0]
            callback(move)

    async def get_move(self, previous_moves: Iterable["Card"]) -> "Card":
        return self.moves.popleft()

    async def get_name(self) -> str:
        return self.name

    def append_moves(self, *moves: Card) -> None:
        self.moves.extend(moves)
