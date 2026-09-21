from typing import Any

import requests


class NycPlanningLabs:
    base_url = "https://geosearch.planninglabs.nyc/v2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def search(self, text: str, size: int = 1) -> dict[str, Any]:
        """
        Search for a location in NYC using the geosearch API
        Args:
            text (str): The text to search for
            size (int): The number of results to return
        Returns:
            Dict[str, Any]: The response from the geosearch API
        """
        url = f"{self.base_url}/search"
        params = {"text": text, "size": size}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
        ) as e:
            return {"error": str(e)}
