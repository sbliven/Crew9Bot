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
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from . import events as evt
from .cards import DECK_SIZE, Card, Suite, shuffled_deck
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

    @property
    def n_players(self) -> int:
        return len(self.players)

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

        # determine order of play
        if len(self.history) == 0:
            random.shuffle(self.players)

        # deal cards
        await self.deal()

        # choose tasks
        await self.assign_tasks()

        # Start hand
        self.next_player = self.commander

        await self.communicate()

        await self.start_turn()

    async def deal(self) -> None:
        if self.state != "waiting":
            raise InvalidStateError(f"Cannot deal. State: {self.state}")

        self.state = "deal"
        cards = shuffled_deck()
        handlen = len(cards) / self.n_players
        # TODO track dealer or randomize?
        self.hands = [
            sorted(cards[math.ceil(handlen * i) : math.ceil(handlen * (i + 1))])
            for i in range(self.n_players)
        ]
        commander_card = Card(4, Suite.Rocket)
        for i in range(self.n_players):
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
        if self.state != "deal":
            raise InvalidStateError(f"Cannot assign tasks. State: {self.state}")

        self.state = "bid"
        await self.mission.bid(self.players, self.commander)

    async def communicate(self) -> None:
        if self.state not in ("bid", "turn"):
            raise InvalidStateError(f"Cannot start communication. State: {self.state}")

        self.state = "communicate"

        handnum = len(self.played_cards[0])

        remaining: List[Iterable[Card]] = [
            set(self.hands[p]) - set(self.played_cards[p])
            for p in range(self.n_players)
        ]
        await self.mission.communicate(self.players, remaining, handnum)

    async def start_turn(self) -> None:
        "Notify the next player it is their turn"
        if self.state not in ("communicate", "turn"):
            raise InvalidStateError(f"Cannot start turn. State: {self.state}")

        self.state = f"turn"

        valid = self.hands[self.next_player]

        await self.players[self.next_player].notify(evt.YourTurn(valid))

    def _current_hand(self) -> Tuple[Optional[List[Optional[Card]]], int]:
        """Get cards from the most recent (possibly partial) hand

        Returns:
        - Most recent hand, with None for any missing players
        - index of the player that lead the hand


        """
        # [B]
        # [] next_player
        # []
        # [A] lead
        handnum = len(self.played_cards[self.next_player])

        # lead is index of the first player
        for lead in permute_range(self.next_player + 1, self.n_players):
            if len(self.played_cards[lead]) == handnum + 1:
                break
        if lead == self.next_player:  # complete hand
            handnum -= 1
        if handnum < 0:
            return None, lead
        return [
            self.played_cards[i][handnum]
            if len(self.played_cards[i]) == handnum + 1
            else None
            for i in range(self.n_players)
        ], lead

    def _get_valid(self, player: int, lead: Optional["Suite"] = None) -> List[Card]:
        "Get all valid cards for the given player"
        if lead is not None:
            return [card for card in self.hands[player] if card.suite == lead]
        return self.hands[player]

    def _current_winner(self) -> int:
        "Index of the player currently winning the hand"
        hand, lead = self._current_hand()
        if hand is None:
            raise InvalidStateError("No cards played")
        lead_card = hand[lead]
        assert lead_card is not None
        lead_suite = lead_card.suite
        winner = lead
        winning_card: Card = lead_card

        for p in permute_range(lead + 1, self.n_players):
            card = hand[p]
            if p == self.next_player or card is None:
                break
            if card.takes(winning_card, lead_suite):
                winner = p
                winning_card = card

        return winner

    async def play(self, player: Player, card: Card) -> None:
        if self.state != "turn":
            raise InvalidStateError(f"Cannot play turn. State: {self.state}")

        if player is not self.players[self.next_player]:
            raise InvalidStateError(
                f"Out of turn! Next player is {self.players[self.next_player]}"
            )

        # Verify card is valid
        hand, lead_player = self._current_hand()

        if hand:
            lead_card = hand[lead_player]
            assert lead_card is not None
            lead_suit = lead_card.suite
        else:
            lead_suit = None

        valid = self._get_valid(self.next_player, lead_suit)
        if not card in valid:
            raise ValueError("Card not a valid play")

        # Accept play
        self.played_cards[self.next_player].append(card)

        await asyncio.wait(
            [
                asyncio.create_task(
                    self.players[i].notify(evt.CardPlayed(card, player))
                )
                for i in range(self.n_players)
                if i != player
            ]
        )

        # Check if hand finished
        if hand is not None and lead_player == self.next_player:
            winner = self._current_winner()
            self.next_player = winner

            await asyncio.wait(
                [
                    asyncio.create_task(
                        self.players[i].notify(evt.HandWon(self.players[winner]))
                    )
                    for i in range(self.n_players)
                ]
            )

            status = self.mission.get_status(self.played_cards)

            if status == "win":
                await self.win()
                return
            elif status == "lose":
                await self.lose()
                return
            assert status == "ongoing"

            # Check if no more hands to play
            if DECK_SIZE - len(self.played_cards[0]) * self.n_players < self.n_players:
                await self.lose()
                return
        else:
            self.next_player = (self.next_player + 1) % self.n_players

        await self.start_turn()

    async def win(self) -> None:
        await asyncio.wait(
            [
                asyncio.create_task(self.players[i].notify(evt.GameOver(True)))
                for i in range(self.n_players)
            ]
        )

        # TODO increment mission

    async def lose(self) -> None:
        await asyncio.wait(
            [
                asyncio.create_task(self.players[i].notify(evt.GameOver(False)))
                for i in range(self.n_players)
            ]
        )

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
