from supabase import create_client, Client
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase client singleton
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client"""
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        _supabase_client = create_client(url, key)
    
    return _supabase_client


class Database:
    """Database operations wrapper"""
    
    def __init__(self):
        self.client = get_supabase()
    
    async def insert_car(self, car_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new car into the database"""
        result = self.client.table("cars").insert(car_data).execute()
        return result.data[0] if result.data else None
    
    async def insert_route(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a route into the database"""
        result = self.client.table("routes").insert(route_data).execute()
        return result.data[0] if result.data else None
    
    async def insert_car_position(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a car position update"""
        result = self.client.table("car_positions").insert(position_data).execute()
        return result.data[0] if result.data else None
    
    async def update_car_position(self, car_id: str, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a car's position"""
        result = self.client.table("car_positions").insert(position_data).execute()
        return result.data[0] if result.data else None
    
    async def update_car_status(self, car_id: str, status: str) -> None:
        """Update car status"""
        self.client.table("cars").update({"status": status}).eq("id", car_id).execute()
    
    async def get_all_cars(self) -> List[Dict[str, Any]]:
        """Get all cars"""
        result = self.client.table("cars").select("*").execute()
        return result.data if result.data else []
    
    async def get_car_latest_position(self, car_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest position for a car"""
        result = (
            self.client.table("car_positions")
            .select("*")
            .eq("car_id", car_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    async def get_car_route(self, car_id: str) -> Optional[Dict[str, Any]]:
        """Get route for a car"""
        result = (
            self.client.table("routes")
            .select("*")
            .eq("car_id", car_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    async def delete_all_data(self) -> None:
        """Clear all simulation data"""
        # Delete in order: positions, routes, cars (due to foreign keys)
        self.client.table("car_positions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("routes").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("cars").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    async def get_latest_car_positions(self) -> List[Dict[str, Any]]:
        """
        Get the latest position for each car.
        Strategy: Fetch recent positions and deduplicate by car_id in Python.
        """
        # Fetch last 1000 positions (should cover all active cars in a small simulation)
        result = (
            self.client.table("car_positions")
            .select("*")
            .order("timestamp", desc=True)
            .limit(1000)
            .execute()
        )
        
        if not result.data:
            return []
            
        # Group by car_id, keeping only the first (latest) occurrence
        latest_positions = {}
        for pos in result.data:
            car_id = pos["car_id"]
            if car_id not in latest_positions:
                latest_positions[car_id] = pos
                
        return list(latest_positions.values())


# Global database instance
db = Database()
