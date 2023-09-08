"""Tracks a Crew9 game

Games progress through the following states:

1. *waiting*. Players can join. Mission can be set. Transitions on begin()
2. *deal*. Assigns hands. Transitions immediately
3. *bid*. Mission-specific task assignment.
4. *communicate*. Communicate, if allowed by mission
5. *turn[X]*. Waiting for player X to play. Transition after all players play
6. *check_hand*. Check if mission is fullfilled. If not, start the next hand with turn[X]
7. *end*. End of the round. Update the mission, then transition to waiting.

"""

import asyncio
import base64
import math
import random
from asyncio.exceptions import InvalidStateError
from functools import partial
from io import StringIO
from typing import Dict, List, Optional, Set, Tuple, Union

from . import events as evt
from .cards import Card, Suite, shuffled_deck
from .missions import ImpossibleMission, Mission, create_mission
from .player import Player
from .util import permute_range


class Game:
    #: binary game ID
    game_id: int  # TODO should be bytes
    #: Players by order of play
    players: List[Player]
    #: Commander for this game
    commander: int
    #: Sorted list of remaining cards for each player
    hands: List[List[Card]]
    #: Current mission
    mission: Mission
    #: Mission history. Tuple of mission numbers and if it was won
    history: List[Tuple[int, bool]]
    # Current state
    state: str
    #: next player
    next_player: int
    #: History of all cards played this round.
    #: Indexed [player][hand number]
    played_cards: List[List[Card]]

    def __init__(self) -> None:
        """Create a new game. Should normally be instantiated through the GameMaster"""
        self.game_id = self.random_game_id()  # multiple of 5 for base32 encoding
        self.players = []
        self.commander = 0
        self.hands = []
        self.mission = ImpossibleMission()
        self.history = []
        self.state = "waiting"
        self.next_player = self.commander
        self.played_cards = []

    def get_game_id(self) -> str:
        "Get the human-readable game id"
        return self.encode_game_id(self.game_id)

    @classmethod
    def random_game_id(cls) -> int:
        return random.getrandbits(5 * 8)

    @classmethod
    def encode_game_id(cls, id: int) -> str:
        return base64.b32encode(id.to_bytes(5, "big")).decode()

    @classmethod
    def decode_game_id(cls, id: str) -> int:
        "Parse a human-readable game id back to a numeric hash"
        b = base64.b32decode(id.encode())
        return int.from_bytes(b, "big")

    def __str__(self) -> str:
        return self.get_game_id()

    async def join(self, player: Player) -> None:
        if self.state != "waiting":
            raise InvalidStateError(f"Cannot join game. State: {self.state}")

        tasks = [
            asyncio.create_task(p.notify(evt.PlayerJoined(player)))
            for i, p in enumerate(self.players)
        ]
        tasks.append(asyncio.create_task(player.notify(evt.JoinGame(self))))

        self.players.append(player)
        self.played_cards.append([])

        await asyncio.wait(tasks)

    async def begin(self) -> None:
        if self.state != "waiting":
            raise InvalidStateError(f"Cannot start game. State: {self.state}")

        self.state = "deal"

        # determine order of play
        if len(self.history) == 0:
            random.shuffle(self.players)
        # deal cards
        await self.deal()

        # choose tasks
        await self.assign_tasks()

        # Start hand
        self.next_player = self.commander
        await self.start_turn()

    async def deal(self) -> None:
        cards = shuffled_deck()
        handlen = len(cards) / len(self.players)
        # TODO track dealer or randomize?
        self.hands = [
            sorted(cards[math.ceil(handlen * i) : math.ceil(handlen * (i + 1))])
            for i in range(len(self.players))
        ]
        commander_card = Card(4, Suite.Rocket)
        for i in range(len(self.players)):
            if commander_card in self.hands[i]:
                self.commander = i
                break

        # Notify players of hands
        await asyncio.wait(
            [
                asyncio.create_task(player.notify(evt.CardsDelt(self.hands[i])))
                for i, player in enumerate(self.players)
            ]
        )

    async def assign_tasks(self) -> None:
        await self.mission.bid(self.players, self.commander)

    async def start_turn(self) -> None:
        current_trick: List[Card] = []

        def turn_callback(card: Card) -> None:
            # TODO validate play
            current_trick.append(card)

        player_order = list(permute_range(self.next_player, len(self.players)))

        valid = self.hands[self.next_player]
        try:
            await self.players[self.next_player].notify(
                evt.YourTurn(valid, turn_callback)
            )

            assert len(current_trick) == 1
        except ValueError:
            pass  # TODO

        lead = current_trick[0].suite
        # TODO notify trump?

        for player in player_order[1:]:
            valid = [card for card in self.hands[player] if card.suite == lead]
            if not valid:
                valid = self.hands[player]
            try:
                await self.players[player].notify(evt.YourTurn(valid, turn_callback))

                assert (
                    len(current_trick)
                    == player + 1 + len(self.players) - self.next_player
                )
            except ValueError:
                pass  # TODO

        for i, card in zip(player_order, current_trick):
            self.played_cards[i].append(card)

        assert len(current_trick) == len(self.players)
        assert not any(t is None for t in current_trick)

        # winner = get_winner(current_trick, s)

    async def get_description(self) -> str:
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

    def get_game_url(self) -> str:
        return f"https://t.me/Crew9Bot?start={self.get_game_id()}"

    async def set_mission(self, mission: Union[int, Mission]) -> None:
        if self.state != "waiting":
            raise InvalidStateError(f"Game already started. State {self.state}")
        if isinstance(mission, int):
            self.mission = create_mission(mission, self.players, self.commander)
        else:
            self.mission = mission

        await asyncio.wait(
            [
                asyncio.create_task(player.notify(evt.MissionChange(self.mission)))
                for player in self.players
            ]
        )
