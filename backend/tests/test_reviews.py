import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import (
    auth_header, 
    create_test_user, 
    login_user,  
    create_test_dish)


################
# update review 
################
@pytest.mark.anyio
async def test_update_review_success(client: AsyncClient, db_session: AsyncSession):
    ## /reviews/{review_id}
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    #create dish
    dish = await create_test_dish(db_session)
    #review dish
    response = await client.post(f"/dishes/{dish.id}/reviews",
           json={"dish_id": dish.id, "rating": 3, "comment": "This is user review comment" },
           headers=headers,
       )
    assert response.status_code == 201, response.text
    review_id = response.json()["review_id"]

    response = await client.patch(f"/reviews/{review_id}",
        json={"comment":"Updated review comment now"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 3
    assert data["comment"] == "Updated review comment now"



@pytest.mark.anyio
async def test_update_review_wrong_user(client: AsyncClient, db_session: AsyncSession):
    await create_test_user(client, username="user1", email="user1@example.com")
    token1 = await login_user(client, email="user1@example.com")

    dish = await create_test_dish(db_session)
    # user1 creates review
    response = await client.post(f"/dishes/{dish.id}/reviews",
        json={"dish_id": dish.id, "rating": 1, "comment": "Only user1 can update this review" },
        headers=auth_header(token1),
    )
    review_id = response.json()["review_id"]

    #wrong user 
    await create_test_user(client, username="user2", email="user2@example.com")
    token2 = await login_user(client, email="user2@example.com" )

    response = await client.patch(f"/reviews/{review_id}",
        json={"comment": "Hacked comment, I am the wrong user to update review"},
        headers=auth_header(token2)
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to edit this review"


# Update review - failure: a review id that doesn't exist
@pytest.mark.anyio
async def test_update_review_not_found(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.patch("/reviews/9999", json={"rating": 4}, headers=headers)
   assert response.status_code == 404
   assert response.json()["detail"] == "Review not found"


# Update review - unauthorized: no token is rejected
@pytest.mark.anyio
async def test_update_review_unauthorized(client: AsyncClient):
   response = await client.patch("/reviews/1", json={"rating": 4})
   assert response.status_code == 401

################
# user deleted review 
################
# Delete review - success
@pytest.mark.anyio
async def test_delete_review_success(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session)
   response = await client.post(f"/dishes/{dish.id}/reviews",
       json={"rating": 4, "comment": "To be deleted"},
       headers=headers,
   )
   assert response.status_code == 201
   review_id = response.json()["review_id"]

    # delete review start here
   response = await client.delete(f"/reviews/{review_id}", headers=headers)
   assert response.status_code == 204
   assert response.text == ""  

   response = await client.get(f"/dishes/{dish.id}")
   assert response.json()["reviews"] == []


# Delete review - failure: a review id that doesn't exist
@pytest.mark.anyio
async def test_delete_review_not_found(client: AsyncClient):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   response = await client.delete("/reviews/9999", headers=headers)
   assert response.status_code == 404
   assert response.json()["detail"] == "Review not found"


# Delete review - failure: deleting someone else's review 
@pytest.mark.anyio
async def test_delete_review_wrong_user(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token_a = await login_user(client)
   headers_a = auth_header(token_a)

    #create dish
   dish = await create_test_dish(db_session)
   # create review to this
   response = await client.post(f"/dishes/{dish.id}/reviews",
       json={"rating": 5, "comment": "A's review"},
       headers=headers_a,
   )
   assert response.status_code == 201
   review_id = response.json()["review_id"]

   # User B tries to delete user A's
   await create_test_user(client, username="user_b", email="b@test.com", password="b_passworduser111")
   token_b = await login_user(client, email="b@test.com", password="b_passworduser111")
   headers_b = auth_header(token_b)

   response = await client.delete(f"/reviews/{review_id}", headers=headers_b)
   assert response.status_code == 403
   assert response.json()["detail"] == "Not authorized to edit this review"

   """""
   # A's review is still there
   response = await client.get(f"/users/me/reviews")
   assert response.status_code == 200
   reviews = response.json()
   assert reviews["total"] == 1
   assert len(reviews["items"]) == 1
   assert reviews["items"][0]["comment"] == "A's review"
   """""


# Delete review - failure: deleting the same review twice
@pytest.mark.anyio
async def test_delete_review_twice(client: AsyncClient, db_session: AsyncSession):
   await create_test_user(client)
   token = await login_user(client)
   headers = auth_header(token)

   dish = await create_test_dish(db_session)
   response = await client.post(f"/dishes/{dish.id}/reviews",
       json={"rating": 4, "comment": "Delete me twice"},
       headers=headers,
   )
   review_id = response.json()["review_id"]

   response = await client.delete(f"/reviews/{review_id}", headers=headers)
   assert response.status_code == 204
   response = await client.delete(f"/reviews/{review_id}", headers=headers)
   assert response.status_code == 404

# Delete review - unauthorized
@pytest.mark.anyio
async def test_delete_review_unauthorized(client: AsyncClient):
   response = await client.delete("/reviews/1")
   assert response.status_code == 401