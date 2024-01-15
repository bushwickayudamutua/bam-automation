import argparse
from typing import Dict, Optional
from bam_core.lib.google import GoogleMaps
from bam_core.lib.nyc_planning_labs import NycPlanningLabs

COMMON_ZIPCODE_MISTAKES = {
    "112007": "11207",
}
# default bin response from nyc planning labs
DEFAULT_BIN_RESPONSES = ["3000000", "1000000"]

DEFAULT_CITY_STATE = "Brooklyn, NY"


def _fix_address(address: str) -> str:
    """
    Attempt to fix common mistakes in addresses
    """
    address = address.upper().strip()
    address = address.replace(" PISO", " FLOOR")
    address = address.replace(" APARTAMENTO", " APT")
    address = address.replace(" APTO", " APT")
    address = address.replace(" APRT", " APT")
    address = address.replace(" DE ", " ")

    if address.endswith("#"):
        address = address[:-1].strip()
    return address


def _fix_zip_code(zip_code: Optional[str]) -> str:
    """
    Attempt to fix common mistakes in zipcodes
    """
    return COMMON_ZIPCODE_MISTAKES.get(zip_code, zip_code)


def format_address(
    address: Optional[str] = None,
    city_state: Optional[str] = "",
    zipcode: Optional[str] = "",
    strict_bounds: bool = True,
) -> Dict[str, str]:
    """
    Format an address using the Google Maps API and the NYC Planning Labs API
    Args:
        address (str): The address to format
        city_state (str): The city and state to use if the address is missing
        zipcode (str): The zipcode to use if the address is missing
        strict_bounds (bool): Whether to use strict bounds of 10 miles from Mayday
    Returns:
        Dict[str, str]: The formatted address, bin, and accuracy
    """
    # connect to APIs
    gmaps = GoogleMaps()
    nycpl = NycPlanningLabs()

    response = {
        "cleaned_address": "",
        "bin": "",
        "cleaned_address_accuracy": "No result",
    }
    # don't do anything for missing addresses
    if not address or not address.strip():
        return response

    # common address mistakes/translations
    address = _fix_address(address)

    # format address for query
    address_query = f"{address.strip()}, {city_state.strip() or DEFAULT_CITY_STATE} {_fix_zip_code(zipcode.strip())}".strip().upper()

    # lookup address using Google Maps Places API
    place_response = gmaps.get_place(
        address_query, strict_bounds=strict_bounds
    )
    if len(place_response):
        no_place_response = False
        place_address = place_response[0]["description"]
        if "subpremise" in place_response[0]["types"]:
            response["cleaned_address_accuracy"] = "Apartment"
        elif "premise" in place_response[0]["types"]:
            response["cleaned_address_accuracy"] = "Building"
        else:
            # ignore geocode results if not at the level of a building or apartment
            return response

    # if no results, use the original address
    else:
        no_place_response = True
        place_address = address_query

    # lookup the cleaned address using the google maps address validation api
    norm_address_result = gmaps.get_normalized_address(place_address)

    norm_address = norm_address_result.get("result", {})
    if no_place_response:
        # if no place response, use granularity from the norm address response
        granularity = norm_address.get("verdict", {}).get(
            "validationGranularity", ""
        )
        input_granularity = norm_address.get("verdict", {}).get(
            "inputGranularity", ""
        )
        if granularity == "SUB_PREMISE":
            response["cleaned_address_accuracy"] = "Apartment"
        # never confirm apartment-level granularity based on input-level granularity
        elif granularity == "PREMISE" or input_granularity.endswith("PREMISE"):
            response["cleaned_address_accuracy"] = "Building"

    usps_data = norm_address.get("uspsData", {}).get("standardizedAddress", {})
    cleaned_address = (
        usps_data.get("firstAddressLine", "")
        + " "
        + usps_data.get("cityStateZipAddressLine", "")
    ).strip()
    if not cleaned_address:
        # if no USPS data, use the formatted address
        cleaned_address = (
            norm_address.get("address", {}).get("formattedAddress", "").upper()
        )

        # if no formatted address, use the place address
        if not cleaned_address:
            cleaned_address = place_address.upper()

    # perform some standardization on the formatted address
    cleaned_address = cleaned_address.replace(" # ", " APT ")

    # return the cleaned address and
    # lookup the bin using the nyc planning labs api
    # only if the granularity is returned
    if response["cleaned_address_accuracy"] != "No result":
        response["cleaned_address"] = cleaned_address
        nycpl_response = nycpl.search(cleaned_address)
        features = nycpl_response.get("features", [])
        if len(features):
            bin = (
                features[0]
                .get("properties", {})
                .get("addendum", {})
                .get("pad", {})
                .get("bin", "")
            )
            if bin and str(bin) not in DEFAULT_BIN_RESPONSES:
                response["bin"] = bin
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="bam-geo")
    parser.add_argument("-a", "--address", help="The address to format")
    parser.add_argument(
        "-c",
        "--city-state",
        help="The city and state to use.",
        default="New York",
    )
    parser.add_argument(
        "-z", "--zipcode", help="The zipcode to use.", default=""
    )
    parser.add_argument(
        "-ns",
        "--no-strict-bounds",
        help="Whether to use strict bounds of 10 miles from Mayday",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    from pprint import pprint

    pprint(
        format_address(
            args.address,
            args.city_state,
            args.zipcode,
            not args.no_strict_bounds,
        )
    )
