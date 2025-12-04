from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class SpawnCarRequest(BaseModel):
    """Request model for spawning a new AI car"""
    start_lng: float = Field(..., description="Starting longitude")
    start_lat: float = Field(..., description="Starting latitude")
    end_lng: float = Field(..., description="Destination longitude")
    end_lat: float = Field(..., description="Destination latitude")
    speed: Optional[float] = Field(30.0, description="Car speed in km/h")


class RouteRequest(BaseModel):
    """Request model for computing a route"""
    start_lng: float
    start_lat: float
    end_lng: float
    end_lat: float


class Car(BaseModel):
    """Car entity model"""
    id: UUID
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    speed: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarPosition(BaseModel):
    """Car position update model"""
    id: UUID
    car_id: UUID
    lat: float
    lng: float
    heading: float
    progress: float
    timestamp: datetime

    class Config:
        from_attributes = True


class Route(BaseModel):
    """Route model with OSRM geometry"""
    id: UUID
    car_id: UUID
    geometry: Dict[str, Any]  # GeoJSON geometry
    distance: float  # meters
    duration: float  # seconds
    created_at: datetime

    class Config:
        from_attributes = True


class CarWithPosition(BaseModel):
    """Combined car and position data for API responses"""
    id: UUID
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    speed: float
    status: str
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    heading: Optional[float] = None
    progress: Optional[float] = None
    route_geometry: Optional[Dict[str, Any]] = None


class OSRMRoute(BaseModel):
    """OSRM route response model"""
    geometry: Dict[str, Any]  # GeoJSON LineString
    distance: float  # meters
    duration: float  # seconds
    coordinates: List[List[float]]  # [[lng, lat], ...]


class NearbyCar(BaseModel):
    """Car with distance to user"""
    car_id: UUID
    lat: float
    lng: float
    heading: float
    distance_km: float


class CarToUserRoute(BaseModel):
    """Route from a car to the user"""
    car_id: UUID
    user_lat: float
    user_lng: float
    coordinates: List[List[float]]
    distance: float  # meters
    duration: float  # seconds


class ChatRequest(BaseModel):
    """Chat command request from user"""
    message: str = Field(..., description="User's chat message/command")
    user_lat: float = Field(..., description="User's current latitude")
    user_lng: float = Field(..., description="User's current longitude")


class ChatResponse(BaseModel):
    """Chat bot response with optional car data"""
    reply: str = Field(..., description="Bot's text response")
    cars: List[NearbyCar] = Field(default_factory=list, description="List of relevant cars")
    highlight_car_id: Optional[str] = Field(None, description="Car ID to highlight on map")

