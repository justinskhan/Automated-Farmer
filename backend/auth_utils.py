import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone

#encode turens the password in byptes
#gensalt adds random data to the password to deal with duplicate passwords
#decode turns the bytes to a randomized hashed string in the db
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub":      user_id,
        "username": username,
        "exp":      datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")
