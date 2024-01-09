import googlemaps

from bam_core.settings import GOOGLE_MAPS_API_KEY
from bam_core.constants import MAYDAY_LOCATION, MAYDAY_RADIUS


class GoogleMaps(object):
    def __init__(self, api_key=GOOGLE_MAPS_API_KEY):
        self.client = googlemaps.Client(key=api_key)

    def get_place(
        self,
        address,
        location=MAYDAY_LOCATION,
        radius=MAYDAY_RADIUS,
        types=["premise", "subpremise", "geocode"],
        language="en-US",
        strict_bounds=True,
    ):
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

    def get_normalized_address(self, address):
        """
        Normalize an address using the Google Maps API
        Args:
            address (str): The address to normalize
        """
        return self.client.addressvalidation(address)
