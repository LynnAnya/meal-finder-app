from contextlib import asynccontextmanager
from fastapi import  FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles

from seed import seed_data
from database import Base, engine, AsyncSessionLocal
#from auth import get_current_user
from routers import users, reviews, dishes

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_data()

    yield
    #shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(dishes.router, prefix="/dishes", tags=["Dishes"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])

################
# home main
################


##############
# handle global error 
#############
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
  
    return await http_exception_handler(request, exception)

@app.exception_handler(RequestValidationError) #422
async def validation_exception_handler(request: Request, exception: RequestValidationError):

    return await request_validation_exception_handler(request, exception)











