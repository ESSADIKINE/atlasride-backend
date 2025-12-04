import asyncio
from typing import Dict, Any, List
from app.database import db
from app.services.osrm_service import osrm_service
import math
import os


class SimulationEngine:
    """
    Core simulation engine that moves cars along their routes
    """
    
    def __init__(self):
        self.running = False
        self.update_interval = float(os.getenv("SIMULATION_UPDATE_INTERVAL", "0.2"))
        self.car_states: Dict[str, Dict[str, Any]] = {}  # car_id -> state
    
    async def start(self):
        """Start the simulation loop"""
        self.running = True
        print(f"🚗 Simulation engine started (update interval: {self.update_interval}s)")
        
        while self.running:
            try:
                await self.update_all_cars()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on error
    
    def stop(self):
        """Stop the simulation loop"""
        self.running = False
        print("🛑 Simulation engine stopped")
    
    async def add_car(self, car_id: str, route_coordinates: List[List[float]]):
        """
        Add a new car to the simulation
        
        Args:
            car_id: UUID of the car
            route_coordinates: List of [lng, lat] coordinates from OSRM
        """
        if len(route_coordinates) < 2:
            raise ValueError("Route must have at least 2 coordinates")
        
        self.car_states[car_id] = {
            "coordinates": route_coordinates,
            "current_index": 0,
            "progress": 0.0,
            "status": "moving"
        }
        
        # Set initial position
        start_coord = route_coordinates[0]
        await db.insert_car_position({
            "car_id": car_id,
            "lng": start_coord[0],
            "lat": start_coord[1],
            "heading": self._calculate_initial_heading(route_coordinates),
            "progress": 0.0
        })
        
        print(f"✅ Car {car_id[:8]} added to simulation ({len(route_coordinates)} waypoints)")
    
    def _calculate_initial_heading(self, coordinates: List[List[float]]) -> float:
        """Calculate initial heading from first two points"""
        if len(coordinates) < 2:
            return 0.0
        
        lng1, lat1 = coordinates[0]
        lng2, lat2 = coordinates[1]
        return osrm_service.calculate_bearing(lng1, lat1, lng2, lat2)
    
    async def update_all_cars(self):
        """Update positions of all active cars"""
        # Get list of car IDs to update (avoid dict size change during iteration)
        car_ids = list(self.car_states.keys())
        
        for car_id in car_ids:
            try:
                await self.update_car_position(car_id)
            except Exception as e:
                print(f"❌ Error updating car {car_id[:8]}: {e}")
    
    async def update_car_position(self, car_id: str):
        """
        Update a single car's position along its route
        """
        state = self.car_states.get(car_id)
        if not state:
            return
        
        # Check if car is finished
        if state["status"] == "finished":
            return
        
        coordinates = state["coordinates"]
        current_index = state["current_index"]
        
        # Check if we've reached the end
        if current_index >= len(coordinates) - 1:
            await self._finish_car(car_id)
            return
        
        # Get current and next waypoint
        current_point = coordinates[current_index]
        next_point = coordinates[current_index + 1]
        
        # Get car speed from database
        car_data = await db.get_all_cars()
        car = next((c for c in car_data if str(c["id"]) == car_id), None)
        
        if not car:
            # Car deleted, remove from simulation
            del self.car_states[car_id]
            return
        
        speed_kmh = car.get("speed", 30.0)
        
        # Calculate movement
        # Distance per update = (speed in m/s) * update_interval
        # speed_kmh / 3.6 = speed in m/s
        distance_per_update = (speed_kmh / 3.6) * self.update_interval
        
        # Calculate distance between current and next point (approximate)
        segment_distance = self._calculate_distance(
            current_point[1], current_point[0],
            next_point[1], next_point[0]
        )
        
        # If we can reach the next waypoint in this update, move to it
        if distance_per_update >= segment_distance:
            state["current_index"] += 1
            new_position = coordinates[state["current_index"]]
            
            # Calculate heading to next point (if available)
            if state["current_index"] < len(coordinates) - 1:
                next_coord = coordinates[state["current_index"] + 1]
                heading = osrm_service.calculate_bearing(
                    new_position[0], new_position[1],
                    next_coord[0], next_coord[1]
                )
            else:
                # Last point, use previous heading
                latest_pos = await db.get_car_latest_position(car_id)
                heading = latest_pos["heading"] if latest_pos else 0.0
        else:
            # Interpolate between current and next point
            progress_ratio = distance_per_update / segment_distance if segment_distance > 0 else 0
            
            new_lng = current_point[0] + (next_point[0] - current_point[0]) * progress_ratio
            new_lat = current_point[1] + (next_point[1] - current_point[1]) * progress_ratio
            new_position = [new_lng, new_lat]
            
            heading = osrm_service.calculate_bearing(
                current_point[0], current_point[1],
                next_point[0], next_point[1]
            )
            
            # Update coordinates for next iteration
            coordinates[current_index] = new_position
        
        # Calculate overall progress (0-100)
        progress = (state["current_index"] / (len(coordinates) - 1)) * 100
        state["progress"] = progress
        
        # Store position update in database
        await db.insert_car_position({
            "car_id": car_id,
            "lng": new_position[0],
            "lat": new_position[1],
            "heading": heading,
            "progress": progress
        })
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    async def _finish_car(self, car_id: str):
        """Mark a car as finished"""
        state = self.car_states.get(car_id)
        if state:
            state["status"] = "finished"
            state["progress"] = 100.0
            
            # Update database
            await db.update_car_status(car_id, "finished")
            
            print(f"🏁 Car {car_id[:8]} finished route")


# Global simulation engine instance
simulation_engine = SimulationEngine()
