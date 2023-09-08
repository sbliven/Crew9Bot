from crew9bot.util import permute_range


def test_permute_range() -> None:
    assert list(permute_range(0, 4)) == [0, 1, 2, 3]
    assert list(permute_range(1, 4)) == [1, 2, 3, 0]
    assert list(permute_range(4, 4)) == [0, 1, 2, 3]
