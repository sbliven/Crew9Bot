import functools
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar, Union, overload

T = TypeVar("T", bound="Card")


DECK_SIZE = 40


@functools.total_ordering
class Suite(Enum):
    Blue = "🌀"
    Pink = "🌸"
    Green = "☘️"
    Yellow = "⭐️"
    Rocket = "🚀"

    def __init__(self, icon: str) -> None:
        self.icon = icon

    def __lt__(self, other: "Suite") -> bool:
        return self.icon < other.icon

    def __str__(self) -> str:
        return self.icon


@dataclass
@functools.total_ordering
class Card:
    value: int
    suite: Suite

    _card_re = re.compile(rf'([0-9])({"|".join(s.value for s in Suite)})')

    @overload
    def __init__(self, value: int, suite: Suite) -> None:
        ...

    @overload
    def __init__(self, value: str, suite: None = None) -> None:
        ...

    def __init__(self, value: Union[int, str], suite: Optional[Suite] = None) -> None:
        """Create a Card, either from a value/suite pair or from a string representation"""
        if suite is None:
            assert isinstance(value, str)
            match = self._card_re.match(value)
            if not match:
                raise ValueError("Invalid card")

            self.suite = Suite(match.group(2))
            self.value = int(match.group(1))
        else:
            assert isinstance(value, int)
            self.suite = suite
            self.value = value

    def takes(self, other: "Card", lead: Suite) -> bool:
        """True if this card can "take" the second, given a particular suite for the trick."""
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

    def __str__(self) -> str:
        return f"{self.value}{self.suite.icon}"

    def __repr__(self) -> str:
        return f"{self.__class__}({str(self)})"

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Card):
            return (self.suite, self.value) < (other.suite, other.value)
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash((self.value, self.suite))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.value == other.value and self.suite == other.suite

    @classmethod
    def format_hand(cls: Type[T], hand: Iterable[T], markdown: bool = False) -> str:
        """String representation of the cards.

        Defaults to a one-line space-separated list.

        If markdown, gives a markdown list with one item per suite
        """
        if not markdown:
            return " ".join(map(str, sorted(hand)))
        return "\n".join(
            f"- {cls.format_hand(hand, False)}"
            for suite, cards in by_suite(hand).items()
        )

    @classmethod
    def parse_hand(cls: Type[T], hand: str) -> List[T]:
        return [cls(s) for s in hand.split(" ") if s]


def by_suite(hand: Iterable[Card]) -> Dict[Suite, List[Card]]:
    "Divide cards by suite"
    suites: Dict[Suite, List[Card]] = {s: [] for s in Suite}
    for card in hand:
        suites[card.suite].append(card)

    return suites


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
