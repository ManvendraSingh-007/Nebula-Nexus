from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_database
from app.models import func
from app.models import Message
import json, datetime

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: websocket_object}
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    def get_online_users(self):
        return list(self.active_connections.keys())

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_database)):
    await manager.connect(user_id, websocket)
    # Broadcast to all other users that this user is online
    await broadcast_user_status(user_id, True)

    try:
        while True:
            # Receive data from the client
            data = await websocket.receive_text()
            message_data = json.loads(data) # Expecting {"receiver_id": 2, "content": "Hi!"}
            
            # 1. Save to MySQL db
            new_message = Message(
                sender_id=user_id,
                receiver_id=int(message_data["receiver_id"]),
                content=message_data["content"]
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            # Get unread counts
            unread_count = db.query(func.count(Message.id)).filter(
                Message.sender_id == user_id,
                Message.receiver_id == message_data["receiver_id"],
                Message.is_read == False
            ).scalar()


            # prepare response
            receiver_id = int(message_data["receiver_id"])
            receiver_message = {
                "type": "chat",
                "sender_id": user_id,
                "content": message_data["content"],
                "timestamp": new_message.timestamp.isoformat(),
                "message_id": new_message.id,
                "unread_count": unread_count
            }

            
            # 2. Push to the receiver
            await manager.send_personal_message(receiver_message, receiver_id)

            # 3. Also send to sender (for confirmation with DB timestamp)
            sender_message = receiver_message.copy()
            sender_message["type"] = "message_sent"
            await manager.send_personal_message(sender_message, user_id)

    except WebSocketDisconnect:
        # Broadcast that user went offline
        await broadcast_user_status(user_id, False)
        manager.disconnect(user_id)


async def broadcast_user_status(user_id: int, is_online: bool):
    """Broadcast user online/offline status to all other users"""

    status_message = {
        "type": "user_status",
        "user_id": user_id,
        "is_online": is_online,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    for uid, connection in manager.active_connections.items():
        if uid != user_id:
            try:
                await connection.send_json(status_message)
            except:
                if uid in manager.active_connections.keys():
                    del manager.active_connections[uid]