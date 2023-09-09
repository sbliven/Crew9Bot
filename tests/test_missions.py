import random
from typing import TYPE_CHECKING, List

import pytest

from crew9bot.missions import RandomMission

from .mocks import MockPlayer

if TYPE_CHECKING:
    from crew9bot.player import Player


@pytest.mark.asyncio
async def test_mission_iter() -> None:
    random.seed(0)
    players: List["Player"] = [MockPlayer(f"Player{i}") for i in range(3)]

    mission = RandomMission(1, 1)

    await mission.bid(players, 0)

    tasks = list(mission.items())

    assert len(tasks) == 1
    card, owner = tasks[0]
    assert owner == 0
    assert str(card) == "7☘️", card
