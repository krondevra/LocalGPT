import os
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from .database import get_db, User

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Export SECRET_KEY before running.")

ALGO = "HS256"
TOKEN_LIFETIME_HOURS = 1
MAX_BCRYPT_LEN = 72
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# -------------------- Validation helpers --------------------

def validate_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-24 characters and contain only letters, numbers and underscore.",
        )
    return username


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must contain at least 8 characters.")
    return password


# -------------------- Password helpers --------------------

def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes, so the input is limited intentionally.
    pwd = password[:MAX_BCRYPT_LEN].encode("utf-8")
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    pwd = password[:MAX_BCRYPT_LEN].encode("utf-8")
    return bcrypt.checkpw(pwd, hashed.encode("utf-8"))


# --------------------- JWT helpers ----------------------

def make_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=TOKEN_LIFETIME_HOURS)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGO)


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username = data.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _admins_count(db: Session) -> int:
    return db.query(User).filter_by(is_admin=True).count()


# ---------------------- Auth routes ---------------------

@router.post("/register")
def register(username: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    username = validate_username(username)
    password = validate_password(password)

    if db.query(User).filter_by(username=username).first():
        raise HTTPException(status_code=409, detail="Username is already taken")

    users_count = db.query(User).count()
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=(users_count == 0),
    )
    db.add(user)
    db.commit()

    return {"ok": True, "user": username, "first_user_admin": user.is_admin}


@router.post("/login")
def login(username: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    username = username.strip()
    if not username or not password:
        raise HTTPException(status_code=422, detail="Username and password are required")

    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    return {"access_token": make_token(username), "token_type": "bearer"}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.username, "admin": user.is_admin}


@router.get("/list")
def list_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        {
            "id": user.id,
            "name": user.username,
            "admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current: User = Depends(admin_user), db: Session = Depends(get_db)):
    user_to_delete = db.get(User, user_id)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    if user_to_delete.id == current.id:
        raise HTTPException(status_code=403, detail="You cannot delete your own account while logged in")

    if user_to_delete.is_admin and _admins_count(db) <= 1:
        raise HTTPException(status_code=403, detail="Cannot delete the only admin")

    db.delete(user_to_delete)
    db.commit()


@router.post("/users/{user_id}/promote", status_code=204)
def promote_user(user_id: int, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    db.commit()


@router.post("/users/{user_id}/demote", status_code=204)
def demote_user(user_id: int, current: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current.id:
        raise HTTPException(status_code=403, detail="You cannot demote your own account while logged in")

    if user.is_admin and _admins_count(db) <= 1:
        raise HTTPException(status_code=403, detail="Cannot demote the last admin")

    user.is_admin = False
    db.commit()
