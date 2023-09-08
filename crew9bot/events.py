from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable, List, Set

if TYPE_CHECKING:
    from .cards import Card
    from .game import Game, Player
    from .missions import Mission


@dataclass
class Event:
    message: str

    def __str__(self) -> str:
        return self.message


class JoinGame(Event):
    "Notifies the player that they have joined a game"
    game: "Game"

    def __init__(self, game: "Game") -> None:
        super().__init__(f"You Joined {game}")
        self.game = game


class PlayerJoined(Event):
    "Notifies the player that they have joined a game"
    player: "Player"

    def __init__(self, player: "Player") -> None:
        super().__init__(f"Player joined {player}")
        self.player = player


class CardsDelt(Event):
    "Notifies the player that they have joined a game & been dealt cards"
    cards: Iterable["Card"]

    def __init__(self, cards: Iterable["Card"]) -> None:
        super().__init__("Game started")
        self.cards = cards


class MissionChange(Event):
    mission: "Mission"

    def __init__(self, mission: "Mission") -> None:
        super().__init__("Mission changed")
        self.mission = mission


class TasksAssigned(Event):
    tasks: List["Card"]
    player: "Player"

    def __init__(self, tasks: List["Card"], player: "Player"):
        super().__init__("Tasks assigned")
        self.tasks = tasks
        self.player = player


class YourTurn(Event):
    valid_moves: List["Card"]
    callback: Callable[["Card"], None]

    def __init__(
        self, valid_moves: List["Card"], callback: Callable[["Card"], None]
    ) -> None:
        super().__init__("Your turn")
        self.valid_moves = valid_moves
        self.callback = callback
