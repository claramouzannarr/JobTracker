"""
Adzuna API client for job search.
See: https://developer.adzuna.com/docs/search
"""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class AdzunaAPIError(Exception):
    """Raised when Adzuna API returns an error or non-200 response."""

    def __init__(self, message: str, status_code: Optional[int] = None, body: Optional[str] = None):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class AdzunaClient:
    """Client for Adzuna Job Search API."""

    def __init__(self, app_id: str, app_key: str, base_url: str = "https://api.adzuna.com/v1/api"):
        self.app_id = app_id
        self.app_key = app_key
        self.base_url = base_url.rstrip("/")
        self._timeout = 30.0

    def search_jobs(
        self,
        country: str,
        page: int,
        what: Optional[str] = None,
        where: Optional[str] = None,
        results_per_page: int = 50,
        extra_params: Optional[dict] = None,
    ) -> dict:
        """
        Search jobs from Adzuna.

        GET {base_url}/jobs/{country}/search/{page}?app_id=...&app_key=...&what=...&where=...&results_per_page=...

        :param country: Country code (e.g. "gb", "us", "es").
        :param page: Page number (1-based).
        :param what: Job title/keyword search.
        :param where: Location filter.
        :param results_per_page: Number of results per page (default 50).
        :param extra_params: Optional extra query parameters.
        :return: API response dict with "results" list of job objects.
        :raises AdzunaAPIError: On non-200 response or request failure.
        """
        url = f"{self.base_url}/jobs/{country}/search/{page}"
        params: dict[str, Any] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": results_per_page,
        }
        if what:
            params["what"] = what
        if where:
            params["where"] = where
        if extra_params:
            params.update(extra_params)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=params)
        except httpx.RequestError as e:
            logger.warning("Adzuna request failed: %s", e)
            raise AdzunaAPIError(f"Adzuna request failed: {e}") from e

        if response.status_code != 200:
            raise AdzunaAPIError(
                f"Adzuna API returned {response.status_code}",
                status_code=response.status_code,
                body=response.text[:500] if response.text else None,
            )

        try:
            data = response.json()
        except Exception as e:
            raise AdzunaAPIError(f"Invalid JSON response: {e}", body=response.text[:500]) from e

        return data
