from pydantic import BaseModel, EmailStr


class UserProfileOutput(BaseModel):
    first_name: str
    last_name: str

    class Config:
        from_attributes = True
