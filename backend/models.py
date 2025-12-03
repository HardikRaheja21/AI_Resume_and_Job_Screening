<<<<<<< HEAD
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
=======
# from typing import Optional
# from sqlmodel import SQLModel, Field
# from datetime import datetime

# class User(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     username: str = Field(index=True, unique=True)
#     hashed_password: str

# class Resume(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     filename: str
#     filepath: str
#     parsed_text: Optional[str] = None
#     email: Optional[str] = None
#     name: Optional[str] = None
#     matched_job: Optional[str] = None
#     match_score: Optional[float] = None
#     created_at: datetime = Field(default_factory=datetime.utcnow)
from typing import Optional
from sqlmodel import SQLModel, Field
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
<<<<<<< HEAD
    email: str = Field(index=True, nullable=False, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
=======
    email: str = Field(index=True, unique=True)
    hashed_password: str
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91

class Resume(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    filepath: str
    parsed_text: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
<<<<<<< HEAD
    created_at: datetime = Field(default_factory=datetime.utcnow)
    matched_job: Optional[str] = None
    match_score: Optional[float] = None
=======
    matched_job: Optional[str] = None
    match_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
