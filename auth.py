from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError
from typing import Optional
from config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM

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