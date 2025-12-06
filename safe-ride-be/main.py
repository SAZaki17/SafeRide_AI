import os
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables (must be first)
load_dotenv()

# --- SERVICES IMPORT ---
# Note: Ensure all these service files are using the Python 'typing' imports:
# from typing import Optional, List, Dict, Any, Tuple
from services import maps_service
from services import places_service
from services.weather_service import get_weather_forecast, WeatherForecast

# --- MODELS ---
# The Pydantic model for a single segment of the route
class Segment(BaseModel):
    lat: float
    lng: float
    eta_timestamp: int
    human_readable_time: str
    place_name: str
    # NEW fields for weather data
    weather_condition: str = "N/A"
    weather_icon: str = "N/A"
    temperature: float = 0.0
    risk_score: int = 0  # Added field to align with weather_service.py

# The Pydantic model for the final response
class SegmentedRouteResponse(BaseModel):
    start_time: str
    total_duration_seconds: int
    polyline_encoded: str
    segments: List[Segment]

# --- FASTAPI APP INITIALIZATION ---
app = FastAPI(
    title="Weather Navigation Backend",
    description="Provides segmented route data integrated with place names and weather forecasts.",
)

# --- COORDINATOR ROUTE ---
@app.get(
    "/api/route", 
    response_model=SegmentedRouteResponse,
    summary="Get route segments with real-time place names and weather",
    status_code=status.HTTP_200_OK
)
async def get_route(
    origin: str = Query(..., description="Starting point for the route"),
    destination: str = Query(..., description="End point for the route"),
    departure_time: Optional[str] = Query(None, description="ISO 8601 timestamp (e.g., 2025-12-07T14:00:00+08:00)")
):
    try:
        # STEP 1: Get the route and segments from Maps Service
        route_segments, raw_response = await maps_service.get_segmented_route(
            origin, destination, departure_time
        )
        
        # Ensure we have segments before proceeding
        if not route_segments or 'routes' not in raw_response:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="No route could be found or an external API error occurred."
            )

        # Safely extract core route data from the first leg
        leg = raw_response['routes'][0]['legs'][0]
        
        # --- CRITICAL FIX FOR 'departure_time' KEYERROR ---
        # The 'departure_time' object is only present if a specific time was requested.
        # Fall back to "Now" if it's missing (i.e., when using the default 'now' time).
        if 'departure_time' in leg:
            start_time_text = leg['departure_time']['text']
        else:
            start_time_text = "Now"
        # ---------------------------------------------------

        total_duration_seconds = leg['duration']['value']
        polyline_encoded = raw_response['routes'][0]['overview_polyline']['points']

        # STEP 2 & 3: Concurrently fetch Place Names and Weather Forecasts
        # Create a list of async tasks for Place Name lookup
        place_name_tasks = [
            places_service.get_place_name(segment.lat, segment.lng)
            for segment in route_segments
        ]
        
        # Create a list of async tasks for Weather lookup
        weather_tasks = [
            get_weather_forecast(segment.lat, segment.lng, segment.eta_timestamp)
            for segment in route_segments
        ]
        
        # Run all concurrent tasks together for maximum speed
        results = await asyncio.gather(*place_name_tasks, *weather_tasks)
        
        # Split results back into their respective lists
        num_segments = len(route_segments)
        place_names = results[:num_segments]
        weather_forecasts: List[WeatherForecast] = results[num_segments:]

        # STEP 4: COORDINATION - Merge all data into the final Segment models
        final_segments: List[Segment] = []
        for segment, place_name, weather_data in zip(
            route_segments, place_names, weather_forecasts
        ):
            final_segments.append(
                Segment(
                    lat=segment.lat,
                    lng=segment.lng,
                    # Note: maps_service SegmentData's eta_timestamp is now duration_seconds
                    eta_timestamp=segment.eta_timestamp, 
                    human_readable_time=segment.human_readable_time,
                    place_name=place_name,
                    weather_condition=weather_data.description,
                    weather_icon=weather_data.icon,
                    temperature=weather_data.temperature,
                    risk_score=weather_data.risk_score # Added risk_score
                )
            )

        # STEP 5: Return the combined response
        return SegmentedRouteResponse(
            start_time=start_time_text,
            total_duration_seconds=total_duration_seconds,
            polyline_encoded=polyline_encoded,
            segments=final_segments
        )

    except HTTPException:
        # Re-raise explicit HTTP exceptions (like 404 from maps_service)
        raise
    except Exception as e:
        print(f"Server error during processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal server error occurred. Please check API keys and service logs."
        )