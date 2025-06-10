"""
Modern HTTP Client Utility

Enhanced HTTP client using httpx for superior performance, HTTP/2 support,
and modern async capabilities. Provides both sync and async interfaces
with connection pooling, retry logic, and comprehensive error handling.

This module serves as a strategic upgrade from traditional requests library,
offering better performance and modern features for API interactions.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import urljoin
import httpx
from httpx import RequestError, HTTPStatusError, TimeoutException
import structlog

from utils.retry_decorators import retry_google_sheets
from core.exceptions import BotError


logger = structlog.get_logger(__name__)


class HTTPClientError(BotError):
    """HTTP client related errors"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ModernHTTPClient:
    """
    Modern HTTP client with httpx backend

    Features:
    - HTTP/1.1 and HTTP/2 support
    - Connection pooling and keep-alive
    - Async and sync interfaces
    - Built-in retry logic
    - Request/response middleware
    - Performance metrics
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        enable_http2: bool = False,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize HTTP client

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            pool_connections: Number of connection pools
            pool_maxsize: Maximum connections per pool
            enable_http2: Enable HTTP/2 support
            default_headers: Default headers for all requests
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = default_headers or {}

        # Performance metrics
        self._request_count = 0
        self._total_time = 0.0
        self._error_count = 0

        # Create httpx clients using explicit keyword arguments to satisfy mypy
        timeout_conf = httpx.Timeout(timeout)
        limits_conf = httpx.Limits(
            max_connections=pool_connections,
            max_keepalive_connections=pool_maxsize,
        )

        self._sync_client = httpx.Client(
            timeout=timeout_conf,
            limits=limits_conf,
            http2=enable_http2,
            headers=self.default_headers,
            base_url=base_url or None,
        )

        self._async_client = httpx.AsyncClient(
            timeout=timeout_conf,
            limits=limits_conf,
            http2=enable_http2,
            headers=self.default_headers,
            base_url=base_url or None,
        )

    def __enter__(self):
        """Context manager support for sync client"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup for sync client"""
        self.close()

    async def __aenter__(self):
        """Async context manager support"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager cleanup"""
        await self.aclose()

    @retry_google_sheets
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Perform GET request

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional httpx arguments

        Returns:
            httpx.Response: Response object

        Raises:
            HTTPClientError: On request failure
        """
        return self._request("GET", url, params=params, headers=headers, **kwargs)

    @retry_google_sheets
    def post(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Perform POST request

        Args:
            url: Request URL
            data: Form data or raw data
            json: JSON data
            headers: Additional headers
            **kwargs: Additional httpx arguments

        Returns:
            httpx.Response: Response object

        Raises:
            HTTPClientError: On request failure
        """
        return self._request(
            "POST", url, data=data, json=json, headers=headers, **kwargs
        )

    @retry_google_sheets
    def put(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Perform PUT request"""
        return self._request(
            "PUT", url, data=data, json=json, headers=headers, **kwargs
        )

    @retry_google_sheets
    def delete(
        self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs
    ) -> httpx.Response:
        """Perform DELETE request"""
        return self._request("DELETE", url, headers=headers, **kwargs)

    async def aget(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Async GET request"""
        return await self._arequest(
            "GET", url, params=params, headers=headers, **kwargs
        )

    async def apost(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Async POST request"""
        return await self._arequest(
            "POST", url, data=data, json=json, headers=headers, **kwargs
        )

    async def aput(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Async PUT request"""
        return await self._arequest(
            "PUT", url, data=data, json=json, headers=headers, **kwargs
        )

    async def adelete(
        self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs
    ) -> httpx.Response:
        """Async DELETE request"""
        return await self._arequest("DELETE", url, headers=headers, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Internal sync request with metrics and error handling"""
        start_time = time.perf_counter()

        try:
            self._request_count += 1

            # Merge headers
            headers = kwargs.get("headers") or {}
            merged_headers = {**self.default_headers, **headers}
            kwargs["headers"] = merged_headers

            # Make request
            response = self._sync_client.request(method, url, **kwargs)

            # Check for HTTP errors
            response.raise_for_status()

            duration = time.perf_counter() - start_time
            self._total_time += duration

            logger.debug(
                "HTTP request completed",
                method=method,
                url=str(response.url),
                status=response.status_code,
                duration=duration,
                http_version=response.http_version,
            )

            return response

        except HTTPStatusError as e:
            self._error_count += 1
            duration = time.perf_counter() - start_time
            self._total_time += duration

            logger.error(
                "HTTP status error",
                method=method,
                url=str(e.response.url),
                status=e.response.status_code,
                duration=duration,
            )

            raise HTTPClientError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            )

        except (RequestError, TimeoutException) as e:
            self._error_count += 1
            duration = time.perf_counter() - start_time
            self._total_time += duration

            logger.error(
                "HTTP request error",
                method=method,
                url=url,
                error=str(e),
                duration=duration,
            )

            raise HTTPClientError(f"Request failed: {str(e)}")

    async def _arequest(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Internal async request with metrics and error handling"""
        start_time = time.perf_counter()

        try:
            self._request_count += 1

            # Merge headers
            headers = kwargs.get("headers") or {}
            merged_headers = {**self.default_headers, **headers}
            kwargs["headers"] = merged_headers

            # Make request
            response = await self._async_client.request(method, url, **kwargs)

            # Check for HTTP errors
            response.raise_for_status()

            duration = time.perf_counter() - start_time
            self._total_time += duration

            logger.debug(
                "Async HTTP request completed",
                method=method,
                url=str(response.url),
                status=response.status_code,
                duration=duration,
                http_version=response.http_version,
            )

            return response

        except HTTPStatusError as e:
            self._error_count += 1
            duration = time.perf_counter() - start_time
            self._total_time += duration

            logger.error(
                "Async HTTP status error",
                method=method,
                url=str(e.response.url),
                status=e.response.status_code,
                duration=duration,
            )

            raise HTTPClientError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            )

        except (RequestError, TimeoutException) as e:
            self._error_count += 1
            duration = time.perf_counter() - start_time
            self._total_time += duration

            logger.error(
                "Async HTTP request error",
                method=method,
                url=url,
                error=str(e),
                duration=duration,
            )

            raise HTTPClientError(f"Async request failed: {str(e)}")

    def batch_get(self, urls: List[str], **kwargs) -> List[httpx.Response]:
        """
        Perform multiple GET requests in batch

        Args:
            urls: List of URLs to request
            **kwargs: Common request arguments

        Returns:
            List[httpx.Response]: List of responses
        """
        responses: List[httpx.Response] = []
        for url in urls:
            try:
                response = self.get(url, **kwargs)
                responses.append(response)
            except HTTPClientError as e:
                logger.warning(f"Batch request failed for {url}: {e}")
                # Continue with other URLs

        return responses

    async def abatch_get(self, urls: List[str], **kwargs) -> List[httpx.Response]:
        """
        Perform multiple async GET requests concurrently

        Args:
            urls: List of URLs to request
            **kwargs: Common request arguments

        Returns:
            List[httpx.Response]: List of responses
        """
        tasks = [self.aget(url, **kwargs) for url in urls]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Async batch request failed for {urls[i]}: {result}")
            else:
                responses.append(result)

        return responses

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get client performance metrics

        Returns:
            Dict[str, Any]: Performance metrics
        """
        avg_time = (
            self._total_time / self._request_count if self._request_count > 0 else 0.0
        )
        success_rate = (
            (self._request_count - self._error_count) / self._request_count
            if self._request_count > 0
            else 0.0
        )

        return {
            "request_count": self._request_count,
            "total_time": self._total_time,
            "average_time": avg_time,
            "error_count": self._error_count,
            "success_rate": success_rate,
            "http2_enabled": getattr(self._sync_client, "http2", False),
        }

    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self._request_count = 0
        self._total_time = 0.0
        self._error_count = 0

    def close(self) -> None:
        """Close sync client"""
        self._sync_client.close()

    async def aclose(self) -> None:
        """Close async client"""
        await self._async_client.aclose()


# Convenience functions for simple usage
def get(url: str, **kwargs) -> httpx.Response:
    """Simple GET request using default client"""
    with ModernHTTPClient() as client:
        return client.get(url, **kwargs)


def post(url: str, **kwargs) -> httpx.Response:
    """Simple POST request using default client"""
    with ModernHTTPClient() as client:
        return client.post(url, **kwargs)


async def aget(url: str, **kwargs) -> httpx.Response:
    """Simple async GET request using default client"""
    async with ModernHTTPClient() as client:
        return await client.aget(url, **kwargs)


async def apost(url: str, **kwargs) -> httpx.Response:
    """Simple async POST request using default client"""
    async with ModernHTTPClient() as client:
        return await client.apost(url, **kwargs)


# Migration utilities from requests
class RequestsCompatibility:
    """
    Compatibility layer for migrating from requests to httpx

    Provides requests-like interface using httpx backend
    """

    @staticmethod
    def get(url: str, **kwargs) -> httpx.Response:
        """requests.get compatible method"""
        return get(url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs) -> httpx.Response:
        """requests.post compatible method"""
        return post(url, **kwargs)

    @staticmethod
    def put(url: str, **kwargs) -> httpx.Response:
        """requests.put compatible method"""
        with ModernHTTPClient() as client:
            return client.put(url, **kwargs)

    @staticmethod
    def delete(url: str, **kwargs) -> httpx.Response:
        """requests.delete compatible method"""
        with ModernHTTPClient() as client:
            return client.delete(url, **kwargs)


# Export compatibility interface
requests_compat = RequestsCompatibility()
