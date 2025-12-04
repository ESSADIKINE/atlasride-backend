import asyncio
import uuid
from app.database import db
from datetime import datetime

async def seed_data():
    print("🌱 Seeding fake data...")

    # 1. Create a Car
    car_id = str(uuid.uuid4())
    car_data = {
        "id": car_id,
        "start_lat": 52.520008,
        "start_lng": 13.404954,
        "end_lat": 52.529407,
        "end_lng": 13.397634,
        "speed": 50.0,
        "status": "moving"
    }
    
    print(f"🚗 Creating car {car_id}...")
    try:
        await db.insert_car(car_data)
        print("✅ Car created")
    except Exception as e:
        print(f"❌ Failed to create car: {e}")
        return

    # 2. Create a Route (Mock Data)
    # Simple straight line for testing
    route_geometry = {
        "type": "LineString",
        "coordinates": [
            [13.404954, 52.520008],
            [13.400000, 52.525000],
            [13.397634, 52.529407]
        ]
    }
    
    route_data = {
        "car_id": car_id,
        "geometry": route_geometry,
        "distance": 1500.0,
        "duration": 300.0
    }

    print("🗺️ Creating route...")
    try:
        await db.insert_route(route_data)
        print("✅ Route created")
    except Exception as e:
        print(f"❌ Failed to create route: {e}")

    # 3. Create Initial Position
    position_data = {
        "car_id": car_id,
        "lat": 52.520008,
        "lng": 13.404954,
        "heading": 0.0,
        "progress": 0.0
    }

    print("📍 Creating initial position...")
    try:
        await db.insert_car_position(position_data)
        print("✅ Position created")
    except Exception as e:
        print(f"❌ Failed to create position: {e}")

    print("\n✨ Seeding complete! You should see the car in the dashboard.")

if __name__ == "__main__":
    asyncio.run(seed_data())
