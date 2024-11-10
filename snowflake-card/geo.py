import math


import math
from typing import Tuple

import numpy as np
from shapely.geometry.polygon import Polygon


def calculate_angle(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], use_360: bool = False) -> float:
    """
    Calculate the angle between lines p1->p2 and p2->p3 in degrees.
    Points should be provided as tuples of (x, y) coordinates.

    Args:
        p1, p2, p3: Points as (x,y) tuples
        use_360: If True, returns angle in [0, 360] range.
                If False, returns angle in [-180, 180] range.

    Returns:
        Angle in degrees. Positive angles indicate counterclockwise rotation
        from vector1 to vector2.
    """
    # Calculate vectors
    vector1 = (p1[0] - p2[0], p1[1] - p2[1])
    vector2 = (p3[0] - p2[0], p3[1] - p2[1])

    # Calculate dot product
    dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]

    # Calculate cross product (z component only since we're in 2D)
    cross_product = vector1[0] * vector2[1] - vector1[1] * vector2[0]

    # Calculate angle using atan2
    angle_radians = math.atan2(cross_product, dot_product)

    # Convert to degrees
    angle_degrees = math.degrees(angle_radians)

    # Convert to [0, 360] range if requested
    if use_360 and angle_degrees < 0:
        angle_degrees += 360

    return angle_degrees


def polygon_coord_windows(polygon):
    coords = list(polygon.exterior.coords)
    if coords[0] == coords[-1]:
        # Remove the last point if it's the same as the first
        coords = coords[:-1]
    yield coords[-1], coords[0], coords[1]
    for i in range(len(coords)-2):
        yield coords[i], coords[i+1], coords[i+2]
    yield coords[-2], coords[-1], coords[0]


def offset_point(p1, p2, p3, distance):
    angle = calculate_angle(p1, p2, p3, use_360=True)

    bisect_angle = math.radians(angle/2)

    # Calculate the offset distance
    offset_distance = distance / math.sin(bisect_angle)

    direction_angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + bisect_angle

    # Calculate the new point
    new_x = p2[0] + offset_distance * math.cos(direction_angle)
    new_y = p2[1] + offset_distance * math.sin(direction_angle)
    return (new_x, new_y)


def create_offset_polygon(polygon, distance):
    new_coords = []
    for p1, p2, p3 in polygon_coord_windows(polygon):
        try:
            new_coord = offset_point(p1, p2, p3, distance)
            new_coords.append(new_coord)
        except ZeroDivisionError:
            print(f"Zero division error at {p1}, {p2}, {p3}")
            new_coords.append(p2)
            pass
    return Polygon(new_coords)


def perspective_by_angle(polygon, angle_degrees, distance=10):
    """
    Apply 3D perspective transformation to a polygon based on a viewing angle.

    Parameters:
    polygon: shapely.geometry.Polygon - The polygon to transform
    angle_degrees: float - Angle in degrees (0° = front view, 90° = edge view)
    distance: float - Virtual camera distance (affects perspective strength)

    Returns:
    shapely.geometry.Polygon - The transformed polygon
    """
    # Convert angle to radians
    angle = math.radians(angle_degrees)
    print(f"angle: {angle_degrees} degrees = {angle} radians")

    # Get the bounds and center of the polygon
    minx, miny, maxx, maxy = polygon.bounds
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2

    def transform_point(x, y):
        # Translate point relative to center
        rel_x = x - center_x
        rel_y = y - center_y

        # Calculate z-coordinate based on angle
        z = rel_x * math.sin(angle)

        # Calculate new x based on angle
        x_rotated = rel_x * math.cos(angle)

        # Apply perspective projection
        scale = distance / (distance + z)

        # Transform the point
        new_x = center_x + x_rotated * scale
        new_y = center_y + rel_y * scale

        print(f"({x}, {y}) -> ({new_x}, {new_y}) [z={z}, rel_x={rel_x} scale={scale}, x_rotated={x_rotated}]")

        return new_x, new_y

    # Apply transformation to all coordinates
    coords = list(polygon.exterior.coords)
    new_coords = [transform_point(x, y) for x, y in coords]

    return Polygon(new_coords)