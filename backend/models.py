from __future__ import annotations
from datetime import datetime, UTC, time
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Time,Float, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base 

#create user table and its column and relationship to other tables  
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    image_file: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None,)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    
    reviews: Mapped[list[Review]] = relationship(back_populates="reviewer", cascade="all, delete-orphan")
    favourite_dishes: Mapped[list["Dish"]] = relationship(secondary="favourites",back_populates="favourited_by_users")
    
    @property
    def image_path(self) -> str:
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"
        return "/static/profile_pics/default.jpg"

# user can create their review on any dishes and can see other's review    
class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
    UniqueConstraint("user_id", "dish_id", name="uq_user_dish_review"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rating: Mapped[int] = mapped_column(nullable=False, default=5)
    # Storing tags as a simple comma-separated string (e.g., "spicy,big_portion,good_value")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    #FK
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), index=True, nullable=False)

    reviewer: Mapped[User] = relationship(back_populates="reviews")
    dish: Mapped[Dish] = relationship(back_populates="reviews")

class Dish(Base): 
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    menu_category: Mapped[str] = mapped_column(String(50), index=True)
    average_rating: Mapped[float] = mapped_column(Float, default=0.0)
    
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), index=True, nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="dishes")
    reviews: Mapped[list[Review]] = relationship(back_populates="dish", cascade="all, delete-orphan")
    favourited_by_users: Mapped[list["User"]] = relationship(secondary="favourites",back_populates="favourite_dishes")

class Restaurant(Base):
    __tablename__ = "restaurants"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    venue_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cuisine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # 🔄 RELATIONSHIP: 1 Restaurant -> Many Dishes
    dishes: Mapped[list[Dish]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")

class Favourite(Base):
    __tablename__ = "favourites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    dish: Mapped["Dish"] = relationship("Dish", overlaps="favourite_dishes,favourited_by_users")
    user: Mapped["User"] = relationship("User", overlaps="favourite_dishes,favourited_by_users")

    __table_args__ = ( UniqueConstraint("user_id", "dish_id", name="uq_user_dish_favourite"),)