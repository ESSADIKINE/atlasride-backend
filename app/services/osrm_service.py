import httpx
import os
from typing import Dict, Any, List, Tuple
from app.models import OSRMRoute


class OSRMService:
    """Service for interacting with OSRM routing engine"""
    
    def __init__(self):
        self.base_url = os.getenv("OSRM_URL", "http://localhost:5000")
    
    async def get_route(
        self,
        start_lng: float,
        start_lat: float,
        end_lng: float,
        end_lat: float
    ) -> OSRMRoute:
        """
        Compute route between two points using OSRM
        
        Args:
            start_lng: Starting longitude
            start_lat: Starting latitude
            end_lng: Destination longitude
            end_lat: Destination latitude
        
        Returns:
            OSRMRoute with geometry, distance, duration, and coordinates
        
        Raises:
            Exception: If OSRM request fails
        """
        # Build OSRM request URL
        url = (
            f"{self.base_url}/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}"
            f"?overview=full&geometries=geojson"
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") != "Ok":
                    raise Exception(f"OSRM error: {data.get('message', 'Unknown error')}")
                
                route = data["routes"][0]
                geometry = route["geometry"]
                distance = route["distance"]
                duration = route["duration"]
                
                # Extract coordinates from GeoJSON
                coordinates = geometry["coordinates"]
                
                return OSRMRoute(
                    geometry=geometry,
                    distance=distance,
                    duration=duration,
                    coordinates=coordinates
                )
                
            except (httpx.HTTPError, Exception) as e:
                print(f"⚠️ Local OSRM failed ({str(e)}). Trying public OSRM...")
                
                # Fallback to public OSRM
                public_url = (
                    f"http://router.project-osrm.org/route/v1/driving/"
                    f"{start_lng},{start_lat};{end_lng},{end_lat}"
                    f"?overview=full&geometries=geojson"
                )
                
                try:
                    response = await client.get(public_url)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("code") != "Ok":
                        raise Exception(f"Public OSRM error: {data.get('message', 'Unknown error')}")
                    
                    route = data["routes"][0]
                    geometry = route["geometry"]
                    distance = route["distance"]
                    duration = route["duration"]
                    coordinates = geometry["coordinates"]
                    
                    return OSRMRoute(
                        geometry=geometry,
                        distance=distance,
                        duration=duration,
                        coordinates=coordinates
                    )
                except Exception as public_e:
                    print(f"⚠️ Public OSRM also failed ({str(public_e)}). Using straight-line fallback.")
                
                # Fallback: Create a straight line route
                # Generate 10 points between start and end
                coordinates = []
                steps = 10
                for i in range(steps + 1):
                    t = i / steps
                    lng = start_lng + (end_lng - start_lng) * t
                    lat = start_lat + (end_lat - start_lat) * t
                    coordinates.append([lng, lat])
                
                # Calculate approximate distance (Haversine-ish or simple Euclidean for fallback)
                # Using simple Euclidean approximation for fallback speed
                import math
                dx = (end_lng - start_lng) * 111.32 * math.cos(math.radians(start_lat))
                dy = (end_lat - start_lat) * 110.57
                distance = math.sqrt(dx*dx + dy*dy) * 1000 # meters
                
                duration = distance / 10 # approx 10 m/s (36 km/h)
                
                return OSRMRoute(
                    geometry={
                        "type": "LineString",
                        "coordinates": coordinates
                    },
                    distance=distance,
                    duration=duration,
                    coordinates=coordinates
                )
    
    def calculate_bearing(self, lng1: float, lat1: float, lng2: float, lat2: float) -> float:
        """
        Calculate bearing between two points
        
        Returns bearing in degrees (0-360)
        """
        import math
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lng_diff = math.radians(lng2 - lng1)
        
        # Calculate bearing
        x = math.sin(lng_diff) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - (
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lng_diff)
        )
        
        bearing = math.atan2(x, y)
        bearing_deg = math.degrees(bearing)
        
        # Normalize to 0-360
        return (bearing_deg + 360) % 360


# Global OSRM service instance
osrm_service = OSRMService()
