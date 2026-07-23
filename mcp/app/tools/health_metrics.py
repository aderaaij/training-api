"""MCP tools for querying daily health metrics."""

import logging

from fastmcp import FastMCP

from app.services.api_client import client
from app.wire import text_result

logger = logging.getLogger(__name__)

health_metrics_router = FastMCP("health-metrics")


@health_metrics_router.tool()
@text_result
async def get_health_metrics(
    start_date: str,
    end_date: str | None = None,
) -> list | dict:
    """Get daily health metrics synced from HealthKit.

    Returns metrics like sleep, resting heart rate, HRV, weight, VO2Max,
    steps, active energy, body fat, respiratory rate, and SpO2.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to today
    """
    try:
        return await client.get_health_metrics(
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        return {"error": str(e)}
