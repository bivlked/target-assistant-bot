"""
Tests for Modern HTTP Client utility

Tests both sync and async functionality, performance metrics,
error handling, and compatibility layer.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import httpx
from httpx import HTTPStatusError, RequestError, TimeoutException

from utils.http_client import (
    ModernHTTPClient,
    HTTPClientError,
    get,
    post,
    aget,
    apost,
    requests_compat,
)


class TestModernHTTPClient:
    """Tests for ModernHTTPClient class"""

    def test_init_default_params(self):
        """Test client initialization with default parameters"""
        client = ModernHTTPClient()

        assert client.base_url is None
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.default_headers == {}
        assert client._request_count == 0
        assert client._total_time == 0.0
        assert client._error_count == 0

    def test_init_custom_params(self):
        """Test client initialization with custom parameters"""
        headers = {"Authorization": "Bearer token"}
        client = ModernHTTPClient(
            base_url="https://api.example.com",
            timeout=60.0,
            max_retries=5,
            enable_http2=False,
            default_headers=headers,
        )

        assert client.base_url == "https://api.example.com"
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.default_headers == headers

    def test_context_manager_sync(self):
        """Test sync context manager"""
        with ModernHTTPClient() as client:
            assert isinstance(client, ModernHTTPClient)
            assert client._sync_client is not None

    @pytest.mark.asyncio
    async def test_context_manager_async(self):
        """Test async context manager"""
        async with ModernHTTPClient() as client:
            assert isinstance(client, ModernHTTPClient)
            assert client._async_client is not None

    @patch("httpx.Client.request")
    def test_get_request_success(self, mock_request):
        """Test successful GET request"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.text = "Success"
        mock_response.http_version = "HTTP/1.1"
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        client = ModernHTTPClient()
        response = client.get("https://example.com")

        assert response == mock_response
        mock_request.assert_called_once()

        # Check metrics
        metrics = client.get_performance_metrics()
        assert metrics["request_count"] == 1
        assert metrics["error_count"] == 0

    @patch("httpx.Client.request")
    def test_post_request_with_json(self, mock_request):
        """Test POST request with JSON data"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.url = "https://example.com/api"
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        client = ModernHTTPClient()
        data = {"key": "value"}
        response = client.post("https://example.com/api", json=data)

        assert response == mock_response
        mock_request.assert_called_once_with(
            "POST", "https://example.com/api", data=None, json=data, headers={}
        )

    @patch("httpx.Client.request")
    def test_request_with_custom_headers(self, mock_request):
        """Test request with custom headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        default_headers = {"User-Agent": "TestBot/1.0"}
        client = ModernHTTPClient(default_headers=default_headers)

        custom_headers = {"Authorization": "Bearer token"}
        client.get("https://example.com", headers=custom_headers)

        # Should merge default and custom headers
        expected_headers = {**default_headers, **custom_headers}
        args, kwargs = mock_request.call_args
        assert kwargs["headers"] == expected_headers

    @patch("httpx.Client.request")
    def test_request_http_error(self, mock_request):
        """Test request with HTTP error"""
        # Mock HTTPStatusError
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.url = "https://example.com/notfound"
        mock_response.text = "Not Found"

        error = HTTPStatusError("404", request=Mock(), response=mock_response)
        mock_request.return_value = mock_response
        mock_response.raise_for_status.side_effect = error

        client = ModernHTTPClient()

        with pytest.raises(HTTPClientError) as exc_info:
            client.get("https://example.com/notfound")

        assert exc_info.value.status_code == 404
        assert "404" in str(exc_info.value)

        # Check error metrics
        metrics = client.get_performance_metrics()
        assert metrics["error_count"] == 1

    @patch("httpx.Client.request")
    def test_request_network_error(self, mock_request):
        """Test request with network error"""
        mock_request.side_effect = RequestError("Connection failed")

        client = ModernHTTPClient()

        with pytest.raises(HTTPClientError) as exc_info:
            client.get("https://example.com")

        assert "Request failed" in str(exc_info.value)
        assert exc_info.value.status_code is None

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.request")
    async def test_async_get_request(self, mock_request):
        """Test async GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.http_version = "HTTP/2"
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        client = ModernHTTPClient()
        response = await client.aget("https://example.com")

        assert response == mock_response
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.request")
    async def test_async_batch_requests(self, mock_request):
        """Test async batch requests"""
        # Mock multiple responses
        responses = []
        for i in range(3):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = f"https://example.com/{i}"
            mock_response.raise_for_status.return_value = None
            responses.append(mock_response)

        mock_request.side_effect = responses

        client = ModernHTTPClient()
        urls = [f"https://example.com/{i}" for i in range(3)]
        results = await client.abatch_get(urls)

        assert len(results) == 3
        assert mock_request.call_count == 3

    def test_batch_sync_requests(self):
        """Test sync batch requests"""
        with patch("httpx.Client.request") as mock_request:
            # Mock responses
            responses = []
            for i in range(2):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.url = f"https://example.com/{i}"
                mock_response.raise_for_status.return_value = None
                responses.append(mock_response)

            mock_request.side_effect = responses

            client = ModernHTTPClient()
            urls = [f"https://example.com/{i}" for i in range(2)]
            results = client.batch_get(urls)

            assert len(results) == 2

    def test_performance_metrics(self):
        """Test performance metrics calculation"""
        client = ModernHTTPClient()

        # Initial state
        metrics = client.get_performance_metrics()
        assert metrics["request_count"] == 0
        assert metrics["average_time"] == 0.0
        assert metrics["success_rate"] == 0.0

        # Simulate requests
        client._request_count = 10
        client._total_time = 2.5
        client._error_count = 2

        metrics = client.get_performance_metrics()
        assert metrics["request_count"] == 10
        assert metrics["average_time"] == 0.25  # 2.5 / 10
        assert metrics["success_rate"] == 0.8  # (10 - 2) / 10

    def test_reset_metrics(self):
        """Test metrics reset"""
        client = ModernHTTPClient()

        # Set some metrics
        client._request_count = 5
        client._total_time = 1.0
        client._error_count = 1

        # Reset
        client.reset_metrics()

        assert client._request_count == 0
        assert client._total_time == 0.0
        assert client._error_count == 0

    def test_close_clients(self):
        """Test client cleanup"""
        with patch("httpx.Client.close") as mock_sync_close:
            client = ModernHTTPClient()
            client.close()
            mock_sync_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_clients(self):
        """Test async client cleanup"""
        with patch("httpx.AsyncClient.aclose") as mock_async_close:
            client = ModernHTTPClient()
            await client.aclose()
            mock_async_close.assert_called_once()


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    @patch("utils.http_client.ModernHTTPClient")
    def test_get_function(self, mock_client_class):
        """Test convenience get function"""
        mock_client = Mock()
        mock_response = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        response = get("https://example.com")

        assert response == mock_response
        mock_client.get.assert_called_once_with("https://example.com")

    @patch("utils.http_client.ModernHTTPClient")
    def test_post_function(self, mock_client_class):
        """Test convenience post function"""
        mock_client = Mock()
        mock_response = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        data = {"key": "value"}
        response = post("https://example.com", json=data)

        assert response == mock_response
        mock_client.post.assert_called_once_with("https://example.com", json=data)

    @pytest.mark.asyncio
    @patch("utils.http_client.ModernHTTPClient")
    async def test_aget_function(self, mock_client_class):
        """Test async convenience get function"""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_client.aget.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        response = await aget("https://example.com")

        assert response == mock_response
        mock_client.aget.assert_called_once_with("https://example.com")


class TestRequestsCompatibility:
    """Tests for requests compatibility layer"""

    @patch("utils.http_client.get")
    def test_requests_compat_get(self, mock_get):
        """Test requests compatibility get"""
        mock_response = Mock()
        mock_get.return_value = mock_response

        response = requests_compat.get("https://example.com")

        assert response == mock_response
        mock_get.assert_called_once_with("https://example.com")

    @patch("utils.http_client.post")
    def test_requests_compat_post(self, mock_post):
        """Test requests compatibility post"""
        mock_response = Mock()
        mock_post.return_value = mock_response

        response = requests_compat.post("https://example.com", json={"key": "value"})

        assert response == mock_response
        mock_post.assert_called_once_with("https://example.com", json={"key": "value"})

    @patch("utils.http_client.ModernHTTPClient")
    def test_requests_compat_put(self, mock_client_class):
        """Test requests compatibility put"""
        mock_client = Mock()
        mock_response = Mock()
        mock_client.put.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        response = requests_compat.put("https://example.com", json={"key": "value"})

        assert response == mock_response
        mock_client.put.assert_called_once_with(
            "https://example.com", json={"key": "value"}
        )

    @patch("utils.http_client.ModernHTTPClient")
    def test_requests_compat_delete(self, mock_client_class):
        """Test requests compatibility delete"""
        mock_client = Mock()
        mock_response = Mock()
        mock_client.delete.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        response = requests_compat.delete("https://example.com")

        assert response == mock_response
        mock_client.delete.assert_called_once_with("https://example.com")


class TestHTTPClientError:
    """Tests for HTTPClientError exception"""

    def test_http_client_error_basic(self):
        """Test basic HTTPClientError"""
        error = HTTPClientError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.status_code is None

    def test_http_client_error_with_status(self):
        """Test HTTPClientError with status code"""
        error = HTTPClientError("Not found", status_code=404)

        assert str(error) == "Not found"
        assert error.status_code == 404
