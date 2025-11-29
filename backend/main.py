# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from .database import engine, SQLModel
# from .routers import auth as auth_router
# from .routers import resumes as resumes_router
# from .utils.config import settings


# app = FastAPI(title="AI Resume Parser & Job Matching")

# # CORS (allow frontend localhost during dev)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.CORS_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # include routers
# app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
# app.include_router(resumes_router.router, prefix="/resumes", tags=["resumes"])

# @app.on_event("startup")
# def on_startup():
#     # create DB tables
#     from .models import SQLModel as ModelsSQL  # alias to make mypy happy
#     SQLModel.metadata.create_all(engine)



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, SQLModel
from .routers import auth as auth_router
from .routers import resumes as resumes_router
from .utils.config import settings

app = FastAPI(title="AI Resume Parser & Job Matching")

# ---- CORS FIX ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <---- Important Fix
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(resumes_router.router, prefix="/resumes", tags=["resumes"])

@app.on_event("startup")
def on_startup():
    # create DB tables
    SQLModel.metadata.create_all(engine)
