"""Fractional ordering.

Items carry a float `position`; inserting between two neighbours takes the
midpoint, so a move touches exactly one row. Repeated midpoint insertion
eventually exhausts float precision, at which point the column is rebalanced
to evenly spaced positions in a single pass.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Card

STEP = 1024.0
MIN_GAP = 1e-9


def midpoint(before: float | None, after: float | None) -> float:
    if before is None and after is None:
        return STEP
    if before is None:
        return after / 2  # type: ignore[operator]
    if after is None:
        return before + STEP
    return (before + after) / 2


def needs_rebalance(before: float | None, after: float | None) -> bool:
    if before is None and after is None:
        return False
    if before is None:
        return after < 2 * MIN_GAP  # type: ignore[operator]  # head inserts halve toward 0
    if after is None:
        return False  # tail inserts always have headroom
    return (after - before) < MIN_GAP


async def rebalance_column(session: AsyncSession, column_id: int) -> dict[int, float]:
    """Reassign evenly spaced positions to every card in a column."""
    cards = (
        await session.scalars(
            select(Card).where(Card.column_id == column_id).order_by(Card.position, Card.id)
        )
    ).all()
    positions: dict[int, float] = {}
    for i, card in enumerate(cards):
        card.position = (i + 1) * STEP
        positions[card.id] = card.position
    return positions


async def resolve_neighbour_positions(
    session: AsyncSession, column_id: int, before_id: int | None, after_id: int | None
) -> tuple[float | None, float | None]:
    """Fetch neighbour positions, validating they belong to the target column."""
    before = after = None
    if before_id is not None:
        card = await session.get(Card, before_id)
        if card is None or card.column_id != column_id:
            raise ValueError("before_id is not a card in the target column")
        before = card.position
    if after_id is not None:
        card = await session.get(Card, after_id)
        if card is None or card.column_id != column_id:
            raise ValueError("after_id is not a card in the target column")
        after = card.position
    if before is not None and after is not None and before > after:
        raise ValueError("before_id must precede after_id")
    return before, after
