from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Activity, User
from ..schemas import ActivityOut


async def record(
    session: AsyncSession, board_id: int, user: User, verb: str, detail: dict
) -> dict:
    """Persist an activity entry in the caller's transaction.

    Returns the serialized payload so the caller can broadcast it *after*
    commit — clients must never see events for rolled-back mutations.
    """
    activity = Activity(board_id=board_id, user_id=user.id, verb=verb, detail=detail)
    activity.user = user
    session.add(activity)
    await session.flush()
    return ActivityOut.model_validate(activity).model_dump(mode="json")
