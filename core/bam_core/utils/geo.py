from typing import Dict, Optional
from bam_core.lib.google import GoogleMaps
from bam_core.lib.nyc_planning_labs import NycPlanningLabs

COMMON_ZIPCODE_MISTAKES = {
    "112007": "11207",
}


def _fix_zip_code(zip_code: Optional[str]) -> str:
    """
    Attempt to fix common mistakes in zipcodes
    """
    return COMMON_ZIPCODE_MISTAKES.get(zip_code, zip_code)


def format_address(
    address: Optional[str] = None,
    city_state: Optional[str] = "",
    zipcode: Optional[str] = "",
) -> Dict[str, str]:
    """
    Format an address using the Google Maps API and the NYC Planning Labs API
    Args:
        address (str): The address to format
        city_state (str): The city and state to use if the address is missing
        zipcode (str): The zipcode to use if the address is missing
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

    # format address for query
    address_query = f"{address.strip()} {city_state.strip() or 'New York'} {_fix_zip_code(zipcode.strip())}".strip().upper()

    # lookup address using Google Maps Places API
    place_response = gmaps.get_place(address_query)
    if not len(place_response):
        return response

    place_address = place_response[0]["description"]
    if "subpremise" in place_response[0]["types"]:
        response["cleaned_address_accuracy"] = "Apartment"
    elif "premise" in place_response[0]["types"]:
        response["cleaned_address_accuracy"] = "Building"
    else:
        # ignore geocode results if not at the level of a building or apartment
        return response

    # lookup the cleaned address using the google maps address validation api
    norm_address_result = gmaps.get_normalized_address(place_address)

    norm_address = norm_address_result.get("result", {})
    ## TODO: Figure out if we should report granularity from here or places API
    # granularity = norm_address.get("verdict", {}).get("validationGranularity", "")
    # if granularity == "SUB_PREMISE":
    #     response["cleaned_address_accuracy"] = "Apartment"
    # elif granularity == "PREMISE":
    #     response["cleaned_address_accuracy"] = "Building"

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
    response["cleaned_address"] = cleaned_address

    # lookup the bin using the nyc planning labs api
    nycpl_response = nycpl.search(cleaned_address)
    response["bin"] = (
        nycpl_response.get("features", [{}])[0]
        .get("properties", {})
        .get("addendum", {})
        .get("pad", {})
        .get("bin", "")
    )
    return response
