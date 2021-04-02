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

    @abstractmethod
    async def get_name(self):
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
            await self.client.send_message(self.peer, msg)

        elif isinstance(gameevent, evt.BeginGame):
            self.cards = gameevent.cards
            msg = (
                f"Game {self.game} is beginning!\n\n"
                f"You have cards:\n{self.format_cards()}"
            )

            await self.client.send_message(self.peer, msg)

        elif isinstance(gameevent, evt.MissionChange):
            mission = gameevent.mission
            msg = (
                "The game mission has been changed!\n\n"
                f"**Mission {mission.mission_id}:** {mission.description}"
            )
            await self.client.send_message(self.peer, msg)

        elif isinstance(gameevent, evt.TaskAssigned):
            task = gameevent.task
            player = gameevent.player
            name = await player.get_name()
            msg = f"{name} assigned task {task}"
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

        def add_hand(cards):
            for i in range(1, len(cards)):
                if cards[0].suite != cards[i].suite:
                    return [cards[:i]] + add_hand(cards[i:])
            return [cards]

        cards = sorted(self.cards)
        return "\n".join(
            "- " + " ".join(str(c.value) for c in suite) + suite[0].suite.icon
            for suite in add_hand(cards)
        )
