import requests
from icewatch.geocode.types import Coordinates

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "icewatch/1.0 (collective@lockdown.systems)"


def geocode_address(
    address: str, session: requests.Session | None = None
) -> Coordinates | None:
    params = {
        "q": address,
        "format": "json",
        "limit": "1",  # set as string to match request param type
    }
    headers = {"User-Agent": USER_AGENT}
    s = session or requests.Session()
    response = s.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    results = response.json()
    if results:
        return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
    return None
