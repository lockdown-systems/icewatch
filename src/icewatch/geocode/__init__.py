import logging
import os
from functools import partial
from typing import Callable

import requests

from icewatch.geocode.mapbox import query_mapbox
from icewatch.geocode.types import Coordinates

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

geocode_address: Callable[[str, requests.Session | None], Coordinates | None]

MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN")
if MAPBOX_ACCESS_TOKEN:
    geocode_address = partial(query_mapbox, MAPBOX_ACCESS_TOKEN)
    logger.info("MAPBOX_ACCESS_TOKEN found, using Mapbox api")
else:
    from icewatch.geocode.nomination import geocode_address

    logger.warning("No MAPBOX_ACCESS_TOKEN found, falling back to nomination")


__all__ = ["geocode_address"]
