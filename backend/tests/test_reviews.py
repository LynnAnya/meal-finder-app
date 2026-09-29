import pytest
from httpx import AsyncClient
from tests.conftest import auth_header, create_test_user, login_user


################
# update review 
################
@pytest.mark.anyio
async def test_update_review_success(client: AsyncClient):
    ## /reviews/{review_id}
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    # might add more step to get dish_id correctly
    dish_id = 1 ## TODO

    response = await client.post(
           f"/{dish_id}/reviews",
           json={"dish_id": 1, "rating": 3, "comment": "This is user review comment" },
           headers=headers,
       )

    review_id = response.json()["id"]

    response = await client.patch(
        f"reviews/{review_id}",
        json={"comment":"Updated review comment now"},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 3
    assert data["comment"] == "Updated review comment now"



@pytest.mark.anyio
async def test_update_review_wrong_user(client: AsyncClient):
    await create_test_user(client, username="user1", email="user1@example.com")
    token1 = await login_user(client, email="user1@example.com")

    dish_id = 1 ## TODO: not sure if can hard code 

    response = await client.post(
        f"/{dish_id}/reviews",
        json={"dish_id": 1, "rating": 1, "comment": "Only user1 can update this review" },
        headers=auth_header(token1),
    )

    review_id = response.json()["id"]
    await create_test_user(client, username="user2", email="user2@example.com")
    token2 = await login_user(client, email="user2@example.com" )

    response = await client.patch(
        f"/review/{review_id}",
        json={"comment": "Hacked comment, I am the wrong user to update review"},
        headers=auth_header(token2)
    )

    assert response.status_code == 403
    assert response.json(["detail"]) == "Not authorized user to update this review!"




################
# user deleted review 
################

# owner deleted review - success 
@pytest.mark.anyio
async def test_delete_review_success(client: AsyncClient):
    pass
#  deleted review -- failed -- no token to prove who --unauthorized 


# deleted review - faield -- wrong user forbidden

# deleted review - faield -- wrong id 99999 --- not found 