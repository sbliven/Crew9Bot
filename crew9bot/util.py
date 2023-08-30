import itertools
from typing import TYPE_CHECKING, Iterable, List, TypeVar

T = TypeVar("T")


def permute(arr: List[T], i: int) -> Iterable[T]:
    "Circularly permute an array starting at index i"
    return itertools.chain(arr[i:], arr[:i])


def permute_range(start: int, n: int) -> Iterable[int]:
    """Circularly permuted array of consecutive integers

    Yields start...n-1, 0...start-1
    """
    return itertools.chain(range(start, n), range(start))
