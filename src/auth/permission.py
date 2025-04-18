from fastapi import Depends, HTTPException, status

from src.auth.dependances import get_current_user
from src.db.models import User
from src.schemas.user import UserRole


async def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Permission denied")
    return current_user

async def agent_or_admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.AGENT]:
        raise HTTPException(status_code=403, detail="Permission denied")
    return current_user
