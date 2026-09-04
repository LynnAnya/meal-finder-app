# backend/seed.py
import asyncio
import random
from sqlalchemy import select
from database import AsyncSessionLocal, engine, Base
import models
from integrations.osm import fetch_nearby_osm_restaurants

# -------------------------------------------------------------------------
# Contextual Review Comment Pool for AI Grounding
# -------------------------------------------------------------------------
REVIEW_DATA = {
    "Ramen": [
        ("The tonkotsu broth is incredibly rich and simmered properly! Best chashu around.", 5),
        ("Very flavorful soup, though the noodles were slightly softer than firm Hakata style.", 4),
        ("Decent ramen for a quick lunch, but a bit too salty towards the end.", 3),
    ],
    "Coffee": [
        ("Velvety smooth milk texture and great specialty roast beans. Highly recommended!", 5),
        ("Good coffee, but they charge $1.00 extra for oat milk which is a bit steep.", 4),
        ("Way too bitter today, seemed like the espresso shot was pulled too fast.", 2),
    ],
    "Burger": [
        ("Patties have that perfect caramelized smash crust. Juicy, messy, and delicious.", 5),
        ("Solid burger and fresh pickles, though the bun got a bit soggy from the sauce.", 4),
        ("Average fast food burger. Convenient location but nothing memorable.", 3),
    ],
    "Steak": [
        ("Cooked to a flawless medium-rare with exceptional charring and tender meat.", 5),
        ("High quality beef, but expected more roasted sides for this premium price.", 4),
        ("A bit gristly on the edge, though the red wine peppercorn jus was fantastic.", 4),
    ],
    "Thai": [
        ("Authentic Bangkok balance of tamarind, heat, and fragrant fresh herbs!", 5),
        ("Tasty curry with generous tender beef, but could definitely use more chili kick.", 4),
        ("A bit sweet for my liking, but great portion size and fast takeout.", 3),
    ],
    "Acai": [
        ("Proper frozen thick acai without watery melted fillers. Granola was crunchy.", 5),
        ("Tasted super refreshing on a hot Brisbane day, but portions are a bit small.", 4),
    ],
    "Default": [
        ("Super fresh ingredients and generous portion size for the price!", 5),
        ("Delicious flavors and friendly staff, though there was a 15-minute wait during peak hour.", 4),
        ("Decent taste, but I found the seasoning slightly inconsistent.", 3),
    ],
}


def _get_dish_reviews(dish_name: str) -> list[tuple[str, int]]:
    name_l = dish_name.lower()
    if "ramen" in name_l:
        return REVIEW_DATA["Ramen"]
    if any(w in name_l for w in ["flat white", "latte", "espresso", "coffee"]):
        return REVIEW_DATA["Coffee"]
    if any(w in name_l for w in ["burger", "cheeseburger"]):
        return REVIEW_DATA["Burger"]
    if any(w in name_l for w in ["steak", "rump", "rib eye"]):
        return REVIEW_DATA["Steak"]
    if any(w in name_l for w in ["thai", "curry", "pad thai"]):
        return REVIEW_DATA["Thai"]
    if "acai" in name_l:
        return REVIEW_DATA["Acai"]
    return REVIEW_DATA["Default"]


