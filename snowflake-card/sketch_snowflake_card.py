from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import vsketch
from anyio.streams.stapled import MultiListener
from shapely import affinity
from shapely.geometry.base import BaseGeometry
from shapely.geometry.linestring import LineString
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon, LinearRing
from shapely.ops import unary_union, polygonize
from shapely.set_operations import difference
from vsketch import Vsketch

from geo import calculate_angle

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class PolygonStoreEntry:
    layer: int
    geometry: Polygon | MultiPolygon
    name: str

class PolygonGroup:
    def __init__(self, name: str):
        self.polygons = []
        self.groups = {}
        self.name = name

    def add_polygon(self, polygon: Polygon | MultiPolygon, layer: int, name: str):
        self.polygons.append(PolygonStoreEntry(layer, polygon, name))

    def add_group(self, group: PolygonGroup, name: str, change_layer: int | None = None):
        if name in self.groups:
            raise ValueError(f"Group {name} already exists")
        self.groups[name] = group

    def all_geometries(self):
        return self.polygons + [PolygonStoreEntry(entry.layer, entry.geometry, f"{self.name}/{entry.name}")
                                for group in self.groups.values()
                                for entry in group.all_geometries()]

    def draw(self, vsk: Vsketch):
        for entry in self.all_geometries():
            try:
                vsk.stroke(entry.layer)
                vsk.geometry(entry.geometry)
            except ValueError as e:
                raise ValueError(f"Error drawing {entry.name}") from e

class SnowflakeCardSketch(vsketch.SketchClass):
    # Sketch parameters
    size = vsketch.Param(60, min_value=1, max_value=200)
    complexity = vsketch.Param(5, min_value=3, max_value=8)
    randomness = vsketch.Param(0.3, min_value=0, max_value=1)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a5", landscape=True, center=False)
        vsk.scale("cm")

        # create the snowflake
        vsk.penWidth("0.7mm")

        sketch_group = PolygonGroup("snowflake card")

        # base_star = self.filled_hexagon_star2(13, 9, self.size / 10, 1, 0.07)
        # sketch_group.add_group(base_star, "star1")

        sector_star = self.filled_hexagon_star_with_sector_ends(7, 5, self.size / 15, 1, sector_offset=1.2, sector_width=0.7, pen_width=0.07)
        sketch_group.add_group(sector_star, "star2")

        sector_star_to_full = self.hexagon_star_with_sector_ends(13, 9, self.size / 15, 1, sector_offset=1.2, sector_width=0.7)
        sector_star_filled = self.filled_polygon_my_way(sector_star_to_full, 0.07)
        sketch_group.add_group(sector_star_filled, 4, "star3")

        sketch_group.draw(vsk)

    def hexagon(self, x: float, y: float, radius: float) -> BaseGeometry:
        points = []
        for i in range(6):
            angle = math.radians(i * 60)
            points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
        return Polygon(points)

    def filled_hexagon_star_with_sector_ends(self, x: float, y: float, radius: float, thickness: float, sector_offset: float, sector_width: float, pen_width: float) -> PolygonGroup:
        group = PolygonGroup("filled_hexagon_star_with_sector_ends")
        star = self.hexagon_star(x, y, radius, thickness)
        sector_ends = []
        for i in range(6):
            sector = self.elongated_hexagon(x + sector_offset, y, radius - sector_offset, thickness + sector_width)
