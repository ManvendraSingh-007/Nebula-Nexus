from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends
from typing import Optional
from database import Session, get_database
import models
from config import Config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expire_delta:  Optional[int] = None):
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_delta)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        claims=to_encode,
        key=Config.SECRET_KEY,
        algorithm=Config.ALGORITHM
    )

    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token=token, key=Config.SECRET_KEY, algorithms=Config.ALGORITHM)
        # {'sub': '2', 'exp': 176783691}
        user_id: str = payload.get("sub") 
        if user_id is None:
            raise HTTPException(status_code=404, detail="Invalid Token")
        
        return user_id
    
    except JWTError as j:
        raise HTTPException(status_code=404, detail=f"{j}")
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_database)):
    user = verify_access_token(token=token)
    user = db.query(models.User).filter(models.User.email == user[0]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
