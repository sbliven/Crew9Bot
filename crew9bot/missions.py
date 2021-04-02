import random
from dataclasses import dataclass
from typing import List

from .cards import Card, deck


@dataclass(frozen=True)
class Mission:
    mission_id: int
    tasks: int

    @property
    def description(self):
        "Markdown description"
        return f"Complete {self.tasks} tasks"

    def make_tasks(self) -> List[Card]:
        all_tasks = deck()
        return random.sample(all_tasks, self.tasks)


all_missions = {
    1: Mission(1, 1),
    2: Mission(2, 2),
    3: Mission(3, 4),
}
