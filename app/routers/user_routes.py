from fastapi import APIRouter, Depends, Cookie
from sqlalchemy.orm import Session
from app.models import User, Message, func
from app.auth import verify_access_token
from app.database import get_database
from .chat_routes import manager
from typing import Annotated

router = APIRouter(prefix="/api", tags=["Users"])

@router.get("/users")
async def get_all_users(access_token: str = Cookie(alias="Authorization"), db: Session = Depends(get_database)):

    current_user_id = verify_access_token(access_token)
    online_ids = manager.get_online_users()

    # 1. Join User with Message to count unread items for current_user_id
    result = db.query(User.id, User.username, func.count(Message.id).label("unread_count")).outerjoin(
        Message, 
        (Message.sender_id == User.id) & 
        (Message.receiver_id == current_user_id) & 
        (Message.is_read == False)
    ).filter(User.id != current_user_id).group_by(User.id).all()

    unread_map = [[sender_id, unread_count, sender_username, sender_id in online_ids] for sender_id, unread_count, sender_username in result]
    return unread_map

@router.get("/messages/{receiver_id}")
async def get_chat_history(
    receiver_id: int, 
    db: Session = Depends(get_database),
    # Use your verify logic to get the logged-in user's ID
    access_token: Annotated[str | None, Cookie(alias="Authorization")] = None
):
    # Verify the current user
    current_user_id = int(verify_access_token(access_token))

    # Fetch history where I am sender AND you are receiver OR vice versa
    messages = db.query(Message).filter(
        ((Message.sender_id == current_user_id) & (Message.receiver_id == receiver_id)) |
        ((Message.sender_id == receiver_id) & (Message.receiver_id == current_user_id))
    ).order_by(Message.timestamp.asc()).all()

    db.query(Message).filter(
    Message.sender_id == receiver_id,
    Message.receiver_id == current_user_id,
    Message.is_read == False
    ).update({"is_read": True})
    
    db.commit()

    return [
        {
            "sender_id": m.sender_id,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() + "Z"
        } 
        for m in messages
    ]
