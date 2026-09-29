import pytest
from httpx import AsyncClient
from tests.conftest import auth_header, create_test_user, login_user

#start testing 

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
    assert data["has_more"] is False
    ## need to adjust to your code as i dont have manual pagination has_more here
    #run: uv run pytest tests/test_dishes.py -v

@pytest.mark.anyio
async def test_get_dishes_not_found(client: AsyncClient):
    response = await client.get("dishes/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dish not found"


@pytest.mark.anyio
async def test_get_dishes_pagination(client:AsyncClient):
   await create_test_user(client)
   token =  await login_user(client)
   headers = auth_header(token)

   for i in range(5):
       response = await client.post(
           "/dishes",
           json={},
           headers=headers,
       )
       assert response.status_code == 201 

   response = await client.get("/dishes")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["dishes"]) == 5
   assert data["has_more"] is False

   response = await client.get("/dishes?limit=2")
   assert response.status_code == 200
   data = response.json()
   assert data["total"] == 5
   assert len(data["dishes"]) == 2
   assert data["has_more"] is True

   response = await client.get("/dishes?skip=2&limit=2")
   assert response.status_code == 200
   data = response.json()
   assert data["totoal"] == 5
   assert len(data["dishes"]) == 2
   assert data["skip"] == 2
   assert data["limit"] == 2
       

###############
# Search dishes
###############

# Search dishes -- success correct output

# faild query 


###############
# get specfic dish detail
###############


###############
# user create review on speicific dish 
###############
@pytest.mark.anyio
async def test_create_review_success(client: AsyncClient):
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    # hwo to have {dish_id} initiated correctly
    response = await client.post(
        "/{dish_id}/reviews",
        json={"dish_id": 1, "rating": 3, "comment": "This is user review comment" },
        headers=headers,
    )

    assert response.status_code == 201 
    data = response.json()
    assert data["dish_id"] == 1
    assert data["rating"] == 3
    assert data["comment"] == "This is user review comment"
    assert data["user_id"] == user["id"]
    assert "id" in data
    assert "created_at" in data
    assert data["reviewer"]["username"] == "testuser"

@pytest.mark.anyio
async def test_create_review_unauthorized(client: AsyncClient):
    response = await client.post("/{dish_id}/reviews",
            json={"dish_id": 1, "rating": 3, "comment": "This is user review comment" },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


###############
# user creates favourite on specific dish 
###############

# toggle success 

# toggle failed


###############
# user creates dishes compare 
###############

# dishes compare - success -- AI generated 

# dishes compare - failed -- unauthorized ?? how?

# dishes compare - faile -- < 5 dished to compare