from typing import Annotated
from config import settings
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from auth import CurrentUser
import models
from database import get_db
from schemas import (
    DishResponse,
    DishDetailResponse,
    ReviewCreate,
    ReviewResponse,
    CompareRequest,
    CompareResponse,
)
from integrations.ai import ai_service
from geo_utils import calculate_distance_meters, estimate_walk_minutes

router = APIRouter()

###############
# Dish activities 
###############
# all dishes (not details, before user click). [[-not used yet -search can show all too]] ----DONE
@router.get("", response_model=list[DishResponse], name="dishes")
async def get_home(db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(models.Dish).options(joinedload(models.Dish.restaurant)))
    dishes = result.scalars().all()
    return dishes

#user search/filter dish -> get list ---DONE
@router.get("/search", response_model=list[DishResponse])
async def get_search_dishes(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str | None, Query(description="Search dish name")] = None,
    max_price: Annotated[float | None, Query(ge=0, description="Max price filter")] = None,
    min_rating: Annotated[float | None, Query(ge=0.0, le=5.0, description="Minimum rating filter (0-5)")] = None,
    menu_category: Annotated[str | None, Query(description="Category filter")] = None,
):  
    query = select(models.Dish).options(joinedload(models.Dish.restaurant))

    if q and q.strip():
        query = query.where(models.Dish.name.ilike(f"%{q.strip()}%"))

    if max_price is not None:
        query = query.where(models.Dish.price <= max_price)

    # Filter by minimum rating (0 to 5)
    if min_rating is not None:
        query = query.where(models.Dish.average_rating >= min_rating)

    if menu_category:
       query = query.where(models.Dish.menu_category.ilike(menu_category.strip()))

    result = await db.execute(query)
    dishes = result.scalars().unique().all()
    return dishes

# get specfic dish detail from specific restaurant. ---- DONE
@router.get("/{dish_id}", response_model=DishDetailResponse)
async def get_dish(dish_id: int, db: Annotated[AsyncSession, Depends(get_db) ]):
    result = await db.execute(select(models.Dish).options(
        selectinload(models.Dish.reviews).selectinload(models.Review.reviewer), 
        selectinload(models.Dish.restaurant)
        )
        .where(models.Dish.id == dish_id))
    dish = result.scalars().first()
    if dish: 
        return dish
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dish content not found")

#user create review on speicific dish from specific restaurant. ---DONE
@router.post("/{dish_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    dish_id: int, 
    current_user: CurrentUser,
    review: ReviewCreate, 
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # check dish existed
    dish = await db.get(models.Dish, dish_id)
    if not dish:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dish not found" )

    # check if review already exist
    result = await db.execute(
        select(models.Review)
        .where(models.Review.user_id == current_user.id, models.Review.dish_id == dish_id)
    )
    existing_review = result.scalar_one_or_none()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this dish. You can edit your review instead."
        )

    # create review 
    new_review = models.Review(
        dish_id=dish_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment,
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    return new_review

#user creates favourite on specific dish  ------DONE
# Tapping heart icon from the main dish feed / dish details screen
@router.post("/{dish_id}/favourite", status_code=status.HTTP_200_OK)
async def toggle_dish_favourite(
    dish_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # 1. if dish exists
    dish = select(models.Dish).where(models.Dish.id == dish_id)
    dish_result = await db.execute(dish)
    if not dish_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dish not found")

    # 2. Check if already favorited
    fav = select(models.Favourite).where(
        models.Favourite.user_id == current_user.id,
        models.Favourite.dish_id == dish_id
    )
    result = await db.execute(fav)
    existing_favourite = result.scalar_one_or_none()

    # 3. Toggle logic
    if existing_favourite:
        await db.delete(existing_favourite)
        await db.commit()
        return {"is_favourite": False, "message": "Removed from favorites"}

    new_favourite = models.Favourite(user_id=current_user.id, dish_id=dish_id)
    db.add(new_favourite)
    await db.commit()
    return {"is_favourite": True, "message": "Added to favorites"}

# dishes compare - user can select 2 or 3 dishes to compare. 8/9/2026
@router.post("/compare-summary", response_model=CompareResponse, status_code=status.HTTP_200_OK)
async def compare_dishes_summary(payload: CompareRequest,db: Annotated[AsyncSession, Depends(get_db)],):
    # 1. Fetch the dishes, their parent restaurant coordinates, and review comments
    query = (select(models.Dish).where(models.Dish.id.in_(payload.dish_ids))
            .options(joinedload(models.Dish.restaurant),selectinload(models.Dish.reviews),) )
    result = await db.execute(query)
    dishes = result.scalars().unique().all()

    if len(dishes) < 2:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST,
        detail="At least 2 valid dishes are required for comparison.",)

    user_has_gps = payload.user_lat is not None and payload.user_lon is not None
    calc_lat = payload.user_lat if user_has_gps else settings.default_city_lat
    calc_lon = payload.user_lon if user_has_gps else settings.default_city_lon
    # 2. Extract metrics and calculate distance via user_lat & user_lon
    dish_summaries = []
    for d in dishes:
        rest = d.restaurant
        dist_m = None

        if rest and rest.lat is not None and rest.lon is not None:
            dist_m = calculate_distance_meters(calc_lat, calc_lon, rest.lat, rest.lon)

        # Format human-readable distance & walk time 
        if dist_m is None:
            distance_label = "Unknown"
            walk_label = "Unknown"
        elif user_has_gps and dist_m < 50:
            distance_label = "Inside or right at venue (<50m)"
            walk_label = "0 mins (You are already here)"
        elif user_has_gps:
            walk_mins = estimate_walk_minutes(dist_m)
            distance_label = f"{dist_m}m away"
            walk_label = f"{walk_mins} mins walk"
        else:
            # User GPS disabled: use CBD reference
            walk_mins = estimate_walk_minutes(dist_m)
            distance_label = f"{dist_m}m from {settings.default_city_name}"
            walk_label = f"{walk_mins} mins walk from {settings.default_city_name}"

        # Pull up to 5 non-empty text reviews
        review_comments = [r.comment for r in d.reviews if r.comment][:5]

        dish_summaries.append({
            "dish_name": d.name,
            "restaurant_name": rest.name if rest else "Unknown",
            "price": f"${d.price:.2f}",
            "rating": d.average_rating,
            "distance": distance_label,
            "walk_time": walk_label,
            "customer_reviews": review_comments
            or ["No text reviews written yet."],
        })

     # 3. Call AI Service and return variable for inspection
    ai_result = await ai_service.generate_dish_comparison(dish_summaries)
    return ai_result