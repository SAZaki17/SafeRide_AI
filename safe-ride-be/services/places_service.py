# WHEN-RAIN-BE/services/places_service.py

import httpx

# We will use the Nearby Search (Legacy) endpoint first
GOOGLE_PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DEFAULT_SEARCH_RADIUS = 1000 # Search within 1000 meters (1 km)

async def get_reverse_geocode_address(location_str: str, api_key: str) -> str:
    """
    Fallback: Reverse Geocodes the coordinates to get a formatted address component.
    """
    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    
    params = {
        "latlng": location_str,
        "result_type": "locality|neighborhood|route", # Prioritize these types
        "key": api_key
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(GOOGLE_GEOCODE_URL, params=params)
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                # Return the formatted address of the most relevant result
                return data['results'][0]['formatted_address']
                
            return "No Place Name Found"
        except Exception as e:
            # print(f"Places API Error (Reverse Geocoding): {e}")
            return "Unknown Area"


async def get_nearby_place_name(lat: float, lng: float, api_key: str) -> str:
    """
    Calls the Google Places API to find a nearby prominent place name.
    Falls back to reverse geocoding if no Point of Interest is found.
    """
    
    location_str = f"{lat},{lng}"
    
    params = {
        "location": location_str,
        "radius": DEFAULT_SEARCH_RADIUS,
        "rankby": "prominence", 
        "type": "point_of_interest", 
        "key": api_key
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(GOOGLE_PLACES_NEARBY_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 1. Try Nearby Search first (best for landmarks/POIs)
            if data.get('status') == 'OK' and data.get('results'):
                return data['results'][0]['name']

            # 2. Fall back to Reverse Geocoding for a more general address/area name
            return await get_reverse_geocode_address(location_str, api_key)

        except Exception as e:
            # print(f"Places API Error (Nearby Search): {e}")
            return "Unknown Area"