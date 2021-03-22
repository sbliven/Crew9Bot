import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Set

from . import events as evt

if TYPE_CHECKING:
    from telethon.types import Peer  # type: ignore

    from .cards import Card
    from .game import Game


class Player(ABC):
    """Abstract Player interface"""

    @abstractmethod
    async def notify(self, gameevent: evt.Event, **kwargs):
        "Notify player of game events that do not need a response"
        ...

    @abstractmethod
    async def get_move(self, previous_moves: List["Card"]) -> "Card":
        ...


class TelegramPlayer(Player):
    peer: "Peer"
    cards: Set["Card"]
    game: Optional["Game"]

    def __init__(self, peer: "Peer", client):
        "Don't call this; use get_player instead"
        self.peer = peer
        self.client = client

    async def notify(self, gameevent: evt.Event, **kwargs):
        if isinstance(gameevent, evt.JoinGame):
            self.game = gameevent.game
            name = await self.get_name()

            msg = (
                "You joined a new game! Forward the following invitation to your "
                "friends:"
            )
            await self.client.send_message(self.peer, msg)

            msg = (
                f"{name} wants to play Crew9Bot with you! "
                f"Join {self.get_game_link()} now!"
            )
            logging.info(f"Sending '{msg}'")
            await self.client.send_message(self.peer, msg)

        elif isinstance(gameevent, evt.BeginGame):
            self.cards = gameevent.cards
            msg = (
                f"Game {self.game} is beginning!\n\n"
                f"You have cards:\n{self.format_cards()}"
            )

            await self.client.send_message(self.peer, msg)

        else:
            await self.client.send_message(self.peer, gameevent.message)

    def get_game_link(self):
        "Markdown code for the game link"
        if self.game:
            return f"[{self.game.get_game_id()}]({self.game.get_game_url()})"
        return None

    async def get_move(self, previous_moves: List["Card"]) -> "Card":
        ...

    async def get_name(self):
        if not hasattr(self, "_name"):
            you = await self.client.get_entity(self.peer)
            if hasattr(you, "first_name"):
                self._name = you.first_name
            else:
                self._name = you.title
        return self._name

    def format_cards(self):
        "Markdown description of the players cards"
        return " ".join(str(c) for c in sorted(self.cards))
