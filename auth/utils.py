from fastapi import BackgroundTasks
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from auth.models import UserLog
from core.config import settings
import smtplib
from email.mime.text import MIMEText

from core.database import SessionLocal
import os

def getPublicKey():
    path = os.getcwd() +"/keys/" +"public_key.pem"
    with open(path, "rb") as f:
        key = f.read()
    return key


def get_user_id_from_token(token: str):
    try:
        payload = jwt.decode(token, getPublicKey(),
                             algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def log_user_event(event: str, user_id=None, details=None, ip_address: str = None):
    db = SessionLocal()
    try:
        log = UserLog(user_id=user_id, event=event,
                      details=details, ip_address=ip_address)
        db.add(log)
        db.commit()
    finally:
        db.close()


def schedule_log_event(bg_tasks: BackgroundTasks, user_id: str, event: str, details: str = None, ip_address: str = None):
    bg_tasks.add_task(log_user_event, event, user_id, details, ip_address)
