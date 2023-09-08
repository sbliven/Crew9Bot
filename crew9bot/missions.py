import asyncio
import itertools
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, List, Literal

from .cards import Card, deck
from .events import TasksAssigned
from .util import permute_range

if TYPE_CHECKING:
    from .player import Player

    State = Literal["win", "lose", "ongoing"]


class Mission(ABC):
    """Encapsulates the objective for the current round."""

    #: Mission number 1-100 are reserved for official missions
    mission_id: int

    def __init__(self, mission_id: int):
        self.mission_id = mission_id

    @abstractmethod
    def description(self) -> str:
        "Markdown description"
        ...

    @abstractmethod
    def get_status(self, played_cards: List[List[Card]]) -> "State":
        """Get the current win/lose/ongoing status"""
        ...

    @abstractmethod
    async def bid(self, players: List["Player"], commander: int) -> None:
        """Called before the round starts to assign tasks"""
        ...

    async def communicate(
        self, players: List["Player"], remaining: List[Iterable["Card"]], handnum: int
    ) -> None:
        """Called before each hand to allow communication"""
        pass

    def __eq__(self, other: Any) -> bool:
        """Missions are equal if they represent the same general type
        (although may differ in specific assignments).

        This default implementation compares the mission_id"""
        if not isinstance(other, self.__class__):
            return False
        return self.mission_id == other.mission_id


class RandomMission(Mission):
    """Test mission where cards are assigned randomly to players"""

    #: list of tasks for each player
    tasks: List[List[Card]]
    n_tasks: int
    #: Players, used for description only
    players: List["Player"]

    def __init__(self, mission_id: int, n_tasks: int):
        super().__init__(mission_id)
        self.players = []
        self.tasks = []
        self.n_tasks = n_tasks

    def description(self) -> str:
        "Markdown description"
        if not self.tasks:
            return f"Complete {self.n_tasks} tasks (Not yet assigned)"

        md = [f"Complete {self.n_tasks} tasks:"]
        for p in range(len(self.players)):
            cards = sorted(self.tasks[p])
            if cards:
                md.append(
                    f"- {self.players[p].get_name()} takes {' '.join(map(str,cards))}"
                )
        return "\n".join(md)

    async def bid(self, players: List["Player"], commander: int) -> None:
        self.players = players
        num_players = len(players)
        self.tasks = [[] for t in range(num_players)]
        all_tasks = random.sample(deck(), self.n_tasks)
        player_order = itertools.cycle(permute_range(commander, num_players))
        for player, card in zip(player_order, all_tasks):
            self.tasks[player].append(card)

        notices: List[asyncio.tasks.Task[Any]] = []
        for i, task in enumerate(self.tasks):
            notices.extend(
                asyncio.create_task(player.notify(TasksAssigned(task, self.players[i])))
                for player in self.players
            )
        await asyncio.wait(notices)

    def get_status(self, played_cards: List[List[Card]]) -> "State":
        """Get the current win/lose/ongoing status"""
        won = True  # all tasks successful
        for owner in range(len(self.tasks)):
            for task in self.tasks[owner]:
                task_finished = False
                for player, cards in enumerate(played_cards):
                    if task in cards:
                        if owner != player:
                            return "lose"
                        task_finished = True
                won = won and task_finished

        return "win" if won else "ongoing"


class ImpossibleMission(Mission):
    "Impossible to win"

    def __init__(self, mission_id: int = 0) -> None:
        super().__init__(mission_id)

    def description(self) -> str:
        return "Unwinnable."

    def get_status(self, played_cards: List[List[Card]]) -> "State":
        """Get the current win/lose/ongoing status"""
        return "ongoing"

    async def bid(self, players: List["Player"], commander: int) -> None:
        pass


def create_mission(mission_id: int, players: List["Player"], commander: int) -> Mission:
    if mission_id == 0:
        return ImpossibleMission(mission_id)
    # TODO stub mission
    return RandomMission(mission_id, mission_id)
