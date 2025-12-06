# WHEN-RAIN-BE/main.py

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import datetime
import time 
import asyncio # <--- ADDED for concurrent API calls
from typing import List

# Import Pydantic models and service functions
from pydantic import BaseModel
from services.maps_service import get_route_directions
from services.places_service import get_nearby_place_name # <--- NEW SERVICE IMPORT

# --- Pydantic Models ---

class RouteSegment(BaseModel):
    """Data structure for one weather-aware segment of the route."""
    # Location data
    lat: float
    lng: float
    place_name: str = "Traveling" # <--- NEW FIELD
    
    # Time data
    eta_timestamp: int  # Time in seconds since epoch (UNIX timestamp)
    human_readable_time: str
    
    # Placeholder for weather data (Step 3)
    weather_condition: str = "Pending"
    weather_icon: str = ""

class SegmentedRouteResponse(BaseModel):
    """The full response structure returned to the frontend."""
    start_time: str
    total_duration_seconds: int
    segments: List[RouteSegment]

# ---------------------------------------------

# --- Configuration & Initialization ---

# 1. Load environment variables FIRST
load_dotenv() 

# 2. Read the API key
MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
# OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY") # Will be used in Step 3

app = FastAPI(title="Weather Navigation Backend")

# CORS Configuration
origins = ["http://localhost:8080", "http://127.0.0.1:8080"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper Function for Segmentation and Timing (Step 2 Logic) ---

def segment_and_time_route(route_data: dict, start_time_iso: str) -> SegmentedRouteResponse:
    """
    Processes the raw Google Maps steps to create time-aware route segments.
    """
    
    departure_time = datetime.datetime.fromisoformat(start_time_iso)
    current_time_ms = time.time()
    
    segments_list = []
    accumulated_duration = 0
    
    steps = route_data.get('steps', [])
    total_duration_seconds = route_data.get('duration_seconds', 0)
    
    if not steps:
        return SegmentedRouteResponse(
            start_time=departure_time.strftime("%Y-%m-%d %I:%M:%S %p"),
            total_duration_seconds=0,
            segments=[]
        )

    # 1. Add the very START POINT (Point 1)
    start_lat = steps[0]['start_location']['lat']
    start_lng = steps[0]['start_location']['lng']

    segments_list.append(
        RouteSegment(
            lat=start_lat,
            lng=start_lng,
            eta_timestamp=int(current_time_ms), 
            human_readable_time=departure_time.strftime("%I:%M %p")
        )
    )
    
    # 2. Iterate through all subsequent steps (intermediate points)
    for step in steps:
        step_duration = step['duration']['value']
        accumulated_duration += step_duration
        
        segment_lat = step['end_location']['lat']
        segment_lng = step['end_location']['lng']
        
        eta_datetime = departure_time + datetime.timedelta(seconds=accumulated_duration)
        eta_timestamp = int(eta_datetime.timestamp())

        segments_list.append(
            RouteSegment(
                lat=segment_lat,
                lng=segment_lng,
                eta_timestamp=eta_timestamp,
                human_readable_time=eta_datetime.strftime("%I:%M %p")
            )
        )
        
    return SegmentedRouteResponse(
        start_time=departure_time.strftime("%Y-%m-%d %I:%M:%S %p"),
        total_duration_seconds=total_duration_seconds,
        segments=segments_list
    )


# --- Endpoint Definition (Step 1, 2, and Place Name Execution) ---

@app.get("/api/route", response_model=SegmentedRouteResponse)
async def get_route(
    origin: str, 
    destination: str,
    departure_time: str = Query(None, description="ISO 8601 formatted datetime for departure.") 
):
    """
    Calculates the driving route, segments it, estimates arrival times, and fetches nearby place names.
    """
    
    # Check 1: Ensure the API key is available
    if not MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Server Configuration Error: Maps API Key is missing.")

    # Determine departure time (use current time if none provided)
    if departure_time is None:
        departure_dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
        departure_time_iso = departure_dt.isoformat()
    else:
        try:
            departure_dt = datetime.datetime.fromisoformat(departure_time)
            departure_time_iso = departure_dt.isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid departure_time format. Use ISO 8601.")
            

    # 1. Route Calculation
    route_data = await get_route_directions(origin, destination, api_key=MAPS_API_KEY) 
    
    if route_data is None:
        raise HTTPException(status_code=404, detail="No route could be found or an external API error occurred.")

    # 2. Segmentation and Time Estimation 
    segmented_route = segment_and_time_route(route_data, departure_time_iso)

    # 3. Place Name Integration (Concurrent API calls)
    
    place_name_tasks = [] 
    
    for segment in segmented_route.segments:
        # Create a task for each segment to fetch the nearby place name
        place_task = get_nearby_place_name(
            lat=segment.lat,
            lng=segment.lng,
            api_key=MAPS_API_KEY # Reusing the Google API Key
        )
        place_name_tasks.append(place_task)

    # Wait for all place name API calls to complete concurrently
    place_name_results = await asyncio.gather(*place_name_tasks)

    # Update segments with place name data
    for i, name in enumerate(place_name_results):
        segmented_route.segments[i].place_name = name

    # Weather Integration (Step 3 will go here)

    return segmented_route