import pytest

import crew9bot.events as evt
from crew9bot.cards import Card, Suite, get_winner


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


def test_takes() -> None:
    assert Card("2☘️").takes(Card("6⭐️"), Suite.Green)
    assert not Card("2☘️").takes(Card("6⭐️"), Suite.Yellow)
    assert not Card("2☘️").takes(Card("6⭐️"), Suite.Blue)
    assert Card("6⭐️").takes(Card("2☘️"), Suite.Yellow)
    assert not Card("6⭐️").takes(Card("2☘️"), Suite.Green)
    assert not Card("6⭐️").takes(Card("2☘️"), Suite.Blue)

    assert not Card("6⭐️").takes(Card("1🚀"), Suite.Yellow)
    assert Card("1🚀").takes(Card("6⭐️"), Suite.Yellow)


def test_winner() -> None:
    card_str = "9☘️ 4🚀"
    hand = Card.parse_hand(card_str)
    winner = get_winner(hand, Suite.Green)
    assert winner == 1

    card_str = "9☘️ 4🌀"
    hand = Card.parse_hand(card_str)
    winner = get_winner(hand, Suite.Green)
    assert winner == 0

    winner = get_winner(hand, Suite.Blue)
    assert winner == 1

    card_str = "1☘️ 4🌀 9☘️"
    hand = Card.parse_hand(card_str)
    winner = get_winner(hand, Suite.Green)
    assert winner == 2
    winner = get_winner(hand, Suite.Blue)
    assert winner == 1