# -------------------------------------------------------------------------
# Dynamic Menu Factory Mapped to OSM Nodes with Valid menu_category Values
# -------------------------------------------------------------------------
def generate_venue_menu(v_name: str, v_type: str, cuisine: str | None) -> list[dict]:
    nl = v_name.lower()
    cl = (cuisine or "").lower()

    if "gunshop cafe" in nl:
        dishes = [
            ("Potato Hash Cakes with Poached Eggs", 23.50, "Mains", 4.8),
            ("Smashed Avocado on Sourdough", 21.00, "Mains", 4.7),
            ("Single Origin Flat White", 5.20, "Beverages", 4.8),
            ("House Pork Belly & Fried Eggs", 25.00, "Mains", 4.6),
        ]
    elif "west end coffeehouse" in nl:
        dishes = [
            ("Northern Thai Pork Curry (Gaeng Hang Lay)", 21.50, "Mains", 4.9),
            ("Khao Soi Gai Curry Noodles", 19.50, "Mains", 4.8),
            ("Single Origin Flat White", 4.80, "Beverages", 4.7),
            ("Eggs on Toast with House Relish", 14.00, "Mains", 4.5),
        ]
    elif "boomerang snack bar" in nl:
        dishes = [
            ("Classic Double Cheeseburger", 13.50, "Mains", 4.4),
            ("Potato Scallop Batch (3pcs)", 5.50, "Sides", 4.8),
            ("Aussie Works Burger", 15.50, "Mains", 4.6),
            ("Chocolate Malt Milkshake", 7.00, "Beverages", 4.5),
        ]
    elif "rainworth fish" in nl:
        dishes = [
            ("Crumbed Cod & Chips Pack", 16.50, "Mains", 4.7),
            ("Crispy Calamari Rings (6pcs)", 11.00, "Appetizers", 4.5),
            ("Potato Scallop Batch (3pcs)", 5.00, "Sides", 4.7),
        ]
    elif "oakberry" in nl:
        dishes = [
            ("Classic Açai Energy Bowl", 16.50, "Mains", 4.8),
            ("Peanut Butter Crunch Açai Cup", 18.00, "Mains", 4.7),
            ("Açai Guaraná Smoothie", 10.50, "Beverages", 4.6),
        ]
    elif "walters steakhouse" in nl or "moo moo" in nl:
        dishes = [
            ("Char-Grilled Angus Steak (350g)", 58.00, "Mains", 4.9),
            ("Seared Scallops & Pancetta", 26.00, "Appetizers", 4.7),
            ("Truffle Potato Mash", 15.00, "Sides", 4.8),
            ("New York Baked Cheesecake", 17.50, "Dessert", 4.6),
        ]
    elif any(k in nl for k in ["norman hotel", "chalk hotel", "pineapple hotel", "hotel west end"]):
        dishes = [
            ("Classic Chicken Parmigiana", 26.00, "Mains", 4.7),
            ("Char-Grilled Angus Steak (300g)", 34.00, "Mains", 4.6),
            ("Salt & Pepper Calamari", 17.00, "Appetizers", 4.4),
            ("Craft Beer Tasting Pint", 11.50, "Beverages", 4.5),
        ]
    elif "lil luca" in nl or "sandwich" in cl:
        dishes = [
            ("Mortadella & Pistachio Panino", 17.50, "Mains", 4.9),
            ("Crispy Panko Chicken Focaccia", 16.50, "Mains", 4.8),
            ("Italian Iced Shakerato", 6.00, "Beverages", 4.6),
        ]
    elif "olive & angelo" in nl or "italian" in cl:
        dishes = [
            ("Handmade Truffle Pappardelle", 28.50, "Mains", 4.8),
            ("Woodfired Margherita Pizza", 23.00, "Mains", 4.7),
            ("Classic Espresso Tiramisu", 14.50, "Dessert", 4.9),
        ]
    elif any(k in nl for k in ["k-pocha", "han woo ri"]) or "korean" in cl:
        dishes = [
            ("Crispy Korean Fried Chicken", 23.00, "Mains", 4.8),
            ("Stone Pot Bibimbap", 19.50, "Mains", 4.6),
            ("Seafood Scallion Pancake (Pajeon)", 17.00, "Appetizers", 4.5),
        ]
    elif "oishii" in nl or "japanese" in cl:
        dishes = [
            ("Signature Tonkotsu Ramen", 18.50, "Mains", 4.8),
            ("Crispy Chicken Katsu Curry", 17.50, "Mains", 4.6),
            ("Pan-Fried Pork Gyoza (5pcs)", 9.50, "Appetizers", 4.5),
        ]
    elif "tibetan kitchen" in nl:
        dishes = [
            ("Steamed Pork Momos (6pcs)", 17.50, "Mains", 4.9),
            ("Himalayan Slow-Braised Goat Curry", 24.50, "Mains", 4.7),
            ("Tingmo Steamed Bread", 5.50, "Sides", 4.5),
        ]
    elif "west end garden" in nl or "vietnamese" in cl:
        dishes = [
            ("Vietnamese Beef Pho (Pho Bo)", 18.00, "Mains", 4.8),
            ("Crispy Pork Belly Banh Mi", 13.50, "Mains", 4.7),
            ("Pork & Prawn Rice Paper Rolls (3pcs)", 10.50, "Appetizers", 4.6),
        ]
    elif any(k in nl for k in ["siam samrarn", "thai terrace"]) or "thai" in cl:
        dishes = [
            ("Massaman Beef Curry", 23.50, "Mains", 4.8),
            ("Pad Thai Boran", 19.00, "Mains", 4.7),
            ("Crispy Pork Belly with Chinese Broccoli", 22.00, "Mains", 4.6),
            ("Spicy Tom Yum Prawn Soup", 20.50, "Mains", 4.5),
        ]
    elif any(k in nl for k in ["ben & jerry", "happy pops", "new zealand natural"]) or v_type == "Dessert & Ice Cream":
        dishes = [
            ("Artisan Double Scoop Gelato", 9.00, "Dessert", 4.8),
            ("Warm Brownie Fudge Sundae", 14.50, "Dessert", 4.9),
            ("Wild Berry Fruit Sorbet Cup", 8.00, "Dessert", 4.6),
        ]
    elif any(k in nl for k in ["brooklyn slice", "domino"]) or "pizza" in cl:
        dishes = [
            ("NY Pepperoni Slice", 7.50, "Mains", 4.7),
            ("Classic Margherita Pie", 22.00, "Mains", 4.6),
            ("Garlic Parmesan Dough Knots (4pcs)", 8.00, "Appetizers", 4.5),
        ]
    elif any(k in nl for k in ["hungry jack", "grill'd", "5 dogs"]) or "burger" in cl:
        dishes = [
            ("Classic Double Cheeseburger", 14.00, "Mains", 4.5),
            ("Crispy Bacon & Avocado Burger", 17.50, "Mains", 4.6),
            ("Loaded Chilli Cheese Dog", 13.50, "Mains", 4.4),
            ("Rosemary Sea Salt Chips", 7.00, "Sides", 4.5),
        ]
    elif v_type == "Cafe" or "coffee" in cl:
        dishes = [
            ("Smashed Avocado on Sourdough", 19.50, "Mains", 4.6),
            ("Classic Açai Energy Bowl", 16.00, "Mains", 4.5),
            ("Single Origin Flat White", 4.90, "Beverages", 4.7),
            ("Ceremonial Iced Matcha Latte", 6.80, "Beverages", 4.6),
        ]
    else:
        dishes = [
            ("Classic Chicken Parmigiana", 24.50, "Mains", 4.5),
            ("Classic Double Cheeseburger", 15.00, "Mains", 4.4),
            ("Salt & Pepper Calamari", 15.50, "Appetizers", 4.3),
        ]

    seen_names = set()
    cleaned_menu = []

    for name, base_price, category, base_rating in dishes:
        if name in seen_names:
            continue
        seen_names.add(name)

        # Dynamic price variation: +/- $1.00
        price_delta = random.choice([-1.00, -0.50, 0.0, 0.50, 1.00])
        final_price = max(3.50, round(base_price + price_delta, 2))

        # Dynamic rating variation: +/- 0.2
        rating_delta = random.choice([-0.2, -0.1, 0.0, 0.1, 0.2])
        final_rating = round(min(5.0, max(3.2, base_rating + rating_delta)), 1)

        cleaned_menu.append({
            "name": name,
            "price": final_price,
            "menu_category": category,
            "average_rating": final_rating,
        })

    return cleaned_menu


