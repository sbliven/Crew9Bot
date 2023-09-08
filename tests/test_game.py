#!/usr/bin/env python

"""Tests for `crew9bot` package."""

import random
from typing import List

import pytest

import crew9bot.events as evt
from crew9bot.cards import Card

# from crew9bot import crew9bot
from crew9bot.game import Game
from crew9bot.missions import RandomMission

from .mocks import MockPlayer, Player

# TODO https://shallowdepth.online/posts/2021/12/end-to-end-tests-for-telegram-bots/
# TODO

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_dealing() -> None:
    random.seed(0)
    game = Game()
    players = [MockPlayer(f"Player{i}") for i in range(4)]

    assert game.get_game_id() == "MLMCYB6N", "Random seed changed"

    for player in players:
        await game.join(player)
        assert isinstance(player.notices[-1], evt.JoinGame), player.notices[-1]

    await game.begin()

    hands = [Card.format_hand(hand) for hand in game.hands]

    assert hands[0] == "1☘️ 3☘️ 4☘️ 6☘️ 7⭐️ 1🌀 8🌀 3🌸 6🌸 8🌸"
    assert hands[1] == "1⭐️ 2⭐️ 9⭐️ 2🌀 3🌀 6🌀 7🌀 2🌸 4🌸 7🌸"
    assert hands[2] == "7☘️ 9☘️ 3⭐️ 8⭐️ 4🌀 5🌀 9🌸 1🚀 2🚀 3🚀"
    assert hands[3] == "2☘️ 5☘️ 8☘️ 4⭐️ 5⭐️ 6⭐️ 9🌀 1🌸 5🌸 4🚀"

    assert game.commander == 3


@pytest.mark.asyncio
async def test_mission1() -> None:
    random.seed(0)
    game = Game()
    players: List["Player"] = [MockPlayer(f"Player{i}") for i in range(4)]

    assert game.get_game_id() == "MLMCYB6N", "Random seed changed"

    for player in players:
        await game.join(player)

    await game.set_mission(1)
    mission = game.mission
    assert isinstance(mission, RandomMission)

    await game.begin()

    players = game.players  # reordered

    hands = [Card.format_hand(hand) for hand in game.hands]

    assert hands[0] == "1☘️ 3☘️ 4☘️ 6☘️ 7⭐️ 1🌀 8🌀 3🌸 6🌸 8🌸"
    assert hands[1] == "1⭐️ 2⭐️ 9⭐️ 2🌀 3🌀 6🌀 7🌀 2🌸 4🌸 7🌸"
    assert hands[2] == "7☘️ 9☘️ 3⭐️ 8⭐️ 4🌀 5🌀 9🌸 1🚀 2🚀 3🚀"
    assert hands[3] == "2☘️ 5☘️ 8☘️ 4⭐️ 5⭐️ 6⭐️ 9🌀 1🌸 5🌸 4🚀"

    assert game.commander == 3

    assert mission.tasks[0] == []
    assert mission.tasks[1] == []
    assert mission.tasks[2] == []
    assert Card.format_hand(mission.tasks[3]) == "6🌀"

    await game.play(players[3], Card("9🌀"))

    assert game.mission.get_status(game.played_cards) == "ongoing"

    await game.play(players[0], Card("8🌀"))
    await game.play(players[1], Card("6🌀"))
    await game.play(players[2], Card("4🌀"))

    assert game.mission.get_status(game.played_cards) == "win"

    return


@pytest.mark.asyncio
async def test_current_hand() -> None:
    "Tests the internal _current_hand method"
    game = Game()
    await game.join(MockPlayer("P1"))
    await game.join(MockPlayer("P2"))
    await game.join(MockPlayer("P3"))
    game.commander = 1
    game.next_player = 1

    hand, lead = game._current_hand()
    assert hand == None
    assert lead == 1

    game.played_cards[1].append(Card("2🌀"))
    game.next_player = 2

    hand, lead = game._current_hand()
    assert hand == [None, Card("2🌀"), None]
    assert lead == 1

    game.played_cards[2].append(Card("5🌀"))
    game.next_player = 0

    hand, lead = game._current_hand()
    assert hand == [None, Card("2🌀"), Card("5🌀")]
    assert lead == 1

    game.played_cards[0].append(Card("3🌀"))
    game.next_player = 1

    hand, lead = game._current_hand()
    assert hand == [Card("3🌀"), Card("2🌀"), Card("5🌀")]
    assert lead == 1
