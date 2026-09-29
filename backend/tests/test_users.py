from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from tests.conftest import auth_header, create_test_user, login_user


###############
# user get reviews 
##############
#TODO :check again
@pytest.mark.anyio
async def test_get_user_reviews_pagination(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   for i in range(5):
       response = await client.post(
           "/users/me/reviews",
           json={},  # adjust to your ReviewCreate schema if it has required fields
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

#TODO :check again
@pytest.mark.anyio
async def test_user_only_sees_own_reviews(client: AsyncClient):
   # User A
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   for i in range(3):
       response = await client.post("/users/me/reviews", json={}, headers=headers_a)
       assert response.status_code == 201

   # User B (adjust to however your helpers make a second user)
   await create_test_user(client, email="b@test.com")
   token_b = await login_user(client, email="b@test.com")
   headers_b = auth_header(token_b)

   for i in range(2):
       response = await client.post("/users/me/reviews", json={}, headers=headers_b)
       assert response.status_code == 201

   response_a = await client.get("/users/me/reviews", headers=headers_a)
   response_b = await client.get("/users/me/reviews", headers=headers_b)
   assert response_a.json()["total"] == 3
   assert response_b.json()["total"] == 2


###############
# user get favourite
##############
# get all favourite dishes. list[DishResponse] not paginate -success

# wrong user get  all favourite dishes - unauthorized 

#get  all favourite dishes -bad input

#TODO: check all favourites all from Claude !

# Success: a new user with no favourites gets an empty list (200), not an error
@pytest.mark.anyio
async def test_get_favourites_empty(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   assert response.json() == []


# Success: dishes the user favourited come back in the list with the right data
@pytest.mark.anyio
async def test_get_favourites_success(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   # adjust: however your helpers create dishes (they probably need a restaurant too)
   dish_1 = await create_test_dish(client, headers)
   dish_2 = await create_test_dish(client, headers)

   # adjust: your real "add to favourites" route and expected status code
   for dish in (dish_1, dish_2):
       response = await client.post(f"/users/me/favourites/{dish['id']}", headers=headers)
       assert response.status_code == 201

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert len(data) == 2
   assert {d["id"] for d in data} == {dish_1["id"], dish_2["id"]}


# Success: only favourited dishes appear, not every dish that exists
@pytest.mark.anyio
async def test_get_favourites_only_returns_favourited(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   favourited = await create_test_dish(client, headers)
   not_favourited = await create_test_dish(client, headers)

   response = await client.post(f"/users/me/favourites/{favourited['id']}", headers=headers)
   assert response.status_code == 201

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code == 200
   data = response.json()
   assert len(data) == 1
   assert data[0]["id"] == favourited["id"]
   assert data[0]["id"] != not_favourited["id"]


# Privacy: user A must never see user B's favourites
@pytest.mark.anyio
async def test_user_only_sees_own_favourites(client: AsyncClient):
   # User A
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

   dish = await create_test_dish(client, headers_a)
   response = await client.post(f"/users/me/favourites/{dish['id']}", headers=headers_a)
   assert response.status_code == 201

   # User B (adjust to however your helpers make a second user)
   await create_test_user(client, email="b@test.com")
   token_b = await login_user(client, email="b@test.com")
   headers_b = auth_header(token_b)

   response_a = await client.get("/users/me/favourites", headers=headers_a)
   response_b = await client.get("/users/me/favourites", headers=headers_b)
   assert len(response_a.json()) == 1
   assert response_b.json() == []


# Failure: no token means the server doesn't know who "me" is, so it rejects the request
@pytest.mark.anyio
async def test_get_favourites_unauthorized(client: AsyncClient):
   response = await client.get("/users/me/favourites")
   assert response.status_code in (401, 403)  # depends on your auth scheme


# Failure: a garbage token is rejected the same way
@pytest.mark.anyio
async def test_get_favourites_invalid_token(client: AsyncClient):
   headers = auth_header("not-a-real-token")

   response = await client.get("/users/me/favourites", headers=headers)
   assert response.status_code in (401, 403)

###############
# user delete favourite
##############

# delete  favourite dishes -success 

# delete  favourite dishes -bad input 

# delete  favourite dishes - unauthorized 


###############
# create new user
##############

@pytest.mark.anyio
async def test_create_user_validation_error(client: AsyncClient):
    response = await client.post("/users", json={"username": "testuser"},)
    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.txt


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

# user login - success 

# login with wrong format -failed

# login empty value  -failed

# get user profile -- success 


# get user profile -- failed in unauthorized 

###############
# password reset
##############

@pytest.makr.anyio
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

# failed wrong email to send to reset pwd -failed 


# reset-pwd success 


# reset-pwd failed 


# logined user changes password - success 

# logined user changes password - failed - unauthorized 

# logined user changes password - failed - empty or wrong format? 

# user update profile username, email - success 

# user update profile username, email - failed what fail could it be ?


# user deletes account  - success

# user deletes account  - failed wrong user - unauthorized 

#  user deletes account  -- didnot behave/ delete? 

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
        f"/users/{user['id']}/picture",
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


#  test_upload_profile_picture -- unauthorized failed 

# delete_user_picture - success 

# delete_user_picture - failed unauthorized  - wrong user 

# # delete_user_picture -- bad input 