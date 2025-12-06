# WHEN-RAIN-BE/services/maps_service.py

import httpx

GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

async def get_route_directions(origin: str, destination: str, api_key: str):
    """
    Calls the Google Directions API to get the route steps and polyline,
    using the provided api_key.
    """
    
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": api_key
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
            response.raise_for_status() 
            
            data = response.json()
            
            # --- GOOGLE API RESPONSE STATUS: DEBUG PRINT ---
            print(f"--- GOOGLE API RESPONSE STATUS: {data.get('status')} ---") 
            
            if data.get('status') != 'OK':
                print(f"Google Directions API Error: {data.get('status')} - {data.get('error_message')}")
                return None
                
            # Extract the first route's steps and the overall polyline string
            route = data['routes'][0]['legs'][0]
            polyline = data['routes'][0]['overview_polyline']['points']
            
            return {
                "steps": route['steps'],
                "polyline": polyline,
                "duration_seconds": route['duration']['value']
            }

        except httpx.HTTPStatusError as e:
            print(f"HTTP Error calling Google API: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None