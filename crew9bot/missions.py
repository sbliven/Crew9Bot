from dataclasses import dataclass

@dataclass(frozen=True)
class Mission:
    mission_id: int
    tasks: int

    @property
    def description(self):
        "Markdown description"
        return f"Complete {self.tasks} tasks"

all_missions = {
    1: Mission(1, 1),
    2: Mission(2, 2),
    3: Mission(3, 4),
}
