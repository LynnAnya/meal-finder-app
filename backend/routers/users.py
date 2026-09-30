from datetime import timedelta, UTC, datetime
from typing import Annotated
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from PIL import UnidentifiedImageError
from sqlalchemy import delete as sql_delete
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from starlette.concurrency import run_in_threadpool
import models
from auth import (
    create_access_token,
    hash_password,
    verify_password,
    CurrentUser,
    generate_reset_token,
    hash_reset_token,
)
from email_utils import send_password_reset_email   
from database import  get_db
from schemas import (
    Token,
    UserCreate,
    UserPrivate,
    UserUpdate,
    ReviewResponse,
    DishResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from config import settings
from image_utils import delete_profile_image, process_profile_image, upload_profile_image


router = APIRouter()

###############
# user activities 
##############
# get all current user's reviews. ----DONE
@router.get("/me/reviews", response_model=Page[ReviewResponse])
async def get_user_reviews(current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)], ):
   
    query = (select(models.Review)
        .options(selectinload(models.Review.reviewer))
        .where(models.Review.user_id == current_user.id)
        .order_by(models.Review.id.desc())
    )
    return await paginate(db, query)

# get all favourite dishes feature. ----DONE
@router.get("/me/favourites", response_model=list[DishResponse])
async def get_favourites(current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)],):

    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.favourite_dishes).selectinload(models.Dish.restaurant))
        .where(models.User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    return user.favourite_dishes

# REMOVE SPECIFIC FAVOURITE (Swipe to delete from Favorites screen) --DONE
@router.delete("/me/favourites/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favourite(
    dish_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.Favourite).where(
        models.Favourite.user_id == current_user.id,
        models.Favourite.dish_id == dish_id
    ))
    existing_favourite = result.scalar_one_or_none()

    if not existing_favourite:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Item not in your favourites list")

    await db.delete(existing_favourite)
    await db.commit()
    return None

###############
# user auth account
##############
#  register - create new user ----DONE
@router.post("",response_model=UserPrivate,status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    #check if username, email already existed, otherwise create the new one 
    result = await db.execute(select(models.User).where(func.lower(models.User.username) == user.username.lower()),)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This username already exists",
        )

    result = await db.execute(select(models.User).where(func.lower(models.User.email) == user.email.lower()),)
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This email already exists",
        )
    
    #create new user here
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash= hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# login  -----DONE
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
): 
    # Oauth..Requestform uses username field, but we treat it as email
    result = await db.execute(select(models.User).where(func.lower(models.User.email) == form_data.username.lower()),)
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    #create access token w/h user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")

# get current user - prfile. -----DONE 5/8
@router.get("/me", response_model=UserPrivate)
async def get_current_user(current_user: CurrentUser): return current_user

#user gets the email to reset password
@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(func.lower(models.User.email) == request_data.email.lower()))
    user = result.scalars().first()

    if user:
        await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == user.id))

    #generate new token
    token = generate_reset_token()
    token_hash = hash_reset_token(token)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.reset_token_expire_minutes)
    reset_token = models.PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    db.add(reset_token)
    await db.commit()

    #background task to send email
    background_tasks.add_task(
        send_password_reset_email,
        to_email=user.email,
        username=user.username,
        token=token,
    )
    return {"message": "If an account exists with this email, you will receive password reset instructions shortly."}


#when user clicks on the reset pwd link
@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request_data: ResetPasswordRequest,db: Annotated[AsyncSession, Depends(get_db)],):
    token_hash = hash_reset_token(request_data.token)

    result = await db.execute(
        select(models.PasswordResetToken).where(models.PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid or expired reset token.",
        )

    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,detail="Reset token has expired.",
        )

    result = await db.execute(select(models.User).where(models.User.id == reset_token.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid or expired reset token.",
        )

    user.password_hash = hash_password(request_data.new_password)

    await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == user.id))
    await db.commit()
    return {"message": "Password has been reset successfully. You can now log in with your new password."}

# logined user changes password
@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(password_data.new_password)
    await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == current_user.id))
    await db.commit()
    return {"message": "Password has been changed successfully."}

# user update profile username, email. -----DONE 5/8
#@router.patch("/me", response_model=UserResponse)
@router.patch("/me", response_model=UserPrivate) 
async def update_user_account(
                current_user: CurrentUser,
                user_update: UserUpdate,
                db: Annotated[AsyncSession, Depends(get_db)]
):
    if user_update.username is not None and user_update.username.lower() != current_user.username.lower():
        result = await db.execute(select(models.User).where(func.lower(models.User.username) == user_update.username.lower() ))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exists",
            )

    if user_update.email is not None and user_update.email.lower() != current_user.email.lower():
        result = await db.execute(select(models.User).where(func.lower(models.User.email) == user_update.email.lower()))
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,detail="Email already registered",
            )

    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "email" and value is not None:
            value = value.lower()
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user
    
  
#  user deletes account  -----DONE 5/8
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    current_user: CurrentUser, 
    db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.User).where(models.User.id == current_user.id))
    user = result.scalars().first()
    if not user:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, details="User not found")

    old_filename = current_user.image_file

    await db.delete(current_user)
    await db.commit()
    if old_filename:
        await delete_profile_image(old_filename) 

    return None


###########################
# user uploads profile picture 
##########################
# user profile image upload
@router.patch("/me/picture", response_model=UserPrivate)
async def upload_user_picture(
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024*1024)}MB",
        )
    # actual img processing start validating
    try:
        processed_bytes, new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP, HEIC).",
        ) from err

    # upload to S3 cloud storage
    try: 
        await upload_profile_image(processed_bytes, new_filename)
    except ClientError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image. Please try again",
        ) from err

    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)

    if old_filename: 
        await delete_profile_image(old_filename)

    return current_user

@router.delete("/me/picture", response_model=UserPrivate)
async def delete_user_picture(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,detail="No profile picture to delete",)
    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)

    await delete_profile_image(old_filename)
    return current_user


"""""
#user favourite dishes --
@router.get("/me/favourites", response_model=list[DishResponse], name="favourite_dishes")
async def get_user_favourites(current_user: CurrentUser,db: Annotated[AsyncSession, Depends(get_db)]):    
    query = (
        select(models.Dish)
        .join(models.Favourite, models.Dish.id == models.Favourite.dish_id)
        .where(models.Favourite.user_id == current_user.id)
        .options(joinedload(models.Dish.restaurant))
        .order_by(models.Favourite.id.desc(),) 
    )
    result = await db.execute(query)
    fav_dishes = result.scalars().unique().all()
    return fav_dishes
"""""
