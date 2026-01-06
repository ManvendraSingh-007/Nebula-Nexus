from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr
from fastapi import HTTPException, Depends
from typing import Optional
from database import Session, get_database
import models
from config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expire_delta:  Optional[int] = None):
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_delta)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        claims=to_encode,
        key=SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token=token, key=SECRET_KEY, algorithms=ALGORITHM)
        user_email: str = payload.get("sub") 
        if user_email is None:
            raise HTTPException(status_code=404, detail="Invalid Token")
        
        return user_email
    
    except JWTError as j:
        raise HTTPException(status_code=404, detail=f"{j}")
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_database)):
    user_email = verify_access_token(token=token)
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
