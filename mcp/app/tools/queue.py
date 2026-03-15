"""MCP tools for managing the training queue."""

import logging
import uuid

from fastmcp import FastMCP

from app.services.api_client import client

logger = logging.getLogger(__name__)

queue_router = FastMCP(name="Queue Tools")


@queue_router.tool
async def get_pending_workouts() -> dict | list:
    """
    Get all pending workout queue items waiting to be processed.

    Returns:
        List of pending queue items, each with: id, activity_type, title,
        description, workout_data, status, created_at, fetched_at, completed_at.
    """
    try:
        return await client.get_pending_queue()
    except Exception as e:
        logger.exception(f"Error in get_pending_workouts: {e}")
        return {"error": str(e)}


@queue_router.tool
async def create_workout(
    activity_type: str,
    display_name: str,
    location: str,
    scheduled_date: str,
    blocks: list[dict],
    warmup: dict | None = None,
    cooldown: dict | None = None,
    description: str | None = None,
) -> dict | list:
    """
    Create a structured workout composition and queue it for the Apple Watch.

    The workout will appear on the user's Apple Watch via WorkoutKit after
    the iPhone app syncs with the queue.

    Args:
        activity_type: One of "running", "cycling", "walking", "hiking", "swimming".
        display_name: Name shown on Apple Watch (e.g. "6x400m Intervals", "Tempo Run").
        location: Either "outdoor" or "indoor".
        scheduled_date: When the workout should appear, ISO 8601 (e.g. "2026-03-18T07:00:00Z").
        blocks: List of interval blocks. Each block has:
            - iterations (int): Number of times to repeat this block.
            - steps (list): List of interval steps, each with:
                - purpose (str): "work" or "recovery"
                - goal (dict): What defines completion of this step.
                    - type: "distance", "time", "energy", or "open"
                    - value (number): Required for distance/time/energy, omit for open.
                    - unit (str): Required for distance/time.
                      Distance units: "meters", "kilometers", "miles"
                      Time units: "seconds", "minutes"
                      Energy: "kilocalories"
                - alert (dict|null): Optional pacing/effort alert.
                    - type: "speed", "heartRate", "heartRateZone", "cadence", "power", "powerZone"
                    - For speed: min, max, unit ("metersPerSecond" or "kilometersPerHour")
                    - For heartRate: min, max (BPM)
                    - For heartRateZone: zone (1-5)
                    - For cadence: min, max (steps/min)
                    - For power: min, max (watts)
                    - For powerZone: zone (integer)
        warmup: Optional warmup step with same goal/alert structure as an interval step.
        cooldown: Optional cooldown step with same goal/alert structure as an interval step.
        description: Optional text description of the workout.

    Returns:
        The created queue item object.

    Example — 6x400m intervals with 800m warmup and cooldown:
        activity_type: "running"
        display_name: "6x400m Intervals"
        location: "outdoor"
        scheduled_date: "2026-03-18T07:00:00Z"
        warmup: {"goal": {"type": "distance", "value": 800, "unit": "meters"}}
        blocks: [
            {
                "iterations": 6,
                "steps": [
                    {
                        "purpose": "work",
                        "goal": {"type": "distance", "value": 400, "unit": "meters"},
                        "alert": {"type": "speed", "min": 4.5, "max": 5.0, "unit": "metersPerSecond"}
                    },
                    {
                        "purpose": "recovery",
                        "goal": {"type": "distance", "value": 400, "unit": "meters"}
                    }
                ]
            }
        ]
        cooldown: {"goal": {"type": "distance", "value": 800, "unit": "meters"}}

    Example — 20-minute tempo run:
        activity_type: "running"
        display_name: "20min Tempo"
        location: "outdoor"
        scheduled_date: "2026-03-19T07:00:00Z"
        warmup: {"goal": {"type": "distance", "value": 1600, "unit": "meters"}}
        blocks: [
            {
                "iterations": 1,
                "steps": [
                    {
                        "purpose": "work",
                        "goal": {"type": "time", "value": 20, "unit": "minutes"},
                        "alert": {"type": "heartRateZone", "zone": 4}
                    }
                ]
            }
        ]
        cooldown: {"goal": {"type": "distance", "value": 1600, "unit": "meters"}}
    """
    try:
        workout_data = {
            "id": str(uuid.uuid4()),
            "displayName": display_name,
            "activityType": activity_type,
            "location": location,
            "scheduledDate": scheduled_date,
            "blocks": blocks,
            "warmup": warmup,
            "cooldown": cooldown,
        }
        return await client.create_queue_item(
            activity_type=activity_type,
            title=display_name,
            description=description,
            workout_data=workout_data,
        )
    except Exception as e:
        logger.exception(f"Error in create_workout: {e}")
        return {"error": str(e)}


@queue_router.tool
async def update_workout_status(item_id: str, status: str) -> dict | list:
    """
    Update the status of a queue item.

    Args:
        item_id: UUID of the queue item.
        status: New status value (e.g. "pending", "fetched", "completed").
                Setting to "fetched" records the fetch timestamp.
                Setting to "completed" records the completion timestamp.

    Returns:
        The updated queue item object.
    """
    try:
        return await client.update_queue_status(item_id=item_id, status=status)
    except Exception as e:
        logger.exception(f"Error in update_workout_status: {e}")
        return {"error": str(e)}
