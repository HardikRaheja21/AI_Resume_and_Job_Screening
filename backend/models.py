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
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

class Resume(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    filepath: str
    parsed_text: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    matched_job: Optional[str] = None
    match_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
