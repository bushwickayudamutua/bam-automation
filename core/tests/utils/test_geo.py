from bam_core.utils.geo import format_address
import unittest
from unittest.mock import patch


class TestFormatAddress(unittest.TestCase):
    @patch("bam_core.utils.geo.GoogleMaps.get_place")
    @patch("bam_core.utils.geo.GoogleMaps.get_normalized_address")
    @patch("bam_core.utils.geo.GoogleMaps.get_lat_lng")
    @patch("bam_core.utils.geo.GoogleMaps.get_plus_code")
    @patch("bam_core.utils.geo.NycPlanningLabs.search")
    def test_format_address_success(
        self,
        mock_nycpl_search,
        mock_get_plus_code,
        mock_get_lat_lng,
        mock_get_normalized_address,
        mock_get_place,
    ):
        # Mock responses
        mock_get_place.return_value = [
            {
                "description": "123 Main St APT # 1, Brooklyn, NY 11201",
                "types": ["subpremise"],
            }
        ]
        mock_get_normalized_address.return_value = {
            "result": {
                "verdict": {
                    "validationGranularity": "SUB_PREMISE",
                    "inputGranularity": "SUB_PREMISE",
                },
                "uspsData": {
                    "standardizedAddress": {
                        "firstAddressLine": "123 MAIN ST # 1",
                        "cityStateZipAddressLine": "BROOKLYN, NY 11201",
                    }
                },
                "address": {
                    "formattedAddress": "123 Main # 1 St Brooklyn, NY 11201"
                },
            }
        }
        mock_get_lat_lng.return_value = (40.6782, -73.9442)
        mock_get_plus_code.return_value = "87G8P27V+GQ"
        mock_nycpl_search.return_value = {
            "features": [
                {"properties": {"addendum": {"pad": {"bin": "3000001"}}}}
            ]
        }

        expected_result = {
            "cleaned_address": "123 MAIN ST APT 1 BROOKLYN, NY 11201",
            "bin": "3000001",
            "cleaned_address_accuracy": "Apartment",
            "plus_code": "87G8P27V+GQ",
            "lat": 40.6782,
            "lng": -73.9442,
        }

        result = format_address("123 Main St", "Brooklyn, NY", "11201")
        self.assertEqual(result, expected_result)

    @patch("bam_core.utils.geo.GoogleMaps.get_place")
    @patch("bam_core.utils.geo.GoogleMaps.get_normalized_address")
    @patch("bam_core.utils.geo.GoogleMaps.get_lat_lng")
    @patch("bam_core.utils.geo.GoogleMaps.get_plus_code")
    @patch("bam_core.utils.geo.NycPlanningLabs.search")
    def test_format_address_no_place_response(
        self,
        mock_nycpl_search,
        mock_get_plus_code,
        mock_get_lat_lng,
        mock_get_normalized_address,
        mock_get_place,
    ):
        # Mock responses
        mock_get_place.return_value = []
        mock_get_normalized_address.return_value = {
            "result": {
                "verdict": {
                    "validationGranularity": "PREMISE",
                    "inputGranularity": "PREMISE",
                },
                "uspsData": {
                    "standardizedAddress": {
                        "firstAddressLine": "123 MAIN ST",
                        "cityStateZipAddressLine": "BROOKLYN, NY 11201",
                    }
                },
                "address": {
                    "formattedAddress": "123 Main St Brooklyn, NY 11201"
                },
            }
        }
        mock_get_lat_lng.return_value = (40.6782, -73.9442)
        mock_get_plus_code.return_value = "87G8P27V+GQ"
        mock_nycpl_search.return_value = {"features": []}

        expected_result = {
            "cleaned_address": "123 MAIN ST BROOKLYN, NY 11201",
            "bin": "",
            "cleaned_address_accuracy": "Building",
            "plus_code": "87G8P27V+GQ",
            "lat": 40.6782,
            "lng": -73.9442,
        }

        result = format_address("123 Main St", "Brooklyn, NY", "11201")
        self.assertEqual(result, expected_result)

    @patch("bam_core.utils.geo.GoogleMaps.get_place")
    @patch("bam_core.utils.geo.GoogleMaps.get_normalized_address")
    @patch("bam_core.utils.geo.GoogleMaps.get_lat_lng")
    @patch("bam_core.utils.geo.GoogleMaps.get_plus_code")
    @patch("bam_core.utils.geo.NycPlanningLabs.search")
    def test_format_address_no_usps_data(
        self,
        mock_nycpl_search,
        mock_get_plus_code,
        mock_get_lat_lng,
        mock_get_normalized_address,
        mock_get_place,
    ):
        # Mock responses
        mock_get_place.return_value = [
            {
                "description": "123 Main St, Brooklyn, NY 11201",
                "types": ["premise"],
            }
        ]
        mock_get_normalized_address.return_value = {
            "result": {
                "verdict": {
                    "validationGranularity": "PREMISE",
                    "inputGranularity": "PREMISE",
                },
                "address": {
                    "formattedAddress": "123 Main St Brooklyn, NY 11201"
                },
            }
        }
        mock_get_lat_lng.return_value = (40.6782, -73.9442)
        mock_get_plus_code.return_value = "87G8P27V+GQ"
        mock_nycpl_search.return_value = {
            "features": [
                {"properties": {"addendum": {"pad": {"bin": "3000001"}}}}
            ]
        }

        expected_result = {
            "cleaned_address": "123 MAIN ST BROOKLYN, NY 11201",
            "bin": "3000001",
            "cleaned_address_accuracy": "Building",
            "plus_code": "87G8P27V+GQ",
            "lat": 40.6782,
            "lng": -73.9442,
        }

        result = format_address("123 Main St", "Brooklyn, NY", "11201")
        self.assertEqual(result, expected_result)

    @patch("bam_core.utils.geo.GoogleMaps.get_place")
    @patch("bam_core.utils.geo.GoogleMaps.get_normalized_address")
    @patch("bam_core.utils.geo.GoogleMaps.get_lat_lng")
    @patch("bam_core.utils.geo.GoogleMaps.get_plus_code")
    @patch("bam_core.utils.geo.NycPlanningLabs.search")
    def test_format_address_no_address(
        self,
        mock_nycpl_search,
        mock_get_plus_code,
        mock_get_lat_lng,
        mock_get_normalized_address,
        mock_get_place,
    ):
        expected_result = {
            "cleaned_address": "",
            "bin": "",
            "cleaned_address_accuracy": "No result",
            "plus_code": "",
            "lat": None,
            "lng": None,
        }

        result = format_address("", "Brooklyn, NY", "11201")
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