#           filled_sector = self.filled_polygon(sector, -pen_width)
            rotated_sector = affinity.rotate(geom=sector, origin=(x, y), angle=i*60)
            sector_ends.append(rotated_sector)
            group.add_group(self.filled_polygon(rotated_sector, -pen_width), f"sector_{i}")

        star_centre = difference(star, unary_union(sector_ends))
        geoms = list(star_centre.geoms)
        group.add_group(self.filled_polygon(geoms[0], pen_width), "star_centre")

        return group

    def hexagon_star_with_sector_ends(self, x: float, y: float, radius: float, thickness: float, sector_offset: float, sector_width: float) -> BaseGeometry:
        star = self.hexagon_star(x, y, radius, thickness)
        sector_ends = []
        for i in range(6):
            sector = self.elongated_hexagon(x + sector_offset, y, radius - sector_offset, thickness + sector_width)
            sector_ends.append(affinity.rotate(geom=sector, origin=(x, y), angle=i*60))
        return unary_union([star, *sector_ends])

    def filled_hexagon_star(self, x: float, y: float, radius: float, thickness: float, pen_width: float) -> MultiPolygon:
        thickness_offset = 0
        polygons = [self.hexagon_star(x, y, radius, thickness)]
        print(f"Creating filled hexagon star at {x}, {y} with radius {radius}, thickness {thickness} and pen_width {pen_width}")
        while thickness+thickness_offset > 0:
            thickness_offset -= pen_width * 2
            print(f"Thickness offset: {thickness_offset}")
            polygons.append(self.hexagon_star(x, y, radius+thickness_offset*math.tan(math.radians(30)), thickness+thickness_offset))
        return MultiPolygon(polygons)

    def filled_polygon(self, polygon: Polygon, pen_width: float) -> PolygonGroup:
        group = PolygonGroup("filled_polygon")
        polygon_ring: LinearRing = polygon.exterior
        group.add_polygon(polygon, 1, "outer_polygon")
        thickness_offset = 0
        breakout = 50
        while True:
            thickness_offset -= pen_width
            print(f"Thickness offset: {thickness_offset}")
            offset = polygon_ring.offset_curve(thickness_offset)
            if offset.is_empty:
                break
            group.add_polygon(Polygon(offset), 1, f"fill_polygon_{thickness_offset}")
            breakout -= 1
            if breakout < 0:
                raise ValueError("Too many iterations")
        return group

    def filled_polygon_my_way(self, polygon: Polygon, pen_width: float) -> PolygonGroup:
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
                    logger.error(f"Zero division error at {p1}, {p2}, {p3}")
                    new_coords.append(p2)
                    pass
            return Polygon(new_coords)

        group = PolygonGroup("filled_polygon_my_way")
        simplified_polygon = polygon.simplify(0.01)

        for coord in simplified_polygon.exterior.coords:
            print(f"coord: {coord}")
        group.add_polygon(simplified_polygon, 1, "outer_polygon")
        offset_polygons = []
        for i in range(8):
            offset_polygon = create_offset_polygon(simplified_polygon, -pen_width * i)
            offset_polygons.append(offset_polygon)
            print(f"{list(offset_polygon.interiors)} offset_polygon.is_simple: {offset_polygon.is_simple} offset_polygon.is_valid: {offset_polygon.is_valid}")
            #group.add_polygon(offset_polygon, 1, f"fill_polygon_{pen_width}_{i}")

        offset_polygons.append(create_offset_polygon(simplified_polygon, -pen_width * 8))
        group.add_polygon(offset_polygons[8], 2, f"fill_polygon_{pen_width}_8")

        test = unary_union(offset_polygons[8].exterior)
        print(test)
        remaining = difference(simplified_polygon, test)
        holes = [Polygon(hole) for hole in remaining.interiors]
        print(len(holes))



        print(test.geom_type)
        for i, polygon in enumerate(polygonize(test)):
            print(f"Polygon {i}: {polygon}")
            union = unary_union([polygon, test])
            if union.area > offset_polygons[8].area:
                continue
            group.add_polygon(polygon, 3, f"test_poly_{i}")
            offset_polygon = create_offset_polygon(polygon, -pen_width)
            group.add_polygon(offset_polygon, 4, f"fill_polygon_{pen_width}_test_{i}")

        return group

    def filled_hexagon_star2(self, x: float, y: float, radius: float, thickness: float, pen_width: float) -> PolygonGroup:
        hexagon_star = PolygonGroup("filled_hexagon_star2")
        outer_hexagon_star = self.hexagon_star(x, y, radius, thickness)
        hexagon_star.add_polygon(outer_hexagon_star, 1, "outer_hexagon_star")
        ring: LinearRing = outer_hexagon_star.exterior
        print(f"Creating filled hexagon star at {x}, {y} with radius {radius}, thickness {thickness} and pen_width {pen_width}")

        thickness_offset = 0
        while thickness+thickness_offset > 0:
            thickness_offset -= pen_width
            print(f"Thickness offset: {thickness_offset}")
            offset = ring.offset_curve(thickness_offset)
            hexagon_star.add_polygon(offset, 1, f"outer_hexagon_star_{thickness_offset}")
        return hexagon_star

    def hexagon_star(self, x: float, y: float, radius: float, thickness: float) -> Polygon:
        print(f"Creating hexagon star at {x}, {y} with radius {radius} and thickness {thickness}")
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

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")

if __name__ == "__main__":
    SnowflakeCardSketch.display()



