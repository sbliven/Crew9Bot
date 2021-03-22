from dataclasses import dataclass
from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from .game import Card, Game, Player


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


class BeginGame(Event):
    "Notifies the player that they have joined a game"
    cards: Set["Card"]
    commander: bool

    def __init__(self, cards, commander):
        super().__init__("Game started")
        self.cards = cards
        self.commander = commander
