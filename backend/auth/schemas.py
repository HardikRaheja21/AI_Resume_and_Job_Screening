# from pydantic import BaseModel

# class UserCreate(BaseModel):
#     username: str
#     password: str

# class UserRead(BaseModel):
#     id: int
#     username: str

# class Token(BaseModel):
#     access_token: str
#     token_type: str
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    email: EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str
