from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Set

from crew9bot.missions import Mission

if TYPE_CHECKING:
    from .cards import Card
    from .game import Game, Player


@dataclass
class Event:
    message: str

    def __str__(self):
        return self.message


class JoinGame(Event):
    "Notifies the player that they have joined a game"
    game: "Game"

    def __init__(self, game):
        super().__init__(f"You Joined {game}")
        self.game = game


class PlayerJoined(Event):
    "Notifies the player that they have joined a game"
    player: "Player"

    def __init__(self, player):
        super().__init__(f"Player joined {player}")
        self.player = player


class CardsDelt(Event):
    "Notifies the player that they have joined a game & been dealt cards"
    cards: Set["Card"]

    def __init__(self, cards):
        super().__init__("Game started")
        self.cards = cards


class MissionChange(Event):
    mission: Mission

    def __init__(self, mission):
        super().__init__("Mission changed")
        self.mission = mission


class TaskAssigned(Event):
    task: "Card"
    player: "Player"

    def __init__(self, task, player):
        super().__init__("Card assigned")
        self.task = task
        self.player = player


class YourTurn(Event):
    valid_moves: List["Card"]
    callback: Callable[["Card"], None]

    def __init__(self, valid_moves, callback):
        super().__init__("Your turn")
        self.valid_moves = valid_moves
        self.callback = callback
