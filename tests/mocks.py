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

    def __init__(self, name, moves: Iterable[Card] = []):
        self.name = name
        self.notices = []
        self.moves = deque(moves)

    async def notify(self, gameevent: evt.Event, **kwargs):
        "Notify player of game events that do not need a response"
        self.notices.append(gameevent)
        logging.info("Player {self.name} recieved {gameevent}")

    async def get_move(self, previous_moves: Iterable["Card"]) -> "Card":
        return self.moves.popleft()

    async def get_name(self):
        return self.name

    def append_moves(self, *moves: Card):
        self.moves.extend(moves)