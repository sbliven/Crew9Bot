import functools
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar, Union, overload

T = TypeVar("T", bound="Card")


DECK_SIZE = 40


@functools.total_ordering
class Suit(Enum):
    Blue = "🌀"
    Pink = "🌸"
    Green = "☘️"
    Yellow = "⭐️"
    Rocket = "🚀"

    def __init__(self, icon: str) -> None:
        self.icon = icon

    def __lt__(self, other: "Suit") -> bool:
        return self.icon < other.icon

    def __str__(self) -> str:
        return self.icon


@dataclass
@functools.total_ordering
class Card:
    value: int
    suit: Suit

    _card_re = re.compile(rf'([0-9])({"|".join(s.value for s in Suit)})')

    @overload
    def __init__(self, value: int, suit: Suit) -> None:
        ...

    @overload
    def __init__(self, value: str, suit: None = None) -> None:
        ...

    def __init__(self, value: Union[int, str], suit: Optional[Suit] = None) -> None:
        """Create a Card, either from a value/suit pair or from a string representation"""
        if suit is None:
            assert isinstance(value, str)
            match = self._card_re.match(value)
            if not match:
                raise ValueError("Invalid card")

            self.suit = Suit(match.group(2))
            self.value = int(match.group(1))
        else:
            assert isinstance(value, int)
            self.suit = suit
            self.value = value

    def takes(self, other: "Card", lead: Suit) -> bool:
        """True if this card can "take" the second, given a particular suit for the trick."""
        if self.suit == other.suit:
            return self.value > other.value
        if self.suit is Suit.Rocket:
            return True
        if other.suit is Suit.Rocket:
            return False
        if self.suit == lead:
            return True
        # No ordering between non-lead cards
        return False

    def __str__(self) -> str:
        return f"{self.value}{self.suit.icon}"

    def __repr__(self) -> str:
        return f"{self.__class__}({str(self)})"

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Card):
            return (self.suit, self.value) < (other.suit, other.value)
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash((self.value, self.suit))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.value == other.value and self.suit == other.suit

    @classmethod
    def format_hand(cls: Type[T], hand: Iterable[T], markdown: bool = False) -> str:
        """String representation of the cards.

        Defaults to a one-line space-separated list.

        If markdown, gives a markdown list with one item per suit
        """
        if not markdown:
            return " ".join(map(str, sorted(hand)))
        return "\n".join(
            f"- {cls.format_hand(hand, False)}" for suit, cards in by_suit(hand).items()
        )

    @classmethod
    def parse_hand(cls: Type[T], hand: str) -> List[T]:
        return [cls(s) for s in hand.split(" ") if s]


def by_suit(hand: Iterable[Card]) -> Dict[Suit, List[Card]]:
    "Divide cards by suit"
    suits: Dict[Suit, List[Card]] = {s: [] for s in Suit}
    for card in hand:
        suits[card.suit].append(card)

    return suits


def deck() -> List[Card]:
    "Sorted deck"
    return [
        Card(i, suit)
        for suit in Suit
        for i in range(1, 5 if suit is Suit.Rocket else 10)
    ]


def shuffled_deck() -> List[Card]:
    "Shuffled deck"
    cards = deck()
    random.shuffle(cards)
    return cards


def get_winner(cards: List[Card], lead: Suit) -> int:
    "Get index of the winning card"
    # Safe to assume that at least one card has the lead suit
    winner = 0

    for i in range(1, len(cards)):
        if cards[i].takes(cards[winner], lead):
            winner = i

    return winner
