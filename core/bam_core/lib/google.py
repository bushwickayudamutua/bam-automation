import json
from typing import Any, Dict, List

import gspread
import googlemaps

import olc

from bam_core.settings import (
    GOOGLE_MAPS_API_KEY,
    GOOGLE_SERVICE_ACCOUNT_CONFIG,
)
from bam_core.constants import MAYDAY_LOCATION, MAYDAY_RADIUS
from bam_core.utils.etc import retry


class GoogleMaps(object):
    def __init__(self, api_key=GOOGLE_MAPS_API_KEY):
        self.client = googlemaps.Client(key=api_key)

    def get_pluscode(self, address):
        """
        Get a de-specified plus code for a given address
        Args:
            address (str): The address to compute a code for
        """
        geocode = self.client.geocode(address=address)
        loc = geocode['results'][0]['geometry']['location']
        lat, lng = loc['lat'], loc['lng']
        
        return olc.encode(lat, lng)

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


class GoogleSheets(object):
    def __init__(self):
        pass

    @property
    def client(self):
        return gspread.service_account_from_dict(GOOGLE_SERVICE_ACCOUNT_CONFIG)

    @retry(times=5, wait=10, backoff=1.5)
    def upload_to_sheet(
        self,
        sheet_name: str,
        sheet_index: int,
        data: List[Dict[str, Any]],
        overwrite: bool = True,
        header: bool = True,
    ):
        """
        Upload a list of dictionaries to a Google Sheet
        Args:
            sheet_name (str): The name of the sheet to upload to
            sheet_index (int): The index of the sheet to upload to
            data (list): List of dictionaries to upload
            overwrite (bool): Whether to replace all data in the sheet
            header (bool): Whether to write the header to the sheet
        """
        sheet = self.client.open(sheet_name).get_worksheet(sheet_index)
        if overwrite:
            sheet.clear()

        if header:
            headers = list(data[0].keys())
            sheet.append_row(headers)

        # append data to sheet
        sheet.append_rows([list(row.values()) for row in data])
