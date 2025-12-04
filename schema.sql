-- AtlasRide AI Database Schema
-- Run this in your Supabase SQL editor

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cars table: stores car metadata
CREATE TABLE IF NOT EXISTS cars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_lat DOUBLE PRECISION NOT NULL,
    start_lng DOUBLE PRECISION NOT NULL,
    end_lat DOUBLE PRECISION NOT NULL,
    end_lng DOUBLE PRECISION NOT NULL,
    speed DOUBLE PRECISION DEFAULT 30.0, -- km/h
    status VARCHAR(20) DEFAULT 'moving', -- moving, finished, idle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Car positions table: stores real-time position updates
CREATE TABLE IF NOT EXISTS car_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    car_id UUID NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    heading DOUBLE PRECISION DEFAULT 0, -- bearing in degrees
    progress DOUBLE PRECISION DEFAULT 0, -- 0-100 percentage
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_car FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
);

-- Routes table: stores OSRM route geometry
CREATE TABLE IF NOT EXISTS routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    car_id UUID NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    geometry JSONB NOT NULL, -- GeoJSON geometry from OSRM
    distance DOUBLE PRECISION NOT NULL, -- meters
    duration DOUBLE PRECISION NOT NULL, -- seconds
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_car_route FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_car_positions_car_id ON car_positions(car_id);
CREATE INDEX IF NOT EXISTS idx_car_positions_timestamp ON car_positions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_routes_car_id ON routes(car_id);
CREATE INDEX IF NOT EXISTS idx_cars_status ON cars(status);

-- Enable Realtime for car_positions table (CRITICAL for live updates)
-- You must also enable this in Supabase Dashboard > Database > Replication
ALTER PUBLICATION supabase_realtime ADD TABLE car_positions;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_cars_updated_at BEFORE UPDATE ON cars
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
