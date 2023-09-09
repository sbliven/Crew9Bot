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
from .cards import DECK_SIZE, Card, Suit, get_winner, shuffled_deck
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
    #: Cache index of player who won each hand (and who leads the next hand)
    hand_winners: List[int]

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
        self.hand_winners = []

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
        commander_card = Card(4, Suit.Rocket)
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

    def _get_valid(self, player: int, lead: Optional["Suit"] = None) -> List[Card]:
        "Get all valid cards for the given player"
        if lead is not None:
            follow_suit = [card for card in self.hands[player] if card.suit == lead]
            if follow_suit:
                return follow_suit
        return self.hands[player]

    @property
    def _handnum(self) -> int:
        "Index of the next hand to be played"
        # return len(self.hand_winners)  # should be equivalent
        return len(self.played_cards[self.next_player])

    def _get_lead(self, handnum: int) -> int:
        "Index of the player who led or will lead the specified hand"
        if handnum == 0:
            return self.commander
        if 0 <= handnum - 1 < len(self.hand_winners):
            return self.hand_winners[handnum - 1]
        raise IndexError("Negative indexing not implemented")

    def _hand_started(self, handnum: int) -> bool:
        "Has anyone played a card for the specified hand?"
        lead = self._get_lead(handnum)
        return 0 <= handnum < len(self.played_cards[lead])

    def _hand_finished(self, handnum: int) -> bool:
        "Have all players played for the specified hand?"
        return 0 <= handnum < len(self.hand_winners)

    def _lead_suit(self, handnum: int) -> Suit:
        "Suit that lead the given hand"
        # raises IndexError unless the hand started
        lead_card = self.played_cards[self._get_lead(handnum)][handnum]
        return lead_card.suit

    def _accept_play(self, card: Card) -> None:
        "Updates played_cards and hand_winners for a new card"
        # This round is finished if the player after the next has played
        handnum = self._handnum
        player = self.next_player
        successor = (self.next_player + 1) % self.n_players
        hand_will_finish = handnum < len(self.played_cards[successor])

        # play the card
        self.played_cards[player].append(card)

        # update hand_winners
        if hand_will_finish:
            hand = [self.played_cards[p][handnum] for p in range(self.n_players)]
            lead_suit = self._lead_suit(handnum)
            winner = get_winner(hand, lead_suit)
            self.hand_winners.append(winner)
            assert len(self.hand_winners) == self._handnum, "Hand_winners out of sync!"

            self.next_player = winner

        else:
            # update next_player
            self.next_player = (self.next_player + 1) % self.n_players

    async def play(self, player: Player, card: Card) -> None:
        if self.state != "turn":
            raise InvalidStateError(f"Cannot play turn. State: {self.state}")

        if player is not self.players[self.next_player]:
            raise InvalidStateError(
                f"Out of turn! Next player is {self.players[self.next_player]}"
            )

        # Verify card is valid
        handnum = self._handnum
        if self._hand_started(handnum):
            lead_suit = self._lead_suit(handnum)
        else:
            lead_suit = None

        valid = self._get_valid(self.next_player, lead_suit)
        if not card in valid:
            raise ValueError("Card not a valid play")

        # Accept play
        self._accept_play(card)

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
        if self._hand_finished(handnum):
            winner = self.hand_winners[handnum]

            await asyncio.wait(
                [
                    asyncio.create_task(
                        self.players[i].notify(evt.HandWon(self.players[winner]))
                    )
                    for i in range(self.n_players)
                ]
            )

            status = self.mission.get_status(self.played_cards, self.hand_winners)

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
