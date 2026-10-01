import pytest
from config import settings
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from tests.conftest import (
     auth_header, 
     create_test_user, 
     login_user,
     db_session,
     create_test_restaurant,
     create_test_dish,
     create_search_dishes
     )
import models

MOCK_AI_RESULT = {
   "verdict": "Pad Thai is the better pick: cheaper, higher rated, and just as close. Green Curry is fine but costs more.",
   "trade_off_breakdown": [
       "Pad Thai is $2.50 cheaper",
       "Pad Thai has the higher rating (4.5 vs 3.0)",
   ],
   "best_value_pick": "Pad Thai ($12.50)",
   "best_taste_pick": "Pad Thai (4.5)",
}

def get_summaries(mock_ai) -> dict:
   summaries = {}
   for summary in mock_ai.call_args.args[0]:
       summaries[summary["dish_name"]] = summary
   return summaries

###############
# Get all dishes
###############
@pytest.mark.anyio
async def test_get_dishes_empty(client: AsyncClient):
    response = await client.get("/dishes")

    assert response.status_code == 200
    data = response.json()
    assert data["dishes"] == []
    assert data["totla"] == 0
    assert data["page"] == 1
    assert data["pages"] == 0

# Get dishes - success pagination 
@pytest.mark.anyio
async def test_get_dishes_pagination(client: AsyncClient, db_session: AsyncSession):
   restaurant = await create_test_restaurant(db_session)
   for i in range(5):
       await create_test_dish(db_session, name=f"Dish {i}", restaurant=restaurant)

   # all 5 fit on page 1, newest first 
   response = await client.get("/dishes")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["items"]) == 5
   assert data["page"] == 1
   assert data["pages"] == 1
   expected_names = ["Dish 4", "Dish 3", "Dish 2", "Dish 1", "Dish 0"]
   for i in range(5):
        assert data["items"][i]["dish_name"] == expected_names[i]

   # each item carries its restaurant 
   first = data["items"][0]
   assert first["restaurant_id"] == restaurant.id
   assert first["restaurant_name"] == "Test Restaurant"

   # size=2 -> 3 pages (2 + 2 + 1)
   response = await client.get("/dishes?size=2")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["items"]) == 2
   assert data["size"] == 2
   assert data["pages"] == 3

   response = await client.get("/dishes?page=2&size=2")
   assert response.status_code == 200
   data = response.json()
   assert data["page"] == 2
   assert len(data["items"]) == 2
   assert data["items"][0]["dish_name"] == "Dish 2"
   assert data["items"][1]["dish_name"] == "Dish 1"

   # last page holds the remaining 1 item
   response = await client.get("/dishes?page=3&size=2")
   assert response.status_code == 200
   data = response.json()
   assert len(data["items"]) == 1
   assert data["items"][0]["dish_name"] == "Dish 0"

# Get dishes - success multiple restaurants
@pytest.mark.anyio
async def test_get_dishes_multiple_restaurants(client: AsyncClient, db_session: AsyncSession):
   restaurant_a = await create_test_restaurant(db_session, name="Thai Place", address="1 Thai St")
   restaurant_b = await create_test_restaurant(db_session, name="Pizza Place", address="2 Pizza St")
   await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant_a)
   await create_test_dish(db_session, name="Margherita", restaurant=restaurant_b)

   response = await client.get("/dishes")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 2

   # newest first: Margherita was created last
   assert data["items"][0]["dish_name"] == "Margherita"
   assert data["items"][0]["restaurant_name"] == "Pizza Place"
   assert data["items"][0]["restaurant_address"] == "2 Pizza St"
   assert data["items"][0]["restaurant_id"] == restaurant_b.id

   assert data["items"][1]["dish_name"] == "Pad Thai"
   assert data["items"][1]["restaurant_name"] == "Thai Place"
   assert data["items"][1]["restaurant_address"] == "1 Thai St"
   assert data["items"][1]["restaurant_id"] == restaurant_a.id

