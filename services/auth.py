import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from uuid import uuid4

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# -----------------------------
# PASSWORD HASHING
# -----------------------------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)  # >=10 rounds for security
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# -----------------------------
# JWT TOKEN GENERATION
# -----------------------------
def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# -----------------------------
# SESSION ID GENERATION
# -----------------------------
def generate_session_id():
    return str(uuid4())
