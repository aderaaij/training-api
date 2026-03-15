"""HTTP client for Training API."""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TrainingClient:
    """Client for interacting with Training REST API."""

    def __init__(self) -> None:
        self.base_url = settings.training_api_url.rstrip("/")
        self.timeout = settings.request_timeout
        self._api_key = settings.training_api_key.get_secret_value()

    def _ensure_configured(self) -> None:
        """Raise an error if the API key is not configured."""
        if not self._api_key:
            from app.config import Settings

            env_file = Settings.model_config.get("env_file")
            raise ValueError(f"TRAINING_API_KEY is not configured. Please set it in: {env_file}")

    @property
    def headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> list | dict:
        """Make an HTTP request to the Training API."""
        self._ensure_configured()
        url = f"{self.base_url}{path}"
        logger.debug(f"Making {method} request to {url}")

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            response = await http_client.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs,
            )

            if response.status_code == 401:
                raise ValueError("Invalid API key. Check your TRAINING_API_KEY configuration.")
            if response.status_code == 404:
                raise ValueError(f"Resource not found: {path}")

            response.raise_for_status()
            return response.json()

    async def list_workouts(
        self,
        activity_type: str | None = None,
        start_after: str | None = None,
        start_before: str | None = None,
        limit: int = 50,
    ) -> list | dict:
        """List workouts with optional filters."""
        params: dict[str, Any] = {"limit": limit}
        if activity_type:
            params["activity_type"] = activity_type
        if start_after:
            params["start_after"] = start_after
        if start_before:
            params["start_before"] = start_before
        return await self._request("GET", "/api/workouts", params=params)

    async def get_workout(self, workout_id: str) -> list | dict:
        """Get a single workout by ID."""
        return await self._request("GET", f"/api/workouts/{workout_id}")

    async def get_workout_splits(self, workout_id: str) -> list | dict:
        """Get splits for a workout."""
        return await self._request("GET", f"/api/workouts/{workout_id}/splits")

    async def get_workout_heartrate(self, workout_id: str) -> list | dict:
        """Get heart rate samples for a workout."""
        return await self._request("GET", f"/api/workouts/{workout_id}/heartrate")

    async def get_workout_summary(
        self,
        activity_type: str | None = None,
        period: str = "month",
    ) -> list | dict:
        """Get workout summary grouped by period."""
        params: dict[str, Any] = {"period": period}
        if activity_type:
            params["activity_type"] = activity_type
        return await self._request("GET", "/api/workouts/summary", params=params)

    async def get_pending_queue(self) -> list | dict:
        """Get pending queue items."""
        return await self._request("GET", "/api/queue/pending")

    async def create_queue_item(
        self,
        activity_type: str,
        title: str,
        description: str | None = None,
        workout_data: dict | None = None,
    ) -> list | dict:
        """Create a new queue item. Sends camelCase keys as required by the API."""
        body: dict[str, Any] = {
            "activityType": activity_type,
            "title": title,
        }
        if description is not None:
            body["description"] = description
        if workout_data is not None:
            body["workoutData"] = workout_data
        return await self._request("POST", "/api/queue", json=body)

    async def update_queue_status(self, item_id: str, status: str) -> list | dict:
        """Update the status of a queue item."""
        return await self._request("PATCH", f"/api/queue/{item_id}/status", json={"status": status})


# Singleton instance
client = TrainingClient()
