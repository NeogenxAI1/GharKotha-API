from fastapi import APIRouter, Depends, Header, HTTPException, Body
from sqlalchemy.orm import Session
from auth.utils import get_user_id_from_token
from core.database import SessionLocal
from src.db_models.user_profile import schemas
from src.db_models.generic_registry import UserProfile



router = APIRouter(prefix="/user-info")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_active_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/", response_model=list[schemas.UserProfileOutput])
# @router.get("/")
def get_user_info(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_info = db.query(UserProfile).filter(
        UserProfile.user_id == current_user).all()
    return user_info


@router.post("/")
def get_user_info(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_info = db.query(UserProfile).filter(
        UserProfile.user_id == current_user).all()
    return user_info


@router.delete("/1")
def get_user_info(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_info = db.query(UserProfile).filter(
        UserProfile.user_id == current_user).all()
    return user_info

