import math

import vsketch
from shapely import affinity
from shapely.geometry.base import BaseGeometry
from shapely.geometry.linestring import LineString
from shapely.geometry.polygon import Polygon
from shapely.ops import unary_union


line_distances_mm = [0.5 + i * 0.1 for i in range(20)]


class SnowflakeTestSketch(vsketch.SketchClass):
    # Sketch parameters:
    # radius = vsketch.Param(2.0)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a3", landscape=False, center=False)
        vsk.scale("cm")

        vsk.penWidth("0.7mm")

        # implement your sketch here
        # vsk.circle(0, 0, self.radius, mode="radius")

        # let's draw a series of parallel lines that get increasingly further apart
        vsk.stroke(1)
        self.draw_lines(vsk, 2, 2, 5.0)
        vsk.stroke(2)
        self.draw_lines(vsk, 8, 2, 5.0)
        vsk.stroke(3)
        self.draw_lines(vsk, 14, 2, 5.0)

        vsk.geometry(self.elongated_hexagon(20, 3, 5, 2))

        distance_accumulator = 0
        for i, distance in enumerate(line_distances_mm):
            vsk.stroke(i % 3 + 1)
            vsk.geometry(self.hexagon_star(10, 13, 5+distance_accumulator, 1+distance_accumulator/math.tan(math.radians(30))))
            distance_accumulator += distance / 10

        # let's draw some hexagons
        distance_accumulator = 0
        for i, distance in enumerate(line_distances_mm):
            vsk.geometry(self.hexagon(10, 30, 4 + distance_accumulator))
            distance_accumulator += distance / 10

    def hexagon(self, x: float, y: float, radius: float) -> BaseGeometry:
        points = []
        for i in range(6):
            angle = math.radians(i * 60)
            points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
        return Polygon(points)

    def hexagon_star(self, x: float, y: float, radius: float, thickness: float) -> BaseGeometry:
        hexagons = []
        for i in range(6):
            elongated_hexagon = self.elongated_hexagon(x, y, radius, thickness)
            hexagons.append(affinity.rotate(geom=elongated_hexagon, origin=(x, y), angle=i*60))
        return unary_union(hexagons)

    def elongated_hexagon(self, x: float, y: float, length: float, thickness: float) -> Polygon:
        # calculate the distance from the left to the start of the line (essentially a line from the mid-point of the
        # left side at an angle of 30 degrees
        inset_distance = math.tan(math.radians(30)) * thickness * 0.5
        assert length > inset_distance * 2

        # draw a rectangle but with hexagonal ends at the left and right
        points = [
            # start at x, y
            (x, y),
            # top left
            (x + inset_distance, y - thickness / 2),
            # now the top right corner
            (x + length - inset_distance, y - thickness / 2),
            # now the right end
            (x + length, y),
            # now the bottom right corner
            (x + length - inset_distance, y + thickness / 2),
            # now the bottom left corner
            (x + inset_distance, y + thickness / 2)
        ]

        return Polygon(points)

    def draw_lines(self, vsk: vsketch.Vsketch, x: float, y: float, length: float) -> None:
        # let's draw a series of parallel lines that get increasingly further apart
        next_y = y
        for i in range(20):
            line = LineString([(x, next_y), (x+length, next_y)])
            vsk.geometry(line)
            next_y += line_distances_mm[i] / 10


    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    SnowflakeTestSketch.display()
