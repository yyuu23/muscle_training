"""
Account deletion API router (plan §6.4)

DELETE /account requires recent re-authentication. Deletion covers all
user data and is recorded in the deletion ledger.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentSession, CurrentUser
from app.modules.deletion.ledger import delete_user_data

router = APIRouter()

REAUTH_WINDOW_MINUTES = 15


@router.delete("/account", status_code=status.HTTP_202_ACCEPTED)
async def delete_account(
    request: Request,
    user: CurrentUser,
    session: CurrentSession,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete my account data. Requires a session created recently."""
    # Recent re-authentication: the current session must be young
    if session.created_at < datetime.now(tz=None) - timedelta(minutes=REAUTH_WINDOW_MINUTES):
        raise ApiError(
            ErrorCode.AUTH_REQUIRED,
            "删除账号前请重新登录确认身份（15 分钟内）",
        )

    counts = await delete_user_data(db, user.id)

    # Mark user deleting → disabled
    from app.db.models.auth import User

    account = await db.get(User, user.id)
    if account is not None:
        account.status = "deleting"
        # Immediate logical disable
        account.status = "disabled"
        account.username_normalized = f"deleted_{user.id}"
        await db.commit()

    return {
        "status": "deletion_completed",
        "deleted": counts,
        "user_id": str(user.id),
    }
