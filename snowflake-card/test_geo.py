import pytest
from hamcrest import assert_that, close_to

from geo import calculate_angle

@pytest.mark.parametrize(
    "p1, p2, p3, expected",
    [
        ((1,0), (0,0), (1,1), 45.0),
        ((1,0), (0,0), (0,1), 90.0),    # 90° angle
        ((1,0), (0,0), (-1,1), 135.0),   # 135° angle
        ((1,0), (0,0), (-1,0), 180.0),   # 180° angle
        ((1,0), (0,0), (-1,-1), 225.0),  # 225° angle
        ((1,0), (0,0), (0,-1), 270.0),   # 270° angle
        ((1,0), (0,0), (1,-1), 315.0),   # 315° angle
        ((0,1), (0,0), (-1, 1), 45.0),
        ((11.981495457622364, 5.5358983848622465), (11.0, 5.5358983848622465), (10.50925227118882, 6.385898384862244), 120.0),

]
)
def test_calculate_angle(p1, p2, p3, expected):
    angle = calculate_angle(p1, p2, p3, use_360=True)
    assert_that(angle, close_to(expected, delta=0.001))