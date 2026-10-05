import time
import logging
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("api_client")
T = TypeVar("T", bound=BaseModel)

class APIClientError(Exception):
    pass

class SchemaValidationError(APIClientError):
    pass

class ApiClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout)
        )

    def close(self) -> None:
        self._client.close()

    def _execute(
        self,
        method: str,
        endpoint: str,
        response_model: Optional[Type[T]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> tuple[httpx.Response, Optional[T]]:
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        start_time = time.perf_counter()

        try:
            response = self._client.request(
                method=method,
                url=url,
                json=json_data,
                params=params
            )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.error(f"HTTP {method} {url} connection dropped: {str(exc)}")
            raise APIClientError(f"Connection failed for {method} {url}: {exc}") from exc

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(f"[{method}] {response.status_code} {url} | Latency: {elapsed_ms:.2f}ms")

        parsed_data = None
        if response_model and response.is_success:
            try:
                parsed_data = response_model.model_validate(response.json())
            except ValidationError as err:
                logger.error(f"Schema violation on {method} {url}: {err.errors()}")
                raise SchemaValidationError(f"Payload validation failed: {err}") from err

        return response, parsed_data

    def post(
        self,
        endpoint: str,
        payload: BaseModel,
        response_model: Optional[Type[T]] = None
    ) -> tuple[httpx.Response, Optional[T]]:
        return self._execute(
            method="POST",
            endpoint=endpoint,
            response_model=response_model,
            json_data=payload.model_dump(mode="json")
        )

    def get(
        self,
        endpoint: str,
        response_model: Optional[Type[T]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> tuple[httpx.Response, Optional[T]]:
        return self._execute(
            method="GET",
            endpoint=endpoint,
            response_model=response_model,
            params=params
        )
