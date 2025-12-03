<<<<<<< HEAD
from pydantic import BaseModel, EmailStr
from typing import Optional
=======
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
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91

class UserCreate(BaseModel):
    email: EmailStr
    password: str
<<<<<<< HEAD
    full_name: Optional[str] = None
=======
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91

class UserRead(BaseModel):
    id: int
    email: EmailStr
<<<<<<< HEAD
    full_name: Optional[str]

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
=======

class Token(BaseModel):
    access_token: str
    token_type: str
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
