<<<<<<< HEAD
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.utils.config import settings
from backend.auth import routes as auth_routes
from backend.routers import resumes as resume_routes


# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


app = FastAPI(
    title="Resume Parser & Job Matching API",
    version="1.0"
)


# CORS (allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # You can restrict later
=======
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
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD

@app.on_event("startup")
def on_startup():
    init_db()


# Include routes
app.include_router(auth_routes.router)
app.include_router(resume_routes.router)


@app.get("/")
def root():
    return {"status": "ok"}
=======
# include routers
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(resumes_router.router, prefix="/resumes", tags=["resumes"])

@app.on_event("startup")
def on_startup():
    # create DB tables
    SQLModel.metadata.create_all(engine)
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
