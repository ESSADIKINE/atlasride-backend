from fastapi import APIRouter, HTTPException
from app.models import SpawnCarRequest, RouteRequest, CarWithPosition, OSRMRoute, NearbyCar, CarToUserRoute, ChatRequest, ChatResponse
from app.database import db
from app.services.osrm_service import osrm_service
from app.services.simulation import simulation_engine
from typing import List
import uuid

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/spawn-car", response_model=dict)
async def spawn_car(request: SpawnCarRequest):
    """
    Spawn a new AI car with OSRM route
    
    Process:
    1. Compute route using OSRM
    2. Store car in database
    3. Store route geometry
    4. Add car to simulation engine
    5. Return car data
    """
    try:
        # Get route from OSRM
        route = await osrm_service.get_route(
            request.start_lng,
            request.start_lat,
            request.end_lng,
            request.end_lat
        )
        
        # Generate car ID
        car_id = str(uuid.uuid4())
        
        # Insert car into database
        car_data = {
            "id": car_id,
            "start_lat": request.start_lat,
            "start_lng": request.start_lng,
            "end_lat": request.end_lat,
            "end_lng": request.end_lng,
            "speed": request.speed,
            "status": "moving"
        }
        
        car = await db.insert_car(car_data)
        
        # Store route
        route_data = {
            "car_id": car_id,
            "geometry": route.geometry,
            "distance": route.distance,
            "duration": route.duration
        }
        
        await db.insert_route(route_data)
        
        # Add to simulation
        await simulation_engine.add_car(car_id, route.coordinates)
        
        return {
            "success": True,
            "car_id": car_id,
            "message": f"Car spawned successfully with {len(route.coordinates)} waypoints",
            "route": {
                "distance": route.distance,
                "duration": route.duration
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn car: {str(e)}")


@router.get("/cars", response_model=List[CarWithPosition])
async def get_all_cars():
    """
    Get all cars with their latest positions
    """
    try:
        cars = await db.get_all_cars()
        result = []
        
        for car in cars:
            car_id = str(car["id"])
            
            # Get latest position
            position = await db.get_car_latest_position(car_id)
            
            # Get route
            route = await db.get_car_route(car_id)
            
            car_with_pos = CarWithPosition(
                id=car["id"],
                start_lat=car["start_lat"],
                start_lng=car["start_lng"],
                end_lat=car["end_lat"],
                end_lng=car["end_lng"],
                speed=car["speed"],
                status=car["status"],
                current_lat=position["lat"] if position else None,
                current_lng=position["lng"] if position else None,
                heading=position["heading"] if position else None,
                progress=position["progress"] if position else None,
                route_geometry=route["geometry"] if route else None
            )
            
            result.append(car_with_pos)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cars: {str(e)}")


@router.get("/route", response_model=OSRMRoute)
async def get_route(start_lng: float, start_lat: float, end_lng: float, end_lat: float):
    """
    Compute a route between two points (for preview/testing)
    """
    try:
        route = await osrm_service.get_route(start_lng, start_lat, end_lng, end_lat)
        return route
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute route: {str(e)}")


@router.post("/reset")
async def reset_simulation():
    """
    Reset the simulation by clearing all data
    """
    try:
        # Clear simulation state
        simulation_engine.car_states.clear()
        
        # Clear database
        await db.delete_all_data()
        
        return {
            "success": True,
            "message": "Simulation reset successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset simulation: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "simulation_running": simulation_engine.running,
        "active_cars": len(simulation_engine.car_states)
    }


# --- Simple Ride-Style App Endpoints ---

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    import math
    
    # Convert decimal degrees to radians 
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    # Haversine formula 
    dlon = lng2 - lng1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


@router.get("/cars/nearby", response_model=List[NearbyCar])
async def get_nearby_cars(user_lat: float, user_lng: float, radius_km: float = 10.0):
    """
    Get active cars within a specific radius of the user.
    """
    try:
        # 1. Get latest positions per car
        positions = await db.get_latest_car_positions()
        
        nearby_cars = []
        
        for pos in positions:
            # 2. Compute distance
            dist = haversine_distance(
                user_lat, user_lng,
                pos["lat"], pos["lng"]
            )
            
            # 3. Filter by radius
            if dist <= radius_km:
                nearby_cars.append(NearbyCar(
                    car_id=pos["car_id"],
                    lat=pos["lat"],
                    lng=pos["lng"],
                    heading=pos["heading"],
                    distance_km=round(dist, 2)
                ))
                
        # Sort by distance
        nearby_cars.sort(key=lambda x: x.distance_km)
        
        return nearby_cars
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch nearby cars: {str(e)}")


@router.get("/route/car-to-user", response_model=CarToUserRoute)
async def get_car_to_user_route(car_id: str, user_lat: float, user_lng: float):
    """
    Calculate a route from a specific car to the user's location.
    """
    try:
        # 1. Get car's latest position
        position = await db.get_car_latest_position(car_id)
        if not position:
            raise HTTPException(status_code=404, detail="Car not found or has no position")
            
        car_lat = position["lat"]
        car_lng = position["lng"]
        
        # 2. Call OSRM
        # Origin: Car, Destination: User
        route = await osrm_service.get_route(
            start_lng=car_lng,
            start_lat=car_lat,
            end_lng=user_lng,
            end_lat=user_lat
        )
        
        # 3. Return simplified response
        return CarToUserRoute(
            car_id=uuid.UUID(car_id),
            user_lat=user_lat,
            user_lng=user_lng,
            coordinates=route.coordinates,
            distance=route.distance,
            duration=route.duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute route: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat_command(request: ChatRequest):
    """
    Process chat commands and return relevant car data.
    
    Supported commands:
    - /help: List available commands
    - /nearme [radius_km]: Find cars within radius (default 10km)
    - /distance <car_id_suffix>: Get distance to specific car
    """
    try:
        message = request.message.strip()
        
        # Handle /help command
        if message.lower() == "/help":
            help_text = """**Available Commands:**
            
• `/help` - Show this help message
• `/nearme [radius]` - Find cars within radius (default 10 km)
  Example: `/nearme 5`
• `/distance <car_id>` - Get distance to a specific car
  Example: `/distance 3193`
  
💡 Tip: You can use the last 4 digits of a car ID"""
            
            return ChatResponse(
                reply=help_text,
                cars=[],
                highlight_car_id=None
            )
        
        # Handle /nearme command
        if message.lower().startswith("/nearme"):
            parts = message.split()
            radius_km = 10.0  # default
            
            # Parse optional radius parameter
            if len(parts) > 1:
                try:
                    radius_km = float(parts[1])
                except ValueError:
                    return ChatResponse(
                        reply=f"❌ Invalid radius: '{parts[1]}'. Please use a number.\n\nExample: `/nearme 5`",
                        cars=[],
                        highlight_car_id=None
                    )
            
            # Get all car positions
            positions = await db.get_latest_car_positions()
            
            nearby_cars = []
            for pos in positions:
                dist = haversine_distance(
                    request.user_lat, request.user_lng,
                    pos["lat"], pos["lng"]
                )
                
                if dist <= radius_km:
                    nearby_cars.append(NearbyCar(
                        car_id=pos["car_id"],
                        lat=pos["lat"],
                        lng=pos["lng"],
                        heading=pos["heading"],
                        distance_km=round(dist, 2)
                    ))
            
            # Sort by distance
            nearby_cars.sort(key=lambda x: x.distance_km)
            
            # Build response message
            if not nearby_cars:
                reply = f"🔍 No cars found within {radius_km} km of your location."
            else:
                car_word = "car" if len(nearby_cars) == 1 else "cars"
                reply = f"✅ Found **{len(nearby_cars)} {car_word}** within {radius_km} km:\n\n"
                
                # List up to 5 cars
                for i, car in enumerate(nearby_cars[:5]):
                    car_id_short = str(car.car_id)[-4:]
                    reply += f"• Car `...{car_id_short}` - {car.distance_km} km away\n"
                
                if len(nearby_cars) > 5:
                    reply += f"\n...and {len(nearby_cars) - 5} more"
            
            # Highlight closest car
            highlight_id = str(nearby_cars[0].car_id) if nearby_cars else None
            
            return ChatResponse(
                reply=reply,
                cars=nearby_cars,
                highlight_car_id=highlight_id
            )
        
        # Handle /distance command
        if message.lower().startswith("/distance"):
            parts = message.split()
            
            if len(parts) < 2:
                return ChatResponse(
                    reply="❌ Missing car ID.\n\nUsage: `/distance <car_id>`\nExample: `/distance 3193`",
                    cars=[],
                    highlight_car_id=None
                )
            
            car_suffix = parts[1].strip()
            
            # Get all car positions
            positions = await db.get_latest_car_positions()
            
            # Find car matching the suffix or exact ID
            matching_car = None
            for pos in positions:
                car_id_str = str(pos["car_id"])
                if car_id_str.endswith(car_suffix) or car_id_str == car_suffix:
                    matching_car = pos
                    break
            
            if not matching_car:
                return ChatResponse(
                    reply=f"❌ No car found matching '{car_suffix}'.\n\nTry `/nearme` to see available cars.",
                    cars=[],
                    highlight_car_id=None
                )
            
            # Calculate distance
            dist = haversine_distance(
                request.user_lat, request.user_lng,
                matching_car["lat"], matching_car["lng"]
            )
            
            car_id_short = str(matching_car["car_id"])[-4:]
            reply = f"📍 **Car `...{car_id_short}`**\n\n• Distance: **{round(dist, 2)} km**\n• Heading: {round(matching_car['heading'])}°"
            
            nearby_car = NearbyCar(
                car_id=matching_car["car_id"],
                lat=matching_car["lat"],
                lng=matching_car["lng"],
                heading=matching_car["heading"],
                distance_km=round(dist, 2)
            )
            
            return ChatResponse(
                reply=reply,
                cars=[nearby_car],
                highlight_car_id=str(matching_car["car_id"])
            )
        
        # Unknown command
        return ChatResponse(
            reply="❓ Unknown command. Type `/help` to see available commands.",
            cars=[],
            highlight_car_id=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat command failed: {str(e)}")

