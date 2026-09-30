from datetime import UTC, datetime, timedelta
from botocore.exceptions import ClientError
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
import pytest
from httpx import AsyncClient
import models
from config import settings
from tests.conftest import (
    auth_header, 
    create_test_user, 
    login_user, 
    create_test_dish, 
    create_test_restaurant,
    get_reset_token)


###############
# user get reviews 
##############
@pytest.mark.anyio
async def test_get_user_reviews_pagination(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   for i in range(5):
       response = await client.post(
           "/users/me/reviews",
           json={"rating": 5, "comment": "Testing comment created"},  
           headers=headers,
       )
       assert response.status_code == 201

   response = await client.get("/users/me/reviews", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["items"]) == 5
   assert data["page"] == 1
   assert data["pages"] == 1

   response = await client.get("/users/me/reviews?size=2", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["items"]) == 2
   assert data["size"] == 2
   assert data["pages"] == 3

   response = await client.get("/users/me/reviews?page=2&size=2", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["items"]) == 2
   assert data["page"] == 2
   assert data["size"] == 2


@pytest.mark.anyio
async def test_user_only_sees_own_reviews(client: AsyncClient):
   # User A
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   for i in range(3):
       response = await client.post("/users/me/reviews", json={"rating": 5, "comment": "Testing comment created"}, headers=headers_a)
       assert response.status_code == 201

   # User B 
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   for i in range(2):
       response = await client.post("/users/me/reviews", json={"rating": 4, "comment": "Testing comment created user b"}, headers=headers_b)
       assert response.status_code == 201

   response_a = await client.get("/users/me/reviews", headers=headers_a)
   response_b = await client.get("/users/me/reviews", headers=headers_b)
   assert response_a.status_code == 200
   assert response_b.status_code == 200
   data_a = response_a.json()
   data_b = response_b.json()

   assert data_a["total"] == 3
   assert data_b["total"] == 2
   assert len(data_a["items"]) == 3
   assert len(data_b["items"]) == 2
   
    # User A: every review is A's 
   for review in data_a["items"]:
       assert review["rating"] == 5
       assert review["comment"] == "Testing comment created"
       assert review["reviewer"]["username"] == "testuser"

   # User B: every review is B's
   for review in data_b["items"]:
       assert review["rating"] == 4
       assert review["comment"] == "Testing comment created user b"
       assert review["reviewer"]["username"] == "user_b"

   # No review id shows up in both lists
   ids_a = {review["id"] for review in data_a["items"]}
   ids_b = {review["id"] for review in data_b["items"]}
   assert ids_a.isdisjoint(ids_b)

###############
# user get favourite
##############
# Success: a new user with no favourites gets an empty list not an error
@pytest.mark.anyio
async def test_get_favourites_empty(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   assert response.json() == []

# Success:  favourited dishes from user come back with all the right data
@pytest.mark.anyio
async def test_get_favourites_success(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   restaurant = await create_test_restaurant(db_session)
   dish_1 = await create_test_dish(db_session, name="Pad Thai", price=12.5, menu_category="Main", restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", price=15.0, menu_category="Curry", restaurant=restaurant)
   dish_3 = await create_test_dish(db_session, name="Not Favourited", restaurant=restaurant)

   for dish in (dish_1, dish_2):
       response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
       assert response.status_code == 200

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert len(data) == 2
   assert {d["dish_id"] for d in data} == {dish_1.id, dish_2.id}

   by_id = {d["dish_id"]: d for d in data}
   d1 = by_id[dish_1.id]
   assert d1["dish_name"] == "Pad Thai"
   assert d1["average_rating"] == 0.0
   assert d1["restaurant_id"] == restaurant.id
   assert d1["restaurant_name"] == "Test Restaurant"
   assert d1["restaurant_address"] == "1 Test Street"
   assert d1["lat"] == pytest.approx(-28.0)
   assert d1["lon"] == pytest.approx(153.4)

   d2 = by_id[dish_2.id]
   assert d2["dish_name"] == "Green Curry"
   assert d2["average_rating"] == 0.0
   assert d2["restaurant_id"] == restaurant.id
   assert d2["restaurant_name"] == "Test Restaurant"
   assert d2["restaurant_address"] == "1 Test Street"
   assert d2["lat"] == pytest.approx(-28.0)
   assert d2["lon"] == pytest.approx(153.4)

   assert dish_3.id not in by_id

@pytest.mark.anyio
async def test_user_only_sees_own_favourites(client: AsyncClient, db_session: AsyncSession):
   dish_a = await create_test_dish(db_session, name="Pad Thai")
   dish_b = await create_test_dish(db_session, name="Green Curry")

   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)
   response = await client.post(f"/dishes/{dish_a.id}/favourite", headers=headers_a)
   assert response.status_code == 200

   #user b
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   response = await client.post(f"/dishes/{dish_b.id}/favourite", headers=headers_b)
   assert response.status_code == 200

   response_a = await client.get("/users/me/favourites", headers=headers_a)
   response_b = await client.get("/users/me/favourites", headers=headers_b)
   assert response_a.status_code == 200
   assert response_b.status_code == 200

   # each user sees only their own dish
   assert [d["dish_id"] for d in response_a.json()] == [dish_a.id]
   assert [d["dish_id"] for d in response_b.json()] == [dish_b.id]

# Failure: no token means, rejects the request
@pytest.mark.anyio
async def test_get_favourites_unauthorized(client: AsyncClient):
   response = await client.get("/users/me/favourites")
   assert response.status_code == 401  

# Failure: a garbage token 
@pytest.mark.anyio
async def test_get_favourites_invalid_token(client: AsyncClient):
   headers = auth_header("not-a-real-token")
   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 401  

###############
# user delete favourite
##############
# delete  favourite dishes -success 
@pytest.mark.anyio
async def test_remove_favourite_success(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session, name="Pad Thai")

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
   assert response.status_code == 200

   response = await client.delete(f"/users/me/favourites/{dish.id}", headers=headers)
   assert response.status_code == 204
   assert response.text == ""

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   assert response.json() == []

# removing one dish leaves the other favourites untouched - success
@pytest.mark.anyio
async def test_remove_favourite_keeps_others(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   restaurant = await create_test_restaurant(db_session)
   dish_1 = await create_test_dish(db_session, name="Pad Thai", restaurant=restaurant)
   dish_2 = await create_test_dish(db_session, name="Green Curry", restaurant=restaurant)

   for dish in (dish_1, dish_2):
       response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
       assert response.status_code == 200

   response = await client.delete(f"/users/me/favourites/{dish_1.id}", headers=headers)
   assert response.status_code == 204

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   assert [d["dish_id"] for d in response.json()] == [dish_2.id]

# a dish that exists but was never favourited 
@pytest.mark.anyio
async def test_remove_favourite_not_in_favourites(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session)

   response = await client.delete(f"/users/me/favourites/{dish.id}", headers=headers)
   assert response.status_code == 404
   assert response.json()["detail"] == "Item not in your favourites list"

# bad input: a non-integer dish id is rejected with 422 before your code runs
@pytest.mark.anyio
async def test_remove_favourite_invalid_id(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.delete("/users/me/favourites/abc", headers=headers)
   assert response.status_code == 422

# deleting the same favourite twice, the second returns 404
@pytest.mark.anyio
async def test_remove_favourite_twice(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session)

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers)
   assert response.status_code == 200

   response = await client.delete(f"/users/me/favourites/{dish.id}", headers=headers)
   assert response.status_code == 204

   response = await client.delete(f"/users/me/favourites/{dish.id}", headers=headers)
   assert response.status_code == 404

# privacy: both users favourite the same dish, B removing theirs leaves A's intact
@pytest.mark.anyio
async def test_remove_favourite_same_dish_two_users(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers_a)
   assert response.status_code == 200

   # User B 
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   response = await client.post(f"/dishes/{dish.id}/favourite", headers=headers_b)
   assert response.status_code == 200

   # User B removes their favourite
   response = await client.delete(f"/users/me/favourites/{dish.id}", headers=headers_b)
   assert response.status_code == 204
   response = await client.get("/users/me/favourites", headers=headers_b)
   assert response.json() == []

   # A's favourite is still there
   response = await client.get("/users/me/favourites", headers=headers_a)
   favourites = response.json()
   assert len(favourites) == 1
   assert favourites[0]["dish_id"] == dish.id


# unauthorized 
@pytest.mark.anyio
async def test_remove_favourite_unauthorized(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)

   response = await client.delete(f"/users/me/favourites/{dish.id}")
   assert response.status_code == 401  


# unauthorized: a garbage token 
@pytest.mark.anyio
async def test_remove_favourite_invalid_token(client: AsyncClient, db_session: AsyncSession):
   dish = await create_test_dish(db_session)
   headers = auth_header("not-a-real-token")

   response = await client.delete(f"/users/me/favourites/{dish.id}", headers=headers)
   assert response.status_code == 401

###############
# create new user
##############
@pytest.mark.anyio
async def test_create_user_validation_error(client: AsyncClient):
    response = await client.post("/users", json={"username": "testuser"},)
    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.text

@pytest.mark.anyio
async def test_create_user_duplicate_email(client: AsyncClient):
    await create_test_user(client)
    response = await client.post("/users", json={"username": "different_user","email": "test@example.com", "password": "password111"},)

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.anyio
async def test_create_user_success(client: AsyncClient):
    response = await client.post("/users", json={
        "username": "newuser", "email": "newuser@example.com", "password": "securepwd111", })

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "image_path" in data
    assert "password" not in data
    assert "password_hash" not in data

###############
# user login 
##############
# Login - success
@pytest.mark.anyio
async def test_login_success(client: AsyncClient):
   await create_test_user(client)

   response = await client.post(
       "/users/token",  # adjust to your real prefix
       data={"username": "test@example.com", "password": "testpwd12345"},
   )
   assert response.status_code == 200
   data = response.json()
   assert data["token_type"] == "bearer"
   assert data["access_token"] 

   headers = auth_header(data["access_token"])
   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200

# failure: wrong password -- unauthorized
@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient):
   await create_test_user(client)

   response = await client.post("/users/token",
       data={"username": "test@example.com", "password": "wrong-password"},
   )
   assert response.status_code == 401

#  failure: an email that doesn't exist
@pytest.mark.anyio
async def test_login_unknown_email(client: AsyncClient):
   response = await client.post( "/users/token",
       data={"username": "nobody@example.com", "password": "testpwd12345"},
   )
   assert response.status_code == 401

# Login - bad input: missing password
@pytest.mark.anyio
async def test_login_missing_fields(client: AsyncClient):
   response = await client.post("/users/token", data={"username": "test@example.com"})
   assert response.status_code == 422

###############
# get user profile
##############
@pytest.mark.anyio
async def test_get_me_success(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.get("/users/me", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["username"] == "testuser"
   assert data["email"] == "test@example.com"
   assert "password" not in data
   assert "password_hash" not in data

# privacy: each user gets their own profile from the same URL
@pytest.mark.anyio
async def test_get_me_returns_own_user(client: AsyncClient):
   # User A
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   # User B
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   response_a = await client.get("/users/me", headers=headers_a)
   response_b = await client.get("/users/me", headers=headers_b)
   assert response_a.status_code == 200
   assert response_b.status_code == 200
   assert response_a.json()["username"] == "testuser"
   assert response_b.json()["username"] == "user_b"

# unauthorized: no token 
@pytest.mark.anyio
async def test_get_me_unauthorized(client: AsyncClient):
   response = await client.get("/users/me")
   assert response.status_code == 401 

###############
# password forgot
##############
@pytest.mark.anyio
async def test_forgot_password_sends_email_success(client: AsyncClient):
    await create_test_user(client)

    with patch("routers.users.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        response = await client.post("/users/forgot_password", json={"email": "test@example.com"},)

    assert response.status_code == 202
    mock_send.assert_awaited_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == "test@example.com"
    assert call_kwargs["username"] == "testuser"
    assert "token" in call_kwargs

# Forgot password - failure: unknown email 
@pytest.mark.anyio
async def test_forgot_password_unknown_email(client: AsyncClient):
    await create_test_user(client)

    with patch("routers.users.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        response = await client.post("/users/forgot_password", json={"email": "wrong@example.com"},)

    assert response.status_code == 202  
    mock_send.assert_not_awaited()      

# Forgot password - bad input: invalid email format 
@pytest.mark.anyio
async def test_forgot_password_invalid_email_format(client: AsyncClient):
    with patch("routers.users.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        response = await client.post("/users/forgot_password", json={"email": "not-an-email"},)

    assert response.status_code == 422
    mock_send.assert_not_awaited()


# Forgot password - bad input: missing email field 
@pytest.mark.anyio
async def test_forgot_password_missing_email(client: AsyncClient):
    with patch("routers.users.send_password_reset_email", new_callable=AsyncMock) as mock_send:
        response = await client.post("/users/forgot_password", json={},)

    assert response.status_code == 422
    mock_send.assert_not_awaited()

###############
# password reset.  TODO: check each ! 
###############

# reset-pwd success 


# reset-pwd failed

# Reset password - success: valid token 
@pytest.mark.anyio
async def test_reset_password_success(client: AsyncClient):
    await create_test_user(client)
    reset_token = await get_reset_token(client)

    response = await client.post( "/users/reset-password",
        json={"token": reset_token, "new_password": "new_password_12345"},
    )
    assert response.status_code == 200

    # old password no longer works
    response = await client.post( "/users/token",
        data={"username": "test@example.com", "password": "testpwd12345"},
    )
    assert response.status_code == 401

    # new password works
    response = await client.post( "/users/token",
        data={"username": "test@example.com", "password": "new_password_12345"},
    )
    assert response.status_code == 200


# Reset password - failure: a made-up token 
@pytest.mark.anyio
async def test_reset_password_invalid_token(client: AsyncClient):
    response = await client.post("/users/reset-password",
        json={"token": "not-a-real-token", "new_password": "new_password_12345"},
    )
    assert response.status_code == 400

# Reset password - failure: an expired token is rejected, password stays the same
async def test_reset_password_expired_token(client: AsyncClient, db_session: AsyncSession):
    await create_test_user(client)
    reset_token = await get_reset_token(client)

    # push the token's expiry into the past
    await db_session.execute(
        update(models.PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    await db_session.commit()

    response = await client.post( "/users/reset-password",
        json={"token": reset_token, "new_password": "new_password_12345"},
    )
    assert response.status_code == 400

    # the expired token was deleted, so trying it again now -invalid
    response = await client.post("/users/reset-password",
        json={"token": reset_token, "new_password": "new_password_12345"},
    )
    assert response.status_code == 400

    # the old password still works
    response = await client.post("/users/token",
        data={"username": "test@example.com", "password": "testpwd12345"},
    )
    assert response.status_code == 200


# Reset password - failure: a token can only be used once
@pytest.mark.anyio
async def test_reset_password_token_single_use(client: AsyncClient):
    await create_test_user(client)
    reset_token = await get_reset_token(client)

    response = await client.post("/users/reset-password",
        json={"token": reset_token, "new_password": "new_password_12345"},
    )
    assert response.status_code == 200

    # same token again: it was deleted after the first use
    response = await client.post("/users/reset-password",
        json={"token": reset_token, "new_password": "another_password_678"},
    )
    assert response.status_code == 400

# Reset password - bad input: missing fields
@pytest.mark.anyio
async def test_reset_password_missing_fields(client: AsyncClient):
    response = await client.post("/users/reset-password", json={"token": "abc"})
    assert response.status_code == 422
    response = await client.post("/users/reset-password", json={"new_password": "new_password_12345"})
    assert response.status_code == 422

###############
# logined user changes password
##############
# Change password - success 
@pytest.mark.anyio
async def test_change_password_success(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)
   reset_token = await get_reset_token(client)

   response = await client.patch("/users/me/password",
       json={"current_password": "testpwd12345", "new_password": "new_password_12345"},
       headers=headers,
   )
   assert response.status_code == 200
   assert response.json()["message"] == "Password has been changed successfully."

   # old password no longer works
   response = await client.post("/users/token",
       data={"username": "test@example.com", "password": "testpwd12345"},
   )
   assert response.status_code == 401

   # new password works
   response = await client.post( "/users/token",
       data={"username": "test@example.com", "password": "new_password_12345"},
   )
   assert response.status_code == 200

   # the old email link no longer works (the reset token row was deleted)
   response = await client.post("/users/reset-password",
       json={"token": reset_token, "new_password": "hacker_password_678"},
   )
   assert response.status_code == 400

# Change password - fail: wrong current password is rejected
@pytest.mark.anyio
async def test_change_password_wrong_current_password(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch( "/users/me/password",
       json={"current_password": "wrong-password", "new_password": "new_password_12345"},
       headers=headers,
   )
   assert response.status_code == 400
   assert response.json()["detail"] == "Current password is incorrect."

   # the old password still works
   response = await client.post( "/users/token",
       data={"username": "test@example.com", "password": "testpwd12345"},
   )
   assert response.status_code == 200


# Change password - bad input
@pytest.mark.anyio
async def test_change_password_missing_fields(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch( "/users/me/password",
       json={"current_password": "testpwd12345"},
       headers=headers,
   )
   assert response.status_code == 422

# Change password - unauthorized
@pytest.mark.anyio
async def test_change_password_unauthorized(client: AsyncClient):
   response = await client.patch( "/users/me/password",
       json={"current_password": "testpwd12345", "new_password": "new_password_12345"},
   )
   assert response.status_code == 401  

# hange password - not valid format too short pwd
@pytest.mark.anyio
async def test_change_password_new_password_too_short(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/users/me/password",
       json={"current_password": "testpwd12345", "new_password": "short"},
       headers=headers,
   )
   assert response.status_code == 422
   assert "new_password" in response.text

###############
# user update profile
##############
# success: changing only the username 
@pytest.mark.anyio
async def test_update_username_success(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/users/me", json={"username": "new_username"}, headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["username"] == "new_username"
   assert data["email"] == "test@example.com" 

   # the change was saved: reading it back shows the new username
   response = await client.get("/users/me", headers=headers)
   assert response.json()["username"] == "new_username"

# Update account - success: changing only the email works, and it is saved in lowercase
@pytest.mark.anyio
async def test_update_email_success_lowercased(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/users/me", json={"email": "New.Email@Example.com"}, headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert data["email"] == "new.email@example.com"  # your code lowercases it
   assert data["username"] == "testuser"            # not sent, so unchanged

   response = await client.post("/users/token", data={"username": "new.email@example.com", "password": "testpwd12345"})
   assert response.status_code == 200

# Update account - success: changing both username and email in one request
@pytest.mark.anyio
async def test_update_username_and_email(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/users/me",
       json={"username": "new_username", "email": "new@example.com"},
       headers=headers,
   )
   assert response.status_code == 200
   data = response.json()
   assert data["username"] == "new_username"
   assert data["email"] == "new@example.com"


# Update account - success: sending your own current username, same name, different case
@pytest.mark.anyio
async def test_update_own_username_is_not_duplicate(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/users/me", json={"username": "TestUser"}, headers=headers)  
   assert response.status_code == 200


# Update account - failure: username taken by another user
@pytest.mark.anyio
async def test_update_username_already_exists(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")

   response = await client.patch("/users/me", json={"username": "USER_B"}, headers=headers)  # case-insensitive check
   assert response.status_code == 400

   # my username is unchanged
   response = await client.get("/users/me", headers=headers)
   assert response.json()["username"] == "testuser"


# Update account - failure: email taken by another user 
@pytest.mark.anyio
async def test_update_email_already_registered(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")

   response = await client.patch("/users/me", json={"email": "B@Test.com"}, headers=headers)  # case-insensitive check
   assert response.status_code == 400

   # my email is unchanged
   response = await client.get("/users/me", headers=headers)
   assert response.json()["email"] == "test@example.com"


# Update account - bad input: invalid email format 
@pytest.mark.anyio
async def test_update_invalid_email_format(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/users/me", json={"email": "not-an-email"}, headers=headers)
   assert response.status_code == 422
   assert "email" in response.text

# Update account - unauthorized: no token 
@pytest.mark.anyio
async def test_update_account_unauthorized(client: AsyncClient):
   response = await client.patch("/users/me", json={"username": "new_username"})
   assert response.status_code == 401  

###############
# user deletes account
##############
# Delete account - success
@pytest.mark.anyio
async def test_delete_account_success(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.delete("/users/me", headers=headers)
   assert response.status_code == 204
   assert response.text == "" 

   # login no longer works: the account is gone
   response = await client.post( "/users/token",
       data={"username": "test@example.com", "password": "testpwd12345"},
   )
   assert response.status_code == 401

   response = await client.get("/users/me", headers=headers)
   assert response.status_code == 401  


# Delete account - privacy: deleting my account leaves other users untouched
@pytest.mark.anyio
async def test_delete_account_does_not_affect_other_users(client: AsyncClient):
   # User A
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   # User B
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   # A deletes their own account
   response = await client.delete("/users/me", headers=headers_a)
   assert response.status_code == 204

   # B is still there
   response = await client.get("/users/me", headers=headers_b)
   assert response.status_code == 200
   assert response.json()["username"] == "user_b"
   assert response.json()["email"] == "b@test.com"

# Delete account - success: the profile image cleanup runs only when the user has an image
@pytest.mark.anyio
async def test_delete_account_removes_profile_image(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   # give the user a profile image (adjust the column value to whatever your app stores)
   await db_session.execute(
       update(models.User).where(models.User.email == "test@example.com").values(image_file="avatar.jpg")
   )
   await db_session.commit()

   with patch("routers.users.delete_profile_image", new_callable=AsyncMock) as mock_delete:
       response = await client.delete("/users/me", headers=headers)

   assert response.status_code == 204
   mock_delete.assert_awaited_once_with("avatar.jpg")

# Delete account - unauthorized: no token 
@pytest.mark.anyio
async def test_delete_account_unauthorized(client: AsyncClient):
   response = await client.delete("/users/me")
   assert response.status_code == 401  

###########################
# user uploads profile picture 
##########################
@pytest.mark.anyio
async def test_upload_profile_picture(client: AsyncClient, mocked_aws):
    user = await create_test_user(client)
    token = await login_user(client)

    test_image_path = Path(__file__).parent / "test_profile_image.jpg"
    image_bytes = test_image_path.read_bytes()

    response = await client.patch(
        f"/users/me/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
        headers= auth_header(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["image_file"] is not None
    assert data["image_file"].endswith(".jpg")
    assert "s3" in data["image_path"]

    s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
    assert "Contents" in s3_objects
    assert len(s3_objects["Contents"]) == 1
    assert s3_objects["Contents"][0]["Key"].endswith(data["image_file"])

# Upload picture - failure: file over the size limit
@pytest.mark.anyio
async def test_upload_picture_too_large(client: AsyncClient, mocked_aws):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   limit = settings.max_upload_size_bytes          
   too_big = b"0" * (limit + 1)    
   response = await client.patch("/users/me/picture",
        files={"file": ("big.jpg", BytesIO(too_big), "image/jpeg")},
        headers=headers,
    )

   assert response.status_code == 400
   s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
   assert "Contents" not in s3_objects

# Upload picture - failure: a file that is not a real image is rejected with 400 and nothing is stored
@pytest.mark.anyio
async def test_upload_picture_invalid_image(client: AsyncClient, mocked_aws):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    # named .jpg and labelled image/jpeg, but the bytes are just text
    response = await client.patch(
        "/users/me/picture",
        files={"file": ("fake.jpg", BytesIO(b"this is not an image"), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 400
    s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
    assert "Contents" not in s3_objects

# Upload picture - failure: S3 upload error, the user's image is unchanged
@pytest.mark.anyio
async def test_upload_picture_s3_failure(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    image_bytes = (Path(__file__).parent / "test_profile_image.jpg").read_bytes()

    response = await client.get("/users/me", headers=headers)
    image_before = response.json()["image_file"]

    # make the S3 upload blow up the way a real outage would
    fake_error = ClientError({"Error": {"Code": "500", "Message": "boom"}}, "PutObject")
    with patch("routers.users.upload_profile_image", new_callable=AsyncMock, side_effect=fake_error):
        response = await client.patch( "/users/me/picture",
            files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
            headers=headers,
        )
    assert response.status_code == 500
    response = await client.get("/users/me", headers=headers)
    assert response.json()["image_file"] == image_before

# Upload picture - bad input: request with no file is rejected with 422 before your code runs
@pytest.mark.anyio
async def test_upload_picture_missing_file(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.patch("/users/me/picture", headers=headers)
    assert response.status_code == 422

# Upload picture - unauthorized
@pytest.mark.anyio
async def test_upload_picture_unauthorized(client: AsyncClient):
    image_bytes = (Path(__file__).parent / "test_profile_image.jpg").read_bytes()

    response = await client.patch( "/users/me/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
    )
    assert response.status_code == 401  

###########################
# user deletes profile picture 
##########################
# Delete picture - success
@pytest.mark.anyio
async def test_delete_picture_success(client: AsyncClient, mocked_aws):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   image_bytes = (Path(__file__).parent / "test_profile_image.jpg").read_bytes()
   response = await client.patch( "/users/me/picture",
       files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
       headers=headers,
   )
   assert response.status_code == 200
   assert response.json()["image_file"] is not None 

   response = await client.delete("/users/me/picture", headers=headers)
   assert response.status_code == 200
   assert response.json()["image_file"] is None

   response = await client.get("/users/me", headers=headers)
   assert response.json()["image_file"] is None

   s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
   assert "Contents" not in s3_objects

# Delete picture - failure: user with no picture 
@pytest.mark.anyio
async def test_delete_picture_no_picture(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.delete("/users/me/picture", headers=headers)
   assert response.status_code == 403

# Delete picture - failure: deleting twice, the second call is rejected
@pytest.mark.anyio
async def test_delete_picture_twice(client: AsyncClient, mocked_aws):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   image_bytes = (Path(__file__).parent / "test_profile_image.jpg").read_bytes()
   response = await client.patch( "/users/me/picture",
       files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
       headers=headers,
   )
   assert response.status_code == 200

   response = await client.delete("/users/me/picture", headers=headers)
   assert response.status_code == 200
   response = await client.delete("/users/me/picture", headers=headers)
   assert response.status_code == 403

# Delete picture - unauthorized: no token
@pytest.mark.anyio
async def test_delete_picture_unauthorized(client: AsyncClient):
   response = await client.delete("/users/me/picture")
   assert response.status_code == 401  



