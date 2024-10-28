import math


import math
from typing import Tuple

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