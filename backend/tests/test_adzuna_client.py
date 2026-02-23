"""Tests for Adzuna API client."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.providers.adzuna_client import AdzunaClient, AdzunaAPIError


def test_adzuna_client_builds_url():
    """Client builds the correct request URL and params."""
    client = AdzunaClient(app_id="test_id", app_key="test_key", base_url="https://api.adzuna.com/v1/api")
    expected_base = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.text = "{}"
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        result = client.search_jobs(country="gb", page=1, what="python", where="london", results_per_page=20)
        call_args = mock_client_cls.return_value.__enter__.return_value.get.call_args
        assert call_args[0][0] == expected_base
        params = call_args[1]["params"]
        assert params["app_id"] == "test_id"
        assert params["app_key"] == "test_key"
        assert params["what"] == "python"
        assert params["where"] == "london"
        assert params["results_per_page"] == 20
        assert result == {"results": []}


def test_adzuna_client_raises_on_non_200():
    """Client raises AdzunaAPIError on non-200 response."""
    client = AdzunaClient(app_id="id", app_key="key")
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        with pytest.raises(AdzunaAPIError) as exc_info:
            client.search_jobs(country="gb", page=1)
        assert exc_info.value.status_code == 401
