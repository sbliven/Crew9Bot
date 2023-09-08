import pytest

import crew9bot.events as evt
from crew9bot.cards import Card, Suite


def test_parse() -> None:
    card_str = "2☘️ 4⭐️ 9🌀 5🌸 4🚀"
    cards = Card.parse_hand(card_str)
    assert len(cards) == 5
    assert cards[0].suite == Suite.Green
    assert cards[4].value == 4

    assert Card.parse_hand("") == []

    with pytest.raises(ValueError):
        Card.parse_hand("NA")


def test_format_cards() -> None:
    card_str = "2☘️ 6⭐️ 5🌸 9🌀 1🌸 4🚀 5⭐️"
    cards = Card.parse_hand(card_str)
    assert len(cards) == 7
