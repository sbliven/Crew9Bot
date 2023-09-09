import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Set

from . import events as evt

if TYPE_CHECKING:
    from telethon import TelegramClient  # type: ignore
    from telethon.types import Peer  # type: ignore

    from .cards import Card
    from .game import Game


class Player(ABC):
    """Abstract Player interface"""

    @abstractmethod
    async def notify(self, gameevent: evt.Event) -> None:
        "Notify player of game events that do not need a response"
        ...

    @abstractmethod
    async def get_name(self) -> str:
        ...


class TelegramPlayer(Player):
    peer: "Peer"
    client: "TelegramClient"
    cards: Iterable["Card"]
    game: Optional["Game"]

    def __init__(self, peer: "Peer", client: "TelegramClient") -> None:
        "Don't call this; use get_player instead"
        self.peer = peer
        self.client = client
        self.game = None

    async def notify(self, gameevent: evt.Event) -> None:
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

        elif isinstance(gameevent, evt.CardsDelt):
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

        elif isinstance(gameevent, evt.TasksAssigned):
            tasks = gameevent.tasks
            player = gameevent.player
            name = await player.get_name()
            msg = f"{name} assigned tasks {' '.join(map(str,tasks))}"
            await self.client.send_message(self.peer, msg)
        else:
            await self.client.send_message(self.peer, gameevent.message)

    def get_game_link(self) -> Optional[str]:
        "Markdown code for the game link"
        if self.game:
            return f"[{self.game.get_game_id()}]({self.game.get_game_url()})"
        return None

    async def get_name(self) -> str:
        if not hasattr(self, "_name"):
            you = await self.client.get_entity(self.peer)
            if hasattr(you, "first_name"):
                self._name = you.first_name
            else:
                self._name = you.title
        assert isinstance(self._name, str)
        return self._name

    def format_cards(self) -> str:
        "Markdown description of the players cards"

        def add_hand(cards: List[Card]) -> List[List[Card]]:
            for i in range(1, len(cards)):
                if cards[0].suit != cards[i].suit:
                    return [cards[:i]] + add_hand(cards[i:])
            return [cards]

        cards = sorted(self.cards)
        return "\n".join(
            "- " + " ".join(str(c.value) for c in suit) + suit[0].suit.icon
            for suit in add_hand(cards)
        )
