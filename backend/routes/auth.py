from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from models import AuthRequest, AuthResponse
from db import get_db
from auth_utils import hash_password, verify_password, create_token

router = APIRouter(prefix="/auth")

#will fire when user is signing up
@router.post("/signup", response_model=AuthResponse)
def signup(body: AuthRequest):
    db       = get_db()
    username = body.username.strip()
    #if there is no username or password:
    if not username or not body.password:
        raise HTTPException(400, "Username and password required")
    #username needs to be more than 3 characters (might change)
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    #password needs to be more than 4 characters (might change)
    if len(body.password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters")
    #condition if username is already taken
    if db.users.find_one({"username": username}):
        raise HTTPException(400, "Username already taken")
    #data stored in mongoDB, will be extended with more info
    now    = datetime.now(timezone.utc)
    result = db.users.insert_one({
        "username":      username,
        "password_hash": hash_password(body.password),
        "created_at":    now,
        "last_login_at": now,
    })

    token = create_token(str(result.inserted_id), username)
    return AuthResponse(token=token, username=username)


@router.post("/login", response_model=AuthResponse)
def login(body: AuthRequest):
    db       = get_db()
    username = body.username.strip()
    user     = db.users.find_one({"username": username})

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")

    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": datetime.now(timezone.utc)}},
    )

    token = create_token(str(user["_id"]), user["username"])
    return AuthResponse(token=token, username=user["username"])