# Get dishes - success: one dish returns every field 
@pytest.mark.anyio
async def test_get_dishes_response_fields(client: AsyncClient, db_session: AsyncSession):
   restaurant = await create_test_restaurant(db_session)
   dish = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)

   response = await client.get("/dishes")
   assert response.status_code == 200
   item = response.json()["items"][0]

   assert item["dish_id"] == dish.id
   assert item["dish_name"] == "Pad Thai"
   assert item["average_rating"] == 0.0
   assert item["restaurant_id"] == restaurant.id
   assert item["restaurant_name"] == "Test Restaurant"
   assert item["restaurant_address"] == "1 Test Street"
   assert item["lat"] == pytest.approx(-28.0)
   assert item["lon"] == pytest.approx(153.4)

@pytest.mark.anyio
async def test_get_dishes_page_out_of_range(client: AsyncClient, db_session: AsyncSession):
   await create_test_dish(db_session)

   response = await client.get("/dishes?page=99&size=2")
   assert response.status_code == 200
   data = response.json()
   assert data["items"] == []
   assert data["total"] == 1

@pytest.mark.anyio
async def test_get_dishes_invalid_pagination(client: AsyncClient):
   response = await client.get("/dishes?page=0")
   assert response.status_code == 422

   response = await client.get("/dishes?size=0")
   assert response.status_code == 422

   response = await client.get("/dishes?size=1000")
   assert response.status_code == 422
