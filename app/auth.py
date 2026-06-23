import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Form
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session
from .database import get_db, User

# router /auth
router = APIRouter(prefix="/auth", tags=["auth"])

# jwt secret key (REPLACE!)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
ALGO = "HS256"
crypt = CryptContext(["pbkdf2_sha256"], deprecated="auto")

# --------------------- JWT helpers ----------------------

def make_token(name: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": name, "exp": int(exp.timestamp())}, SECRET_KEY, ALGO)

# ---------------------- Auth routes ---------------------

@router.post("/register")
def register(username: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    if not username.strip() or not password.strip():
        raise HTTPException(422, "need username and password")

    # deny duplicates
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(409, "taken")

    # save user
    db.add(User(
        username=username,
        password_hash=crypt.hash(password),
        is_admin=False
    ))
    db.commit()
    return {"ok": 1, "user": username}

# return token if logged in
@router.post("/login")
def login(username: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    # blank check
    if not username.strip() or not password.strip():
        raise HTTPException(422, "missing login data")

    u = db.query(User).filter_by(username=username).first()

    # password check
    if not u or not crypt.verify(password, u.password_hash):
        raise HTTPException(401, "no access")

    return {"access_token": make_token(username), "token": 1}
