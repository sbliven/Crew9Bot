import logging
from collections import deque
from typing import Iterable, List

from crew9bot import events as evt
from crew9bot.cards import Card
from crew9bot.player import Player


class MockPlayer(Player):
    """Mock Player with pre-defined moves"""

    notices: List[evt.Event]

    def __init__(self, name: str, moves: Iterable[Card] = []) -> None:
        self.name = name
        self.notices = []

    async def notify(self, gameevent: evt.Event) -> None:
        "Notify player of game events that do not need a response"
        self.notices.append(gameevent)
        logging.debug("Player {self.name} recieved {gameevent}")

    async def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name
