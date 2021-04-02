import functools
import random
from dataclasses import dataclass
from enum import Enum
from typing import List


@functools.total_ordering
class Suite(Enum):
    Blue = "🌀"
    Pink = "🌸"
    Green = "☘️"
    Yellow = "⭐️"
    Rocket = "🚀"

    def __init__(self, icon):
        self.icon = icon

    def __lt__(self, other: "Suite"):
        return self.icon < other.icon

    def __str__(self):
        return self.icon


@dataclass
@functools.total_ordering
class Card:
    value: int
    suite: Suite

    def takes(self, other: "Card", lead: Suite):
        """True if one card can "take" the second, given a particular suite for
        the trick."""
        if self.suite == other.suite:
            return self.value > other.value
        if self.suite is Suite.Rocket:
            return True
        if other.suite is Suite.Rocket:
            return False
        if self.suite == lead:
            return True
        # No ordering between non-lead cards
        return False

    def __str__(self):
        return f"{self.value}{self.suite.icon}"

    def __lt__(self, other):
        if isinstance(other, Card):
            return (self.suite, self.value) < (other.suite, other.value)
        raise NotImplementedError


def deck() -> List[Card]:
    "Sorted deck"
    return [
        Card(i, suite)
        for suite in Suite
        for i in range(1, 5 if suite is Suite.Rocket else 10)
    ]


def shuffled_deck() -> List[Card]:
    "Shuffled deck"
    cards = deck()
    random.shuffle(cards)
    return cards
