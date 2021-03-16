from dataclasses import dataclass
from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import Dict, List, Set, TYPE_CHECKING, Union
import random
import math
import asyncio
import functools
from io import StringIO
import base64

if TYPE_CHECKING:
    from telethon.types import PeerUser  # type: ignore


class Suite(Enum):
    Rocket = "🚀"
    Blue = "🌀"
    Pink = "🌸"
    Green = "☘️"
    Yellow = "⭐️"

    def __init__(self, icon):
        self.icon = icon


@functools.total_ordering
@dataclass
class Card:
    value: int
    suite: Suite

    def takes(self, other: "Card", lead: Suite):
        """True if one card can "take" the second, given a particular suite for the trick."""
        if self.suite == other.suite:
            return self.value > other.value
        if self.suite is Suite.Rocket:
            return True
        if other.suite is Suite.Rocket:
            return False
        if self.suite == lead:
            return True
        # No ordering between non-lead cards
        return False

    def __str__(self):
        return f"{self.value}{self.suite.icon}"

    def __lt__(self, other):
        if isinstance(other, Card):
            return (self.suite, self.value) < (other.suite, other.value)
        raise NotImplementedError


class Player(ABC):
    """Abstract Player interface"""

    @abstractmethod
    async def notify(self, gameevent, **kwargs):
        "Notify player of game events that do not need a response"
        ...

    @abstractmethod
    async def get_move(self, previous_moves: List[Card]) -> Card:
        ...


class TelegraphPlayer(Player):
    peer: "PeerUser"
    cards: Set[Card]

    def __init__(self, peer: "PeerUser", client):
        "Don't call this; use get_player instead"
        self.peer = peer
        self.client = client

    async def notify(self, gameevent, **kwargs):
        await self.client.send_message(self.peer, gameevent)

    async def get_move(self, previous_moves: List[Card]) -> Card:
        ...

    async def get_name(self):
        if not hasattr(self, "_name"):
            you = await self.client.get_entity(self.peer)
            self._name = you.first_name
        return self._name


_players: Dict[int, TelegraphPlayer] = {}


def get_player(peer: "PeerUser", client):
    if peer.user_id not in _players:
        _players[peer.user_id] = TelegraphPlayer(peer, client)
    return _players[peer.user_id]


class Game:
    game_id: int
    players: List[Player]
    commander: int  # index of commander
    hands: Dict[Player, Set[Card]]

    def __init__(self):
        self.game_id = random.getrandbits(5 * 8)  # multiple of 5 for base32 encoding
        _games[self.game_id] = self
        self.players = []

    def get_game_id(self) -> str:
        return base64.b32encode(
            self.game_id.to_bytes(math.ceil(self.game_id.bit_length() / 8), "big")
        ).decode()

    @classmethod
    def decode_game_id(cls, id: str) -> int:
        b = base64.b32decode(id.encode())
        return int.from_bytes(b, "big")

    async def join(self, player):
        tasks = [
            asyncio.create_task(
                p.notify(
                    "Player Joined",
                    player=player,
                )
            )
            for i, p in enumerate(self.players)
        ]
        tasks.append(asyncio.create_task(player.notify("You Joined", game=self)))

        self.players.append(player)

        await asyncio.wait(tasks)

    async def start(self):
        # deal cards
        self.deal()
        tasks = [
            asyncio.create_task(
                player.notify(
                    "Game started",
                    hand=self.hands[player],
                    commander=i == self.commander,
                )
            )
            for i, player in enumerate(self.players)
        ]
        asyncio.wait(tasks)

    @classmethod
    def shuffle(kls) -> List[Card]:
        cards = [Card(i, suite) for i in range(1, 10) for suite in Suite]
        random.shuffle(cards)
        return cards

    def deal(self):
        cards = self.shuffle()
        handlen = len(cards) / len(self.players)
        self.hands = {
            player: cards[math.ceil(handlen * i) : math.ceil(handlen * (i + 1))]
            for i, player in enumerate(self.players)
        }
        commander_card = Card(4, Suite.Rocket)
        for i in range(len(self.players)):
            if commander_card in self.hands[self.players[i]]:
                self.commander = i
                break

    async def get_description(self):
        s = StringIO()
        s.write(f"Game {self.get_game_id()} with ")
        names = await asyncio.gather(*(p.get_name() for p in self.players))
        if len(names) == 0:
            s.write("no players")
        elif len(names) == 1:
            s.write(names[0])
        else:
            s.write(", ".join(names[:-1]))
            s.write(" and ")
            s.write(names[-1])
        return s.getvalue()


_games: Dict[int, Game] = {}


def get_game(game_id: Union[int,str]):
    if isinstance(game_id, str):
        game_id = Game.decode_game_id(game_id)
    return _games[game_id]


def get_games():
    return _games.values()