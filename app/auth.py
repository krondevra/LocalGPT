import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import jwt
from sqlalchemy.orm import Session
from .database import get_db, User

# router /auth
router = APIRouter(prefix="/auth", tags=["auth"])

# jwt secret key (REPLACE!)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
ALGO = "HS256"
MAX_BCRYPT_LEN = 72

# used by /me
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# -------------------- bcrypt helpers --------------------

def hash_password(password: str) -> str:
    pwd = password[:MAX_BCRYPT_LEN].encode()
    hashed = bcrypt.hashpw(pwd, bcrypt.gensalt())
    return hashed.decode()

def verify_password(password: str, hashed: str) -> bool:
    pwd = password[:MAX_BCRYPT_LEN].encode()
    return bcrypt.checkpw(pwd, hashed.encode())

# --------------------- JWT helpers ----------------------

def make_token(name: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": name, "exp": int(exp.timestamp())}, SECRET_KEY, ALGO)

def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        data = jwt.decode(token, SECRET_KEY, [ALGO])
        name = data.get("sub")
        if not name:
            raise Exception
    except:
        raise HTTPException(401, "bad token")

    u = db.query(User).filter_by(username=name).first()
    if not u:
        raise HTTPException(401, "no user")
    return u

def admin_user(u: User = Depends(current_user)) -> User:
    if not u.is_admin:
        raise HTTPException(403, "for admin")
    return u

# ----------------------- Helper -------------------------

def _admins_count(db: Session) -> int:
    return db.query(User).filter_by(is_admin=True).count()

# ---------------------- Auth routes ---------------------

@router.post("/register")
def register(username: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    if not username.strip() or not password.strip():
        raise HTTPException(422, "need username and password")

    # deny duplicates
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(409, "taken")

    # save user
    # count users to detect first one
    c = db.query(User).count()
    db.add(User(
        username=username,
        password_hash=hash_password(password),
        is_admin=(c == 0)
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
    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(401, "no access")

    return {"access_token": make_token(username), "token_type": "bearer"}

@router.get("/me")
def me(u: User = Depends(current_user)):
    return {"name": u.username, "admin": u.is_admin}

@router.get("/list")
def list_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [{"id": u.id, "name": u.username, "admin": u.is_admin} for u in users]

@router.delete("/users/id/delete", status_code=204)
def delete_user(user_id: int, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    user_to_delete = db.get(User, user_id)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    # count total admins
    total_admins = _admins_count(db)
    if user_to_delete.is_admin and total_admins == 1:
        raise HTTPException(status_code=403, detail="Can't delete the only admin")

    db.delete(user_to_delete)
    db.commit()

@router.post("/users/id/promote", status_code=204)
def promote_user(user_id: int, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        return  # already admin
    user.is_admin = True
    db.commit()

@router.post("/users/id/demote", status_code=204)
def demote_user(user_id: int, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_admin and _admins_count(db) <= 1:
        raise HTTPException(status_code=403, detail="Can't demote the last admin")

    user.is_admin = False
    db.commit()
