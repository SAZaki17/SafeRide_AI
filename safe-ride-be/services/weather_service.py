import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather" # Using OpenWeatherMap as example

# --- RISK SCORING LOGIC ---
def calculate_risk_score(description: str, temp_c: float) -> int:
    """
    Assigns a numerical risk score (0-10) based on weather condition and temperature.
    0 = Safest, 10 = Highest Risk.
    """
    description = description.lower()
    score = 0
    
    # Risk based on condition
    if 'rain' in description or 'drizzle' in description:
        score += 3  # Moderate risk for wet roads
    if 'heavy rain' in description or 'thunderstorm' in description:
        score += 6  # High risk for flooding/low visibility
    if 'snow' in description or 'sleet' in description:
        score += 8  # Very high risk for icy roads
    if 'fog' in description or 'mist' in description:
        score += 4  # Low visibility risk
    
    # Risk based on temperature extremes
    if temp_c > 35: # Extreme heat
        score += 3
    elif temp_c < 0: # Icy conditions
        score += 5
    
    # Ensure score stays within bounds
    return min(10, score)


# --- MODEL FOR WEATHER RESPONSE (UPDATED) ---
class WeatherForecast:
    def __init__(self, description: str, icon: str, temperature: float, risk_score: int):
        self.description = description
        self.icon = icon
        self.temperature = temperature
        self.risk_score = risk_score # NEW FIELD

async def get_weather_forecast(lat: float, lng: float, timestamp: int) -> WeatherForecast:
    """
    Fetches real-time weather data for a given location and time and calculates risk score.
    """
    if not WEATHER_API_KEY:
        print("--- WEATHER API KEY MISSING ---")
        return WeatherForecast(
            description="Weather data N/A (API Key Missing)", 
            icon="❓", 
            temperature=0.0,
            risk_score=0 # Default to 0 if no data
        )

    params = {
        "lat": lat,
        "lon": lng,
        "appid": WEATHER_API_KEY,
        "units": "metric", # Get temperature in Celsius
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(WEATHER_API_URL, params=params)
            response.raise_for_status() # Raises exception for 4xx/5xx status codes
            data = response.json()
            
            # Simple parsing of the OpenWeatherMap response
            main_weather = data['weather'][0]
            temp = data['main']['temp']
            
            # Calculate Risk Score
            risk = calculate_risk_score(main_weather['description'], temp)
            
            return WeatherForecast(
                description=main_weather['description'].title(),
                icon=main_weather['icon'],
                temperature=temp,
                risk_score=risk # RETURN THE NEW FIELD
            )

    except httpx.HTTPStatusError as e:
        print(f"Weather API HTTP Error for {lat},{lng}: {e}")
        return WeatherForecast(
            description=f"Error {e.response.status_code}", 
            icon="❌", 
            temperature=0.0,
            risk_score=10 # Assign max risk on API failure/bad data
        )
    except Exception as e:
        print(f"Weather API General Error: {e}")
        return WeatherForecast(
            description="Connection Failed", 
            icon="⚠️", 
            temperature=0.0,
            risk_score=10 # Assign max risk on connection failure
        )