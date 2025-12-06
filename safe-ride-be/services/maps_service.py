# SAFERIDE_AI/safe-ride-be/services/maps_service.py

import os
import httpx
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List # Added typing imports
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

# --- MODEL FOR SEGMENT DATA ---
class SegmentData:
    def __init__(self, lat: float, lng: float, eta_timestamp: int, human_readable_time: str):
        self.lat = lat
        self.lng = lng
        self.eta_timestamp = eta_timestamp
        self.human_readable_time = human_readable_time

# --- HELPER FUNCTION FOR TIME CONVERSION ---
def convert_iso_to_unix(iso_time_str: str) -> int:
    """Converts an ISO 8601 datetime string to a Unix timestamp (seconds)."""
    try:
        # datetime.fromisoformat handles the timezone offset
        dt_object = datetime.fromisoformat(iso_time_str)
        return int(dt_object.timestamp())
    except ValueError:
        # Fallback if parsing fails, just use current time
        return int(time.time())

# --- GOOGLE API CALLER ---
async def get_route_directions(origin: str, destination: str, api_key: str, departure_time: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Calls the Google Directions API to get the route steps and raw response.
    """
    
    if not api_key:
        print("GOOGLE_MAPS_API_KEY is not set.")
        return None
        
    # 1. Start with 'now' as the default departure time
    final_departure_time: Any = "now" # Will hold "now" (str) or timestamp (int)
    
    if departure_time:
        # 2. If a time is provided (ISO 8601 string), convert it to a UNIX timestamp (integer)
        final_departure_time = convert_iso_to_unix(departure_time)
        
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": api_key,
        # Use the converted UNIX timestamp or the string "now"
        "departure_time": final_departure_time 
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
            response.raise_for_status() 
            
            data = response.json()
            
            if data.get('status') != 'OK':
                print(f"Google Directions API Error: {data.get('status')} - {data.get('error_message')}")
                return None
            
            return data

        except httpx.HTTPStatusError as e:
            # This handles the 400 Bad Request if the key or parameters are fundamentally wrong
            print(f"HTTP Error calling Google API: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

# --- ROUTE SEGMENTATION LOGIC ---
async def get_segmented_route(
    origin: str, 
    destination: str, 
    departure_time: Optional[str] = None
) -> Tuple[List[SegmentData], Dict[str, Any]]:
    """
    Calls Google Directions, segments the route by time intervals, and calculates ETA for each segment.
    """
    
    raw_response = await get_route_directions(origin, destination, GOOGLE_MAPS_API_KEY, departure_time)
    
    if not raw_response or not raw_response.get('routes'):
        return [], {}

    route = raw_response['routes'][0]['legs'][0]
    steps = route['steps']
    
    # 1. Determine the actual route start time (as a Python datetime object)
    # Use the 'value' timestamp if present, otherwise use current time as fallback
    start_time_value = route.get('departure_time', {}).get('value', int(time.time()))
    current_time_dt = datetime.fromtimestamp(start_time_value)
    
    # 2. Define the segmentation interval (e.g., every 5 minutes/300 seconds)
    SEGMENT_INTERVAL_SECONDS = 300 
    
    segmented_data: List[SegmentData] = []
    
    # Accumulators for time and distance across the route
    cumulative_duration_seconds = 0
    
    for step in steps:
        # Get coordinates for the start of the step
        lat = step['start_location']['lat']
        lng = step['start_location']['lng']
        duration = step['duration']['value']
        
        # Calculate ETA for the start of this step
        eta_seconds = start_time_value + cumulative_duration_seconds
        eta_dt = current_time_dt + timedelta(seconds=cumulative_duration_seconds)
        
        # Check if we should place a segment marker here
        # Condition: If it's the first segment, OR if 300 seconds have passed since the last segment
        if not segmented_data or (cumulative_duration_seconds - segmented_data[-1].eta_timestamp) >= SEGMENT_INTERVAL_SECONDS:
            segmented_data.append(
                SegmentData(
                    lat=lat,
                    lng=lng,
                    eta_timestamp=cumulative_duration_seconds,
                    human_readable_time=eta_dt.strftime("%I:%M %p, %a, %b %d")
                )
            )
        
        cumulative_duration_seconds += duration

    # Add the final destination point (end of the last step)
    last_step = steps[-1]
    # Use the total duration of the leg for the final point
    final_duration_seconds = route['duration']['value']
    final_eta_dt = current_time_dt + timedelta(seconds=final_duration_seconds)
    
    segmented_data.append(
        SegmentData(
            lat=last_step['end_location']['lat'],
            lng=last_step['end_location']['lng'],
            eta_timestamp=final_duration_seconds,
            human_readable_time=final_eta_dt.strftime("%I:%M %p, %a, %b %d")
        )
    )

    return segmented_data, raw_response