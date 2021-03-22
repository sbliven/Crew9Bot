import asyncio
import base64
import math
import random
from io import StringIO
from typing import Dict, List, Set, Union

from asyncio.exceptions import InvalidStateError

from . import events as evt
from .cards import Card, Suite
from .player import Player
from .missions import Mission, all_missions


class Game:
    game_id: int
    players: List[Player]
    hands: Dict[Player, Set[Card]]
    mission: Mission
    started: bool

    def __init__(self):
        """Create a new game. Should normally be instantiated through the GameMaster"""
        self.game_id = self.random_game_id()  # multiple of 5 for base32 encoding
        self.players = []
        self.mission = all_missions[1]
        self.started = False

    def get_game_id(self) -> str:
        "Get the human-readable game id"
        return self.encode_game_id(self.game_id)

    @classmethod
    def random_game_id(cls) -> int:
        return random.getrandbits(5 * 8)

    @classmethod
    def encode_game_id(cls, id: int) -> str:
        return base64.b32encode(
            id.to_bytes(5, "big")
        ).decode()

    @classmethod
    def decode_game_id(cls, id: str) -> int:
        "Parse a human-readable game id back to a numeric hash"
        b = base64.b32decode(id.encode())
        return int.from_bytes(b, "big")

    def __str__(self):
        return self.get_game_id()

    async def join(self, player):
        tasks = [
            asyncio.create_task(p.notify(evt.PlayerJoined(player)))
            for i, p in enumerate(self.players)
        ]
        tasks.append(asyncio.create_task(player.notify(evt.JoinGame(self))))

        self.players.append(player)

        await asyncio.wait(tasks)

    async def begin(self):
        self.started = True
        # determine order
        self.players = random.shuffle(self.players)
        # deal cards
        self.deal()


        await asyncio.wait([
            asyncio.create_task(
                player.notify(evt.BeginGame(self.hands[player]))
            )
            for player in self.players
        ])

        # choose tasks
        tasks = self.make_tasks()
        # TODO bidding round; assign randomly for now

    @classmethod
    def shuffle(kls) -> List[Card]:
        cards = [
            Card(i, suite)
            for suite in Suite
            for i in range(1, 5 if suite is Suite.Rocket else 10)
        ]
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

    def get_game_url(self):
        return f"https://t.me/Crew9Bot?start={self.get_game_id()}"

    async def set_mission(self, mission: Union[int, Mission]):
        if isinstance(mission, int):
            mission = all_missions[mission]

        if self.started:
            raise InvalidStateError("Game already started")

        await asyncio.wait([
            asyncio.create_task(
                player.notify(evt.MissionChange(mission))
            )
            for player in self.players
        ])
