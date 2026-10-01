from functools import cached_property
from typing import Any

import googlemaps
import gspread

from bam_core.constants import MAYDAY_LOCATION, MAYDAY_RADIUS
from bam_core.lib import olc
from bam_core.settings import (
    GOOGLE_MAPS_API_KEY,
    GOOGLE_SERVICE_ACCOUNT_CONFIG,
)


class GoogleMaps:
    def __init__(self, api_key=GOOGLE_MAPS_API_KEY):
        self.api_key = api_key

    @cached_property
    def client(self):
        return googlemaps.Client(key=self.api_key)

    def get_lat_lng(self, address: str) -> tuple[float | None, float | None]:
        """
        Get the latitude and longitude of an address
        Args:
            address (str): The address to get the lat/lng for
        """
        geocode_results = self.client.geocode(address=address)
        if not geocode_results:
            return None, None
        loc = geocode_results[0]["geometry"]["location"]
        return loc["lat"], loc["lng"]

    def get_plus_code(self, lat: float | None, lng: float | None) -> str | None:
        """
        Get a de-specified plus code for a given address
        Args:
            address (str): The address to compute a code for
        """
        if not lat or not lng:
            return None
        return olc.encode(lat, lng)

    def get_place(
        self,
        address: str,
        location: str = MAYDAY_LOCATION,
        radius: float = MAYDAY_RADIUS,
        types: list[str] = ["premise", "subpremise", "geocode"],
        language: str = "en-US",
        strict_bounds: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get a place from the Google Maps API
        Args:
            address (str): The address to search for
            location (tuple): The location to search around
            radius (int): The radius to search within
            types (list): The types of places to search for
            language (str): The language to search in
            strict_bounds (bool): Whether to use strict bounds
        """
        return self.client.places_autocomplete(
            address,
            location=location,
            radius=radius,
            types=types,
            language=language,
            strict_bounds=strict_bounds,
        )

    def get_normalized_address(self, address: str) -> dict[str, Any]:
        """
        Normalize an address using the Google Maps API
        Args:
            address (str): The address to normalize
        """
        return self.client.addressvalidation(address)