# -------------------------------------------------------------------------
# Database Seed Pipeline
# -------------------------------------------------------------------------
async def seed_database():
    print("Connecting to database and verifying tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed test users if not present using the exact password_hash column
        res_users = await session.execute(select(models.User))
        existing_users = res_users.scalars().all()
        if not existing_users:
            test_users = [
                models.User(
                    username="alex_brisbane",
                    email="alex@foodie.local",
                    password_hash="pw_hashed_123",
                ),
                models.User(
                    username="sam_westend",
                    email="sam@foodie.local",
                    password_hash="pw_hashed_123",
                ),
                models.User(
                    username="charlie_bites",
                    email="charlie@foodie.local",
                    password_hash="pw_hashed_123",
                ),
            ]
            session.add_all(test_users)
            await session.flush()
            users_pool = test_users
        else:
            users_pool = existing_users

        # 2. Check if restaurant data already exists (idempotency guard)
        check_existing = await session.execute(select(models.Restaurant))
        if check_existing.scalars().first():
            print("Database already populated with restaurants. Skipping seed.")
            return

        # 3. Query real OpenStreetMap Overpass API nodes
        print("Querying Overpass API for West End dining nodes...")
        osm_venues = await fetch_nearby_osm_restaurants(radius=3000, target_count=50)
        if not osm_venues:
            print("No venues received from OSM. Aborting seed.")
            return

        print(f"Injecting {len(osm_venues)} authentic restaurants with matched menus...")
        for venue in osm_venues:
            restaurant = models.Restaurant(
                name=venue["name"],
                address=venue["address"],
                lat=venue["lat"],
                lon=venue["lon"],
                venue_type=venue["venue_type"],
                cuisine=venue["cuisine"],
                opening_hours=venue["opening_hours"],
            )
            session.add(restaurant)
            await session.flush()

            venue_dishes = generate_venue_menu(
                v_name=venue["name"],
                v_type=venue["venue_type"],
                cuisine=venue["cuisine"],
            )

            for d_info in venue_dishes:
                dish = models.Dish(
                    name=d_info["name"],
                    price=d_info["price"],
                    menu_category=d_info["menu_category"],
                    average_rating=d_info["average_rating"],
                    restaurant_id=restaurant.id,
                )
                session.add(dish)
                await session.flush()

                # Pick reviews and sample distinct users to prevent composite UNIQUE constraint violation
                review_candidates = _get_dish_reviews(dish.name)
                num_reviews = random.randint(1, 2)
                sampled_reviews = random.sample(
                    review_candidates, k=min(len(review_candidates), num_reviews)
                )
                assigned_reviewers = random.sample(
                    users_pool, k=min(len(users_pool), len(sampled_reviews))
                )

                for (comment_text, score), review_user in zip(sampled_reviews, assigned_reviewers):
                    rev = models.Review(
                        dish_id=dish.id,
                        user_id=review_user.id,
                        rating=score,
                        comment=comment_text,
                    )
                    session.add(rev)

        await session.commit()
        print(f"Done! Successfully seeded {len(osm_venues)} restaurants with valid category-tagged dishes and reviews.")


if __name__ == "__main__":
    asyncio.run(seed_database())