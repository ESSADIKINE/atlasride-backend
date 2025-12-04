import httpx
import random
import time

# User provided coordinates (Casablanca)
points = [
    {"lat": 33.39123, "lng": -7.94762},
    {"lat": 33.55292, "lng": -7.62379},
    {"lat": 33.54945, "lng": -7.64413},
    {"lat": 33.56277, "lng": -7.66815},
    {"lat": 33.55187, "lng": -7.69003},
    {"lat": 33.53779, "lng": -7.66268}
]

API_URL = "http://localhost:8000/api/spawn-car"

def spawn_cars():
    print(f"🚀 Spawning {len(points)} cars in Casablanca...")
    
    for i, start_point in enumerate(points):
        # Pick a random end point that is not the start point
        end_point = random.choice([p for p in points if p != start_point])
        
        payload = {
            "start_lat": start_point["lat"],
            "start_lng": start_point["lng"],
            "end_lat": end_point["lat"],
            "end_lng": end_point["lng"],
            "speed": 40  # km/h
        }
        
        try:
            response = httpx.post(API_URL, json=payload, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Car {i+1} spawned: {data['car_id']}")
            else:
                print(f"❌ Failed to spawn car {i+1}: {response.text}")
        except Exception as e:
            print(f"❌ Error spawning car {i+1}: {str(e)}")
            
        # Small delay to not overwhelm OSRM
        time.sleep(0.5)

if __name__ == "__main__":
    spawn_cars()
