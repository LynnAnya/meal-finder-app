from __future__ import annotations
from pydantic import Field, BaseModel, ConfigDict, EmailStr, AliasPath
from datetime import datetime, time

######################
# 1. Dish activities
######################
class RestaurantBase(BaseModel):
    id: int
    name: str
    lat: float | None
    lon: float | None
    venue_type: str | None
    cuisine: str | None
    opening_hours: str | None
    
class DishBase(BaseModel): 
    price: float = Field(gt=0)
    menu_category:str = Field(min_length=2, max_length=50,)

#admin create dish - for now 
class DishCreate(DishBase):  
    name: str = Field(validation_alias="dish_name", min_length=2, max_length=50)

#admin update dish - for now
class DishUpdate(BaseModel):
    name: str | None = Field(default=None, validation_alias="dish_name", min_length=2, max_length=50)
    price: float | None = Field(default=None, gt=0)
    menu_category: str | None = Field(default=None, min_length=2, max_length=50)
    

# overall dishes 
class DishResponse(DishBase): 
    model_config = ConfigDict(from_attributes=True)
    
    #add photo file path later
    dish_id: int = Field(validation_alias="id")
    dish_name: str = Field(validation_alias="name")
    average_rating: float
    restaurant_id: int = Field(validation_alias=AliasPath("restaurant", "id"))
    restaurant_name: str = Field(validation_alias=AliasPath("restaurant", "name"))
    restaurant_address: str | None = Field(validation_alias=AliasPath("restaurant", "address"))
    lat: float | None = Field(default=None, validation_alias=AliasPath("restaurant", "lat"))
    lon: float | None = Field(default=None, validation_alias=AliasPath("restaurant", "lon"))
# specific dish 
class DishDetailResponse(DishResponse):
    reviews: list[ReviewResponse] = Field(default=[])
    restaurant: RestaurantBase

# user search bar
class DishSearch(BaseModel):
    search: str | None = Field( default=None)
    rating: float | None = Field(default=None, ge=1.0, le=5.0, )
    max_price: float | None = Field(default=None,  gt=0 )

######################
# reviews dish 
######################
class ReviewBase(BaseModel):
    #dish and restaurant (user already clicked on that -- need or not )
    
    rating: int = Field(default=5, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

class ReviewCreate(ReviewBase): 
   pass
class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

class ReviewResponse(ReviewBase):
    model_config = ConfigDict(from_attributes=True)
    
    review_id: int = Field(validation_alias="id")
    created_at: datetime 
    reviewer: UserPublic


######################
# compare
######################
class CompareRequest(BaseModel):
    dish_ids: list[int] = Field(..., min_length=2, max_length=5)
    user_lat: float | None  = Field(default=None, ge=-90.0, le=90.0)
    user_lon: float | None =  Field(default=None, ge=-180.0, le=180.0)

class CompareResponse(BaseModel):
    verdict: str = Field(description="2 sentences (35-50 words). Decisive summary to pick and why.")
    trade_off_breakdown: list[str] = Field(description="2-3 bullet points highlighting key differences in price, distance, or taste.")
    best_value_pick: str = Field(description="Winning dish name with price e.g., 'Pad Thai Boran ($19.00)'")
    best_taste_pick: str = Field(description="Winning dish name with star rating, e.g., 'Massaman Beef (4.8)'")


######################
# user personal validation 
######################
class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)
   #image_file: str | None
class UserCreate(UserBase):
    password:str = Field(min_length=8)

class UserPublic(BaseModel):   #  what public can see, change from UserResponse -- update in api too!
    model_config = ConfigDict(from_attributes=True)

    username: str
    image_file: str | None
    image_path: str

class UserPrivate(UserPublic):
    email: EmailStr

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=120)
   
class Token(BaseModel): 
    access_token: str
    token_type: str

