"""Geospatial utilities used for distance calculations."""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6_371_000


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two lat/lng points in meters.

    Args:
        lat1: Latitude of the first point.
        lng1: Longitude of the first point.
        lat2: Latitude of the second point.
        lng2: Longitude of the second point.

    Returns:
        Distance in meters.

    Notes:
        The Haversine formula accounts for spherical distance and is accurate
        enough for campus-level matching (approx. +/- 0.5%).
    """

    lat1_rad = radians(lat1)
    lng1_rad = radians(lng1)
    lat2_rad = radians(lat2)
    lng2_rad = radians(lng2)

    delta_lat = lat2_rad - lat1_rad
    delta_lng = lng2_rad - lng1_rad

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(
        delta_lng / 2
    ) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_METERS * c


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two lat/lng points in kilometers."""

    return haversine_meters(lat1, lng1, lat2, lng2) / 1000.0
