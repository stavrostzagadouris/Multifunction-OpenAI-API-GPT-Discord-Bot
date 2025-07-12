import requests
import math
import json
import os
from datetime import datetime

# Dictionary to decode the aircraft category from the state vector.
# Based on the official OpenSky Network documentation and common ADS-B standards.
AIRCRAFT_CATEGORIES = {
    0: 'No information',
    1: 'No ADS-B Emitter Category Information',
    2: 'Light (< 15500 lbs)',
    3: 'Small (15500 to 75000 lbs)',
    4: 'Large (75000 to 300000 lbs)',
    5: 'High-Vortex Large',
    6: 'Heavy (> 300000 lbs)',
    7: 'High-Performance',
    8: 'Rotorcraft',
    9: 'Glider / sailplane',
    10: 'Lighter-than-air',
    11: 'Parachutist / Skydiver',
    12: 'Ultralight / hang-glider / paraglider',
    13: 'Reserved',
    14: 'Unmanned Aerial Vehicle',
    15: 'Space / Trans-atmospheric vehicle',
    16: 'Surface Vehicle – Emergency Vehicle',
    17: 'Surface Vehicle – Service Vehicle',
    18: 'Point Obstacle',
    19: 'Cluster Obstacle',
    20: 'Line Obstacle'
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial bearing from point A to point B.
    Returns bearing in degrees (0-360).
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lon = lon2_rad - lon1_rad

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - (math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

def degrees_to_cardinal(d: float | None) -> str:
    """
    Converts a bearing in degrees to a 16-point compass rose direction.
    """
    if d is None:
        return "N/A"
    dirs = [
        "North", "North-Northeast", "Northeast", "East-Northeast",
        "East", "East-Southeast", "Southeast", "South-Southeast",
        "South", "South-Southwest", "Southwest", "West-Southwest",
        "West", "West-Northwest", "Northwest", "North-Northwest"
    ]
    # Each direction covers 360/16 = 22.5 degrees.
    # We add 11.25 to center the N direction around 0.
    val = int((d + 11.25) / 22.5)
    return dirs[val % 16]

def get_flight_destination(icao24: str, last_contact_ts: int):
    """
    Fetches the estimated arrival airport for a given aircraft by making a
    separate API call. This adds latency but provides valuable route data.
    Returns 'N/A' if no data is found or an error occurs.
    """
    begin = last_contact_ts - 43200  # 12 hours ago
    end = last_contact_ts + 43200    # 12 hours from now
    url = f"https://opensky-network.org/api/flights/aircraft?icao24={icao24}&begin={begin}&end={end}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        flights = response.json()
        if flights:
            return flights[-1].get('estArrivalAirport', 'N/A')
    except requests.RequestException:
        return 'N/A' # Don't let a failure here stop the main process
    return 'N/A'

def get_aircraft_metadata(icao24: str, cache: dict) -> str:
    """
    Fetches aircraft metadata (manufacturer and model) from the OpenSky aircraft database.
    Uses a cache to avoid redundant API calls for the same aircraft within a single run.

    Args:
        icao24 (str): The ICAO24 address of the aircraft.
        cache (dict): A dictionary to cache results for the duration of the script run.

    Returns:
        str: A formatted string with manufacturer and model, or a fallback message.
    """
    if icao24 in cache:
        return cache[icao24]

    url = f"https://opensky-network.org/api/metadata/aircraft/icao/{icao24}"
    try:
        # This public metadata endpoint does not require authentication.
        response = requests.get(url, timeout=5)
        if response.status_code == 404:
            cache[icao24] = 'Unknown Model'
            return cache[icao24]
        
        response.raise_for_status()
        metadata = response.json()
        
        manufacturer = (metadata.get('manufacturerName') or '').strip()
        model = (metadata.get('model') or '').strip()

        result = f"{manufacturer} {model}".strip() if manufacturer or model else 'Unknown Model'
        cache[icao24] = result
        return result
    except requests.RequestException:
        cache[icao24] = 'Metadata N/A'
        return cache[icao24]

def get_oauth_token(client_id: str, client_secret: str) -> str | None:
    """
    Obtains an OAuth2 access token from the OpenSky Network authentication server.

    Args:
        client_id (str): Your OpenSky API client ID.
        client_secret (str): Your OpenSky API client secret.

    Returns:
        str | None: The access token if successful, otherwise None.
    """
    auth_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        response = requests.post(auth_url, data=payload, timeout=10)
        response.raise_for_status()  # Will raise an exception for 4xx/5xx status codes
        token_data = response.json()
        return token_data.get("access_token")
    except requests.RequestException:
        return None

def get_flights_around_location(
    latitude: float,
    longitude: float,
    radius_km: float
) -> str:
    """
    Fetches real-time flight information from the OpenSky Network API around a given location
    within a specified radius and returns it as a human-readable string.

    This function calculates a square bounding box based on the provided center coordinates
    and radius. It authenticates using OAuth2 and queries the OpenSky Network API.
    Only airborne aircraft details are included in the returned string.

    Args:
        latitude (float): The latitude of your current location.
        longitude (float): The longitude of your current location.
        radius_km (float): The radius in kilometers around your location to search for flights.

    Returns:
        str: A string containing a summary of airborne flights found, including their
             callsign, country, position, altitude, speed, heading,
             distance from your location, and bearing from your location.
             Returns an informative error message if the API request fails or
             no airborne flights are found.
    """
    # --- Hardcoded Credentials ---
    # As requested, credentials are hardcoded here.
    # WARNING: This is not a recommended security practice for most applications.
    #
    # !!! IMPORTANT: Replace the placeholder values below with your actual credentials. !!!
    client_id = os.environ['flight_id']
    client_secret = os.environ['flight_secret']
    # Step 1: Get the OAuth2 access token
    token = get_oauth_token(client_id, client_secret)
    if not token:
        return ("Authentication failed. Could not retrieve access token from OpenSky. "
                "Please check your hardcoded client_id and client_secret.")

    # Initialize a cache for aircraft metadata to reduce API calls within a single run.
    aircraft_metadata_cache = {}

    # Earth's approximate radius in kilometers for calculations.
    R_earth = 6371

    # Calculate the change in latitude degrees for the given radius.
    delta_lat_deg = (radius_km / R_earth) * (180 / math.pi)

    # Convert the center latitude to radians for accurate longitude calculation.
    lat_rad = math.radians(latitude)
    delta_lon_deg = (radius_km / (R_earth * math.cos(lat_rad))) * (180 / math.pi)

    # Determine the bounding box coordinates (min/max latitude and longitude).
    min_lat = latitude - delta_lat_deg
    max_lat = latitude + delta_lat_deg
    min_lon = longitude - delta_lon_deg
    max_lon = longitude + delta_lon_deg

    url = "https://opensky-network.org/api/states/all"

    params = {
        "lamin": min_lat,
        "lamax": max_lat,
        "lomin": min_lon,
        "lomax": max_lon,
    }

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data or not data.get("states"):
            return (f"No flight information found within {radius_km} km radius around "
                    f"({latitude:.4f}, {longitude:.4f}) at this time. "
                    f"The OpenSky Network might not have data for this area or period, "
                    f"or the API returned an empty set.")

        flight_details = []
        for s in data["states"]:
            icao24 = s[0]
            callsign = s[1].strip() if s[1] else "N/A"
            origin_country = s[2]
            last_contact_timestamp = s[4]
            current_longitude = s[5]
            current_latitude = s[6]
            baro_altitude_meters = s[7]
            on_ground = s[8]
            velocity_mps = s[9]
            heading_degrees = s[10]
            
            category_code = s[17] if len(s) > 17 and s[17] is not None else None
            
            category_str = AIRCRAFT_CATEGORIES.get(category_code, 'Unknown Type')
            is_helicopter = (category_code == 8)

            # Destination airport is disabled for free trial
            destination_airport = "unavailable (due to free trial limitations)"

            # Fetch aircraft make and model.
            # NOTE: This makes an additional API call per unique aircraft, which can increase latency.
            # A cache is used to prevent duplicate lookups during this run.
            model_info = get_aircraft_metadata(icao24, aircraft_metadata_cache)

            if on_ground:
                continue

            altitude_feet = (baro_altitude_meters * 3.28084) if baro_altitude_meters is not None else None
            velocity_kmh = (velocity_mps * 3.6) if velocity_mps is not None else None
            last_contact_str = datetime.fromtimestamp(last_contact_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')

            # Calculate distance and bearing from your location
            distance_from_me = haversine_distance(latitude, longitude, current_latitude, current_longitude)
            bearing_from_me = calculate_bearing(latitude, longitude, current_latitude, current_longitude)

            flight_details.append({
                "callsign": callsign,
                "icao24": icao24,
                "origin_country": origin_country,
                "model_info": model_info,
                "category_str": category_str,
                "is_helicopter": is_helicopter,
                "last_contact_str": last_contact_str,
                "current_latitude": current_latitude,
                "current_longitude": current_longitude,
                "altitude_feet": altitude_feet,
                "velocity_kmh": velocity_kmh,
                "heading_degrees": heading_degrees,
                "distance_from_me": distance_from_me,
                "bearing_from_me": bearing_from_me,
            })

        if not flight_details:
            return (f"No airborne flight information found within {radius_km} km radius around "
                    f"({latitude:.4f}, {longitude:.4f}) at this time. "
                    f"All detected aircraft might be on the ground or no data is available.")

        # Sort flights by distance (closest first). Handle None for distance gracefully.
        flight_details.sort(key=lambda f: f['distance_from_me'] if f['distance_from_me'] is not None else float('inf'))

        # Build the formatted string output from the sorted list
        output_strings = []
        for flight in flight_details:
            altitude_str = f"{flight['altitude_feet']:.0f}" if flight['altitude_feet'] is not None else "N/A"
            velocity_str = f"{flight['velocity_kmh']:.0f}" if flight['velocity_kmh'] is not None else "N/A"
            heading_str = f"{flight['heading_degrees']:.1f}" if flight['heading_degrees'] is not None else "N/A"
            distance_str = f"{flight['distance_from_me']:.2f}" if flight['distance_from_me'] is not None else "N/A"
            bearing_degrees_str = f"{flight['bearing_from_me']:.1f}°" if flight['bearing_from_me'] is not None else "N/A"
            bearing_cardinal_str = degrees_to_cardinal(flight['bearing_from_me'])

            detail = (
                f"  - Callsign: {flight['callsign']}, ICAO24: {flight['icao24']}, Country: {flight['origin_country']}\n"
                f"    Distance from you: {distance_str} km, Look in this direction: {bearing_cardinal_str} ({bearing_degrees_str})\n"
                f"    Model: {flight['model_info']}\n"
                f"    Type: {flight['category_str']}{' 🚁' if flight['is_helicopter'] else ' ✈️'}\n"
                f"    Position: Lat {flight['current_latitude']:.4f}, Lon {flight['current_longitude']:.4f}\n"
                f"    Altitude: {altitude_str} feet, Speed: {velocity_str} km/h, Heading: {heading_str}°\n"
            )
            output_strings.append(detail)

        summary_string = (
            f"Flight information within {radius_km} km radius of your location "
            f"(Lat: {latitude:.4f}, Lon: {longitude:.4f}):\n"
            f"Total airborne flights found: {len(output_strings)}\n\n" +
            "\n".join(output_strings)
        )
        return summary_string

    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 401:
            return ("HTTP error 401: Unauthorized. Your access token may be invalid or expired. "
                    "This can happen if your hardcoded client credentials are wrong or the token has timed out (30 mins).")
        else:
            return f"HTTP error occurred while fetching flight data: {http_err} - Response: {response.text}"
    except requests.exceptions.ConnectionError as conn_err:
        return f"Connection error occurred: {conn_err} - Could not connect to OpenSky API. Please check your internet connection."
    except requests.exceptions.Timeout as timeout_err:
        return f"Timeout error occurred: {timeout_err} - OpenSky API request timed out after 15 seconds."
    except requests.exceptions.RequestException as req_err:
        return f"An unexpected request error occurred while fetching flight data: {req_err}"
    except json.JSONDecodeError as json_err:
        return f"Error decoding JSON response from OpenSky API: {json_err}. Raw response: {response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"



if __name__ == "__main__":
    print("This is meant to be run within a bot.\nYou'll never actually see this :p")
    