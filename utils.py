import bcrypt

# takes raw password -> returns an hashed one (#####)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password=password.encode(), salt=bcrypt.gensalt())

# checks the raw password with the respected hashed one
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password=password.encode(), hashed_password=hashed_password.encode())