###############
# Search dishes
###############
# Search dishes - success: no filters
@pytest.mark.anyio
async def test_search_dishes_no_filters(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 4
   assert len(data["items"]) == 4
   assert data["items"][0]["dish_name"] == "Thai Iced Tea"
   assert data["items"][3]["dish_name"] == "Pad Thai"


# Search dishes - success: q matches part of the name, ignoring upper/lower case
@pytest.mark.anyio
async def test_search_dishes_by_name(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)
   
   response = await client.get("/dishes/search?q=thai")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 2
   assert data["items"][0]["dish_name"] == "Thai Iced Tea"
   assert data["items"][1]["dish_name"] == "Pad Thai"


# Search dishes - success: max_price 
@pytest.mark.anyio
async def test_search_dishes_max_price(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search?max_price=12") 
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 2
   assert data["items"][0]["dish_name"] == "Thai Iced Tea"
   assert data["items"][0]["price"] == 5.0
   assert data["items"][1]["dish_name"] == "Pad Thai"
   assert data["items"][1]["price"] == 12.0


# Search dishes - success: min_rating 
@pytest.mark.anyio
async def test_search_dishes_min_rating(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search?min_rating=4.5") 
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 2
   assert data["items"][0]["dish_name"] == "Margherita Pizza"
   assert data["items"][0]["average_rating"] == 5.0
   assert data["items"][1]["dish_name"] == "Pad Thai"

# Search dishes - success: menu_category
@pytest.mark.anyio
async def test_search_dishes_by_category(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search?menu_category=mains")  
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 2
   assert data["items"][0]["dish_name"] == "Green Curry"
   assert data["items"][0]["menu_category"] == "Mains"
   assert data["items"][1]["dish_name"] == "Pad Thai"
   assert data["items"][1]["menu_category"] == "Mains"

# Search dishes - success: several filters
@pytest.mark.anyio
async def test_search_dishes_combined_filters(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search?q=thai&max_price=12&min_rating=4")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 1
   assert len(data["items"]) == 1
   assert data["items"][0]["dish_name"] == "Pad Thai"
   assert data["items"][0]["price"] == 12.0
   assert data["items"][0]["average_rating"] == 4.5

# Search dishes - success: pagination works on filtered 
@pytest.mark.anyio
async def test_search_dishes_pagination_with_filter(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search?q=thai&size=1")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 2  
   assert data["pages"] == 2
   assert data["page"] == 1
   assert data["size"] == 1
   assert len(data["items"]) == 1
   assert data["items"][0]["dish_name"] == "Thai Iced Tea"

# Search dishes - edge case: no match returns 200 with an empty page
@pytest.mark.anyio
async def test_search_dishes_no_match(client: AsyncClient, db_session: AsyncSession):
   await create_search_dishes(db_session)

   response = await client.get("/dishes/search?q=sushi")
   assert response.status_code == 200
   data = response.json()
   assert data["items"] == []
   assert data["total"] == 0
   assert data["pages"] == 0

# Search dishes - bad input
@pytest.mark.anyio
async def test_search_dishes_invalid_params(client: AsyncClient):
   response = await client.get("/dishes/search?max_price=-1")
   assert response.status_code == 422
   response = await client.get("/dishes/search?min_rating=6")
   assert response.status_code == 422
   response = await client.get("/dishes/search?min_rating=-1")
   assert response.status_code == 422


###############
# get specfic dish detail
###############
@pytest.mark.anyio
async def test_get_dishes_not_found(client: AsyncClient):
    response = await client.get("dishes/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Dish content not found"


@pytest.mark.anyio
async def test_get_dish_success_no_reviews(client: AsyncClient, db_session: AsyncSession):
   restaurant = await create_test_restaurant(db_session)
   dish = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)

   response = await client.get(f"/dishes/{dish.id}")
   assert response.status_code == 200
   data = response.json()
   assert data["dish_id"] == dish.id
   assert data["dish_name"] == "Pad Thai"
   assert data["restaurant_name"] == "Test Restaurant"
   assert data["reviews"] == []

# Get dish - success: returns its reviews
@pytest.mark.anyio
async def test_get_dish_with_reviews(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   dish = await create_test_dish(db_session, name="Pad Thai")

   result = await db_session.execute(
       select(models.User).where(models.User.email == "test@example.com")
   )
   user = result.scalars().first()

   review = models.Review(user_id=user.id, dish_id=dish.id, rating=5, comment="Great dish")
   db_session.add(review)
   await db_session.commit()

   response = await client.get(f"/dishes/{dish.id}")
   assert response.status_code == 200
   data = response.json()
   assert len(data["reviews"]) == 1
   assert data["reviews"][0]["rating"] == 5
   assert data["reviews"][0]["comment"] == "Great dish"
   assert data["reviews"][0]["reviewer"]["username"] == "testuser"

# Get dish - bad input
@pytest.mark.anyio
async def test_get_dish_invalid_id(client: AsyncClient):
   response = await client.get("/dishes/abcdefg")
   assert response.status_code == 422

###############
# user create review on speicific dish 
###############
@pytest.mark.anyio
async def test_create_review_success(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session, name="Pad Thai")

   response = await client.post(
       f"/dishes/{dish.id}/reviews",
       json={"rating": 3, "comment": "This is user review comment"},
       headers=headers,
   )
   assert response.status_code == 201
   data = response.json()
   assert data["rating"] == 3
   assert data["comment"] == "This is user review comment"
   assert data["reviewer"]["username"] == "testuser"
   assert "id" in data
   assert "created_at" in data

   response = await client.get(f"/dishes/{dish.id}")
   reviews = response.json()["reviews"]
   assert len(reviews) == 1
   assert reviews[0]["comment"] == "This is user review comment"

@pytest.mark.anyio
async def test_create_review_unauthorized(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)
   response = await client.post(f"/dishes/{dish.id}/reviews",
       json={"rating": 3, "comment": "This is user review comment"},
   )
   assert response.status_code == 401


# Create review - fail not found
@pytest.mark.anyio
async def test_create_review_dish_not_found(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.post( "/dishes/9999/reviews",
       json={"rating": 3, "comment": "Ghost dish"},
       headers=headers,
   )
   assert response.status_code == 404
   assert response.json()["detail"] == "Dish not found"


# Create review - fail no duplicate review from same person
@pytest.mark.anyio
async def test_create_review_duplicate(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)
   dish = await create_test_dish(db_session)

   response = await client.post(f"/dishes/{dish.id}/reviews",
       json={"rating": 5, "comment": "First test review"},
       headers=headers,
   )
   assert response.status_code == 201

   response = await client.post( f"/dishes/{dish.id}/reviews",
       json={"rating": 1, "comment": "Second test review"},
       headers=headers,
   )
   assert response.status_code == 409
   assert response.json()["detail"] == "You have already reviewed this dish. You can edit your review instead."

   # only the first review exists
   response = await client.get(f"/dishes/{dish.id}")
   reviews = response.json()["reviews"]
   assert len(reviews) == 1
   assert reviews[0]["comment"] == "First test review"


# Create review - success, two users can each review the same dish
@pytest.mark.anyio
async def test_create_review_two_users_same_dish(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   response = await client.post(f"/dishes/{dish.id}/reviews", json={"rating": 5, "comment": "review from A"}, headers=headers_a)
   assert response.status_code == 201
   data_a = response.json()
   assert data_a["rating"] == 5
   assert data_a["comment"] == "review from A"
   assert data_a["reviewer"]["username"] == "testuser"

   response = await client.post(f"/dishes/{dish.id}/reviews", json={"rating": 2, "comment": "review from B"}, headers=headers_b)
   assert response.status_code == 201
   data_b = response.json()
   assert data_b["rating"] == 2
   assert data_b["comment"] == "review from B"
   assert data_b["reviewer"]["username"] == "user_b"

   response = await client.get(f"/dishes/{dish.id}")
   assert response.status_code == 200
   reviews = response.json()["reviews"]
   assert len(reviews) == 2

   by_username = {r["reviewer"]["username"]: r for r in reviews}
   assert by_username["testuser"]["rating"] == 5
   assert by_username["testuser"]["comment"] == "review from A"
   assert by_username["user_b"]["rating"] == 2
   assert by_username["user_b"]["comment"] == "review from B"

# Create review - bad input: a missing or out-of-range rating
@pytest.mark.anyio
async def test_create_review_invalid_rating(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)
   dish = await create_test_dish(db_session)

   response = await client.post(f"/dishes/{dish.id}/reviews", json={"rating": 6, "comment": "Too high"}, headers=headers)
   assert response.status_code == 422
   response = await client.post(f"/dishes/{dish.id}/reviews", json={"rating": 0, "comment": "Too low"}, headers=headers)
   assert response.status_code == 422

###############
# user creates favourite on specific dish 
###############
# success-- turns on toggle
@pytest.mark.anyio
async def test_toggle_favourite_on(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)
   dish = await create_test_dish(db_session, name="Pad Thai")

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["is_favourite"] is True
   assert data["message"] == "Added to favorites"

   response = await client.get("/users/me/favourites", headers=headers)
   favourites = response.json()
   assert len(favourites) == 1
   assert favourites[0]["dish_id"] == dish.id 
   assert favourites[0]["dish_name"] == "Pad Thai"

# Toggle favourite - success--second tap turns it OFF
@pytest.mark.anyio
async def test_toggle_favourite_off(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)
   dish = await create_test_dish(db_session)

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
   assert response.json()["is_favourite"] is True

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["is_favourite"] is False
   assert data["message"] == "Removed from favorites"

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.json() == []

# Toggle favourite - privacy -each user's toggle is independent, even on the same dish
@pytest.mark.anyio
async def test_toggle_favourite_two_users_same_dish(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)
   # User A turns it ON
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)
   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers_a)
   assert response.json()["is_favourite"] is True

   # User B turns it ON too
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)
   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers_b)
   assert response.json()["is_favourite"] is True

   # User B turns it OFF
   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers_b)
   assert response.json()["is_favourite"] is False

   # B's list is empty
   response = await client.get("/users/me/favourites", headers=headers_b)
   assert response.json() == []

   response = await client.get("/users/me/favourites", headers=headers_a)
   favourites = response.json()
   assert len(favourites) == 1
   assert favourites[0]["dish_id"] == dish.id

# Toggle favourite - fail: a dish that doesn't exist
@pytest.mark.anyio
async def test_toggle_favourite_dish_not_found(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.post("/dishes/9999/favourite", headers=headers)
   assert response.status_code == 404
   assert response.json()["detail"] == "Dish not found"

# Toggle favourite - bad input: a non-integer 
@pytest.mark.anyio
async def test_toggle_favourite_invalid_id(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.post("/dishes/abcdefg/favourite", headers=headers)
   assert response.status_code == 422

# Toggle favourite - unauthorized no token
@pytest.mark.anyio
async def test_toggle_favourite_unauthorized(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)
   response = await client.post(f"/dishes/{dish.id}/favourite")
   assert response.status_code == 401

###############
# user creates dishes compare
###############
# Compare - success
@pytest.mark.anyio
async def test_compare_summary_success(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   restaurant = await create_test_restaurant(db_session)  
   dish_1 = await create_test_dish(db_session, name="Pad Thai", price=12.5, average_rating=4.5, restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", price=15.0, average_rating=3.0, restaurant=restaurant)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock, return_value=MOCK_AI_RESULT) as mock_ai:
       response = await client.post(
           "/dishes/compare-summary",
           json={"dish_ids": [dish_1.id, dish_2.id], "user_lat": -27.0, "user_lon": 153.4},  # about 100km away
           headers=headers,
       )

   assert response.status_code == 200
   data = response.json()
   assert data["verdict"] == MOCK_AI_RESULT["verdict"]
   assert data["trade_off_breakdown"] == MOCK_AI_RESULT["trade_off_breakdown"]
   assert data["best_value_pick"] == "Pad Thai ($12.50)"
   assert data["best_taste_pick"] == "Pad Thai (4.5)"

   mock_ai.assert_awaited_once()
   summaries = get_summaries(mock_ai)
   assert len(summaries) == 2

   assert summaries["Pad Thai"]["restaurant_name"] == "Test Restaurant"
   assert summaries["Pad Thai"]["price"] == "$12.50"
   assert summaries["Pad Thai"]["rating"] == 4.5
   assert "m away" in summaries["Pad Thai"]["distance"]
   assert "mins walk" in summaries["Pad Thai"]["walk_time"]

   assert summaries["Green Curry"]["price"] == "$15.00"
   assert summaries["Green Curry"]["rating"] == 3.0
   assert "m away" in summaries["Green Curry"]["distance"]
   assert "mins walk" in summaries["Green Curry"]["walk_time"]

# Compare - unauthorized
@pytest.mark.anyio
async def test_compare_summary_unauthorized(client: AsyncClient, db_session: AsyncSession):
   dish_1 = await create_test_dish(db_session, name="Pad Thai")
   dish_2 = await create_test_dish(db_session, name="Green Curry")

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock) as mock_ai:
       response = await client.post("/dishes/compare-summary",
                                    json={"dish_ids": [dish_1.id, dish_2.id]},
       )
   assert response.status_code == 401
   mock_ai.assert_not_awaited()  

# Compare - success: user at the restaurant 
@pytest.mark.anyio
async def test_compare_summary_user_at_venue(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   restaurant = await create_test_restaurant(db_session) 
   dish_1 = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", restaurant=restaurant)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock, return_value=MOCK_AI_RESULT) as mock_ai:
       response = await client.post("/dishes/compare-summary",
           json={"dish_ids": [dish_1.id, dish_2.id], "user_lat": -28.0, "user_lon": 153.4},
           headers=headers,
       )

   assert response.status_code == 200
   summaries = get_summaries(mock_ai)
   assert summaries["Pad Thai"]["distance"] == "Inside or right at venue (<50m)"
   assert summaries["Pad Thai"]["walk_time"] == "0 mins (You are already here)"


# Compare - success: no GPS falls back to the default city 
@pytest.mark.anyio
async def test_compare_summary_without_gps(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   restaurant = await create_test_restaurant(db_session)
   dish_1 = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", restaurant=restaurant)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock, return_value=MOCK_AI_RESULT) as mock_ai:
       response = await client.post(
           "/dishes/compare-summary",
           json={"dish_ids": [dish_1.id, dish_2.id]},
           headers=headers,
       )

   assert response.status_code == 200
   summaries = get_summaries(mock_ai)
   assert f"from {settings.default_city_name}" in summaries["Pad Thai"]["distance"]
   assert f"from {settings.default_city_name}" in summaries["Pad Thai"]["walk_time"]


# Compare - edge case: a restaurant with no coordinatese
@pytest.mark.anyio
async def test_compare_summary_restaurant_without_coordinates(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   restaurant = models.Restaurant(name="Bare Restaurant", address=None, lat=None, lon=None)
   db_session.add(restaurant)
   await db_session.commit()
   await db_session.refresh(restaurant)

   dish_1 = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", restaurant=restaurant)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock, return_value=MOCK_AI_RESULT) as mock_ai:
       response = await client.post("/dishes/compare-summary",
           json={"dish_ids": [dish_1.id, dish_2.id], "user_lat": -28.0, "user_lon": 153.4},
           headers=headers,
       )

   assert response.status_code == 200
   summaries = get_summaries(mock_ai)
   assert summaries["Pad Thai"]["distance"] == "Unknown"
   assert summaries["Pad Thai"]["walk_time"] == "Unknown"


# Compare - success: review comments, a dish with none gets the placeholder
@pytest.mark.anyio
async def test_compare_summary_review_comments(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   result = await db_session.execute(
       select(models.User).where(models.User.email == "test@example.com")
   )
   user = result.scalars().first()

   restaurant = await create_test_restaurant(db_session)
   dish_1 = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", restaurant=restaurant)

   # Pad Thai has a written comment, Green Curry only has a rating with no comment
   db_session.add(models.Review(user_id=user.id, dish_id=dish_1.id, rating=5, comment="Great dish"))
   db_session.add(models.Review(user_id=user.id, dish_id=dish_2.id, rating=3, comment=None))
   await db_session.commit()

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock, return_value=MOCK_AI_RESULT) as mock_ai:
       response = await client.post("/dishes/compare-summary",
           json={"dish_ids": [dish_1.id, dish_2.id]},
           headers=headers,
       )

   assert response.status_code == 200
   summaries = get_summaries(mock_ai)
   assert summaries["Pad Thai"]["customer_reviews"] == ["Great dish"]
   assert summaries["Green Curry"]["customer_reviews"] == ["No text reviews written yet."]


# Compare - failure: one of the two ids doesn't exist
@pytest.mark.anyio
async def test_compare_summary_needs_two_valid_dishes(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session, name="Pad Thai")

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock) as mock_ai:
       response = await client.post("/dishes/compare-summary",
           json={"dish_ids": [dish.id, 9999]}, 
           headers=headers,
       )
   assert response.status_code == 400
   assert response.json()["detail"] == "At least 2 valid dishes are required for comparison."
   mock_ai.assert_not_awaited()

# Compare - failure: ids that match no dishes 
@pytest.mark.anyio
async def test_compare_summary_no_dishes_found(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock) as mock_ai:
       response = await client.post( "/dishes/compare-summary",
           json={"dish_ids": [99988, 99999]}, headers=headers,
       )

   assert response.status_code == 400
   assert response.json()["detail"] == "At least 2 valid dishes are required for comparison."
   mock_ai.assert_not_awaited()


# Compare - bad input: too few, too many, or missing dish_ids is rejected with 422 and the AI is never called
@pytest.mark.anyio
async def test_compare_summary_invalid_dish_ids(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock) as mock_ai:
       # missing field
       response = await client.post("/dishes/compare-summary", json={}, headers=headers)
       assert response.status_code == 422
       # min_length=2: one id 
       response = await client.post("/dishes/compare-summary", json={"dish_ids": [1]}, headers=headers)
       assert response.status_code == 422
       # max_length=5: six ids 
       response = await client.post("/dishes/compare-summary", json={"dish_ids": [1, 2, 3, 4, 5, 6]}, headers=headers)
       assert response.status_code == 422
   mock_ai.assert_not_awaited()


# Compare - bad input: GPS values outside the valid range 
@pytest.mark.anyio
async def test_compare_summary_invalid_gps(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   with patch("routers.dishes.ai_service.generate_dish_comparison", new_callable=AsyncMock) as mock_ai:
       response = await client.post( "/dishes/compare-summary",
           json={"dish_ids": [1, 2], "user_lat": 91.0, "user_lon": 153.4}, 
           headers=headers,
       )
       assert response.status_code == 422

       response = await client.post("/dishes/compare-summary",
           json={"dish_ids": [1, 2], "user_lat": -28.0, "user_lon": 181.0},
           headers=headers,
       )
       assert response.status_code == 422

   mock_ai.assert_not_awaited()