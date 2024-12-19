from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Iterable

import vsketch
from shapely import affinity
from shapely.geometry.base import BaseGeometry
from shapely.geometry.linestring import LineString
from shapely.geometry.multilinestring import MultiLineString
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.point import Point
from shapely.geometry.polygon import Polygon, LinearRing
from shapely.linear import shortest_line
from shapely.ops import unary_union, polygonize
from shapely.set_operations import difference
from vpype import FONT_NAMES
from vsketch import Vsketch

from geo import create_offset_polygon, perspective_by_angle

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class PolygonStoreEntry:
    layer: int
    geometry: BaseGeometry
    name: str

class PolygonGroup:
    def __init__(self, name: str):
        self.polygons = []
        self.groups = {}
        self.name = name

    def add_polygon(self, polygon: Polygon | MultiPolygon, layer: int, name: str):
        self.polygons.append(PolygonStoreEntry(layer, polygon, name))

    def add_geom(self, geometry: BaseGeometry, layer: int, name: str):
        self.polygons.append(PolygonStoreEntry(layer, geometry, name))

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
                # if entry.layer == 2:
                vsk.stroke(entry.layer)
                vsk.geometry(entry.geometry)
            except ValueError as e:
                raise ValueError(f"Error drawing {entry.name}") from e

@dataclass
class BranchConfig:
    offset: float
    length: float
    thickness: float


class SnowflakeCardSketch(vsketch.SketchClass):
    # Sketch parameters
    angle = vsketch.Param(0, min_value=0, max_value=45)
    paper_size = vsketch.Param("a5", choices=["a5", "a4"])


    centre_x_prop = vsketch.Param(3/4, min_value=0, max_value=1, decimals=2)
    centre_y_prop = vsketch.Param(1/2, min_value=0, max_value=1, decimals=2)
    snowflake_size = vsketch.Param(2.8, min_value=2.0, max_value=20.0)
    grid_spacing = vsketch.Param(5.6, min_value=5.0, max_value=20.0)
    outer_size_prop = vsketch.Param(1/4, min_value=0.0, max_value=1.0, decimals=2)
    sector_offset = vsketch.Param(20, min_value=0, max_value=50)
    sector_width = vsketch.Param(10, min_value=0, max_value=50)
    dendrite_proportion = vsketch.Param(0.35, min_value=0.0, max_value=1.0, decimals=2)
    non_star_percentage = vsketch.Param(90, min_value=0, max_value=100)
    page_divider = vsketch.Param(False)
    debug = vsketch.Param(False)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size(self.paper_size, landscape=True, center=False)
        vsk.scale("mm")

        psx, psy = (210, 148) if self.paper_size == "a5" else (297, 210)

        # create the snowflake
        vsk.penWidth("0.4mm")

        sketch_group = PolygonGroup("snowflake card")


        mid_line = LineString([(psx/2, 0), (psx/2, psy)])

        # draw a line down the middle of the card where it will be folded
        if self.page_divider:
            vsk.stroke(10)
            vsk.geometry(mid_line)

        # add some credits text to the back of the card
        vsk.stroke(1)
        text_centre_x, text_centre_y = (psx/4, psy*0.96)
        text_size = 2.5 * psx/210
        for i in range(2):
            vsk.text("Card designed and plotted by Simon Hildrew", text_centre_x, text_centre_y, align="center", size=text_size)
        credits_box = Polygon([
            (text_centre_x - psx/7, text_centre_y - text_size/2),
            (text_centre_x + psx/7, text_centre_y - text_size/2),
            (text_centre_x + psx/7, text_centre_y + text_size/2),
            (text_centre_x - psx/7, text_centre_y + text_size/2)
        ])
        if self.debug:
            sketch_group.add_geom(credits_box, 1, "credits_box")

        # make a rectangle with the margin of the size of a snowflake in from the edge
        margin = self.snowflake_size * 1.5
        snowflake_field = Polygon([
            (margin, margin),
            (psx-margin, margin),
            (psx-margin, psy-margin),
            (margin, psy-margin)]
        )

        # coords of front of card
        front_centre_x = self.centre_x_prop * psx
        front_centre_y = self.centre_y_prop * psy

        # draw a snowflake with sector ends
        sector_star_outer = self.hexagon_star_with_sector_ends(front_centre_x, front_centre_y, self.outer_size_prop * psx, 15, sector_offset=self.sector_offset, sector_width=self.sector_width)
        rotated_star_outer = affinity.rotate(sector_star_outer, origin=(front_centre_x, front_centre_y), angle=30+self.angle)

        if self.debug:
            sketch_group.add_polygon(rotated_star_outer, 10, "star1")

        # draw a triangular grid from the centre of the front of the card
        grid_points = self.triangular_grid(front_centre_x, front_centre_y, self.grid_spacing, psx, angle_degrees=30+self.angle)
        used_points = []

        # first, fill in the star outline
        for x, y in grid_points:
            in_star_outline = rotated_star_outer.contains(Point(x, y))
            if in_star_outline:
                sketch_group.add_geom(self.draw_a_star(x, y, self.snowflake_size, vsk.random), 2, f"star_{x}_{y}")
                used_points.append((x, y))

        selector = int(vsk.random(0, 4))

        glitter_flakes_size = self.snowflake_size * 1.5

        for i, (grid_x, grid_y) in enumerate(grid_points):
            x = vsk.random(grid_x - glitter_flakes_size, grid_x + glitter_flakes_size)
            y = vsk.random(grid_y - glitter_flakes_size, grid_y + glitter_flakes_size)
            if not snowflake_field.contains(Point(x, y)):
                continue

            line = shortest_line(mid_line, Point(x, y))
            if line.length < glitter_flakes_size * 2.0:
                continue

            if i%5 != selector:
                continue

            if vsk.random(0, 1) > self.non_star_percentage / 100:
                continue

            # check we are not too close to a point we have already used
            too_close = any(math.hypot(used_x - x, used_y - y) < glitter_flakes_size * 3
                        for used_x, used_y in used_points)
            if not too_close:
                star = self.draw_a_star(x, y, glitter_flakes_size, vsk.random)
                perspective_star = perspective_by_angle(star, vsk.random(-45, 45), distance=20)
                rotated_star = affinity.rotate(perspective_star, origin=(x, y), angle=vsk.random(0, 359))
                if snowflake_field.contains(rotated_star) and not credits_box.intersects(rotated_star):
                    sketch_group.add_geom(rotated_star, 3, f"star_{x}_{y}")
                    used_points.append((x, y))

        sketch_group.draw(vsk)

    def draw_a_star(self, x, y, radius, random):
        # draw a star
        if random(0, 1) > self.dendrite_proportion:
            sector_star = self.hexagon_star_with_sector_ends(
                x=x,
                y=y,
                radius=radius,
                thickness=self.snowflake_size * random(0.1,0.3),
                sector_offset=random(self.snowflake_size/3, (self.snowflake_size/3)*2),
                sector_width=random(0, self.snowflake_size/3)
            )
            return affinity.rotate(sector_star, origin=(x, y), angle=self.angle)
        else:
            # draw a dendrite
            branch_configs = list(self.random_branch_config(radius, 0.1, random))
            dendrite = self.stellar_dendrite(x, y, radius, branch_configs)
            return affinity.rotate(dendrite, origin=(x, y), angle=self.angle)

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

    def offset_my_way(self, polygon: Polygon, distance: float) -> Polygon:
        simplified_polygon = polygon.simplify(0.01)
        return create_offset_polygon(simplified_polygon, distance)

    def filled_polygon_my_way(self, polygon: Polygon, pen_width: float) -> PolygonGroup:
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

    def elongated_hexagon(self, x: float, y: float, length: float, thickness: float, fix: bool = False) -> Polygon:
        # calculate the distance from the left to the start of the line (essentially a line from the mid-point of the
        # left side at an angle of 30 degrees
        inset_distance = math.tan(math.radians(30)) * thickness * 0.5
        if length <= inset_distance * 2:
            assert fix, f"Length ({length}) must be greater than inset distance ({inset_distance}) * 2"
            length = inset_distance * 2 + 0.1

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

    # output a series of coordinates of grid points for a grid that forms equilateral triangles, with the points
    # spaced by the given spacing and repeating the given number of times. The first point is at x, y and
    # subsequent points go outwards from there in all directions.
    def triangular_grid(self, x: float, y: float, spacing: float, distance: float, angle_degrees: int) -> list[tuple[float, float]]:
        def in_accumulator(x: float, y: float, accumulator: list[tuple[float, float]]) -> bool:
            for point in accumulator:
                if math.isclose(point[0], x, abs_tol=0.00001) and math.isclose(point[1], y, abs_tol=0.00001):
                    return True
            return False

        # Initialize with starting point
        accumulator = [(x, y)]
        # Queue of points to process
        queue = [(x, y)]

        while queue:
            current_x, current_y = queue.pop(0)

            # Generate points in all six directions
            for i in range(6):
                angle = math.radians(i * 60 + angle_degrees)
                new_x = current_x + math.cos(angle) * spacing
                new_y = current_y + math.sin(angle) * spacing

                # Calculate distance from origin to new point
                line_length = math.sqrt((new_x - x) ** 2 + (new_y - y) ** 2)

                # If point is within distance and not already processed
                if line_length <= distance and not in_accumulator(new_x, new_y, accumulator):
                    accumulator.append((new_x, new_y))
                    queue.append((new_x, new_y))

        return accumulator


    def random_branch_config(self, radius: float, thickness: float, random) -> Iterable[BranchConfig]:
        fern_like = random(0, 1) < 0.2
        number_of_branches = math.ceil(random(2, 4))
        offset_start = random(radius/9, radius/5)
        offset_end = random(radius*0.9, radius)
        first_length = None
        for branch in range(1, number_of_branches+1):
            offset = ((offset_end - offset_start) / number_of_branches) * branch + offset_start
            if fern_like:
                # get shorter as we go out with a maximum of offset so they don't cross over
                if first_length is None:
                    first_length = offset
                this_branch_reduction = first_length * branch / number_of_branches
                length = first_length - random(this_branch_reduction*(5/6), this_branch_reduction)
            else:
                longest = min(offset, radius - offset)
                length = random(longest/2, longest)
            thickness = random(thickness*0.5, thickness)
            yield BranchConfig(offset, length, thickness)

    def stellar_dendrite(self, x: float, y: float, radius: float, branch_configs: list[BranchConfig]) -> BaseGeometry:
        # Start with a hexagon star
        lines = []
        for i in range(6):
            angle_degrees = i * 60
            branch = LineString([(x, y), (x + radius * math.cos(math.radians(angle_degrees)),
                                        y + radius * math.sin(math.radians(angle_degrees)))])
            lines.append(branch)
            for branch_config in branch_configs:
                branch_start_x = x + branch_config.offset * math.cos(math.radians(angle_degrees))
                branch_start_y = y + branch_config.offset * math.sin(math.radians(angle_degrees))
                branch_end_left_x = branch_start_x + branch_config.length * math.cos(math.radians(angle_degrees-60))
                branch_end_left_y = branch_start_y + branch_config.length * math.sin(math.radians(angle_degrees-60))
                lines.append(LineString([(branch_start_x, branch_start_y), (branch_end_left_x, branch_end_left_y)]))
                branch_end_right_x = branch_start_x + branch_config.length * math.cos(math.radians(angle_degrees+60))
                branch_end_right_y = branch_start_y + branch_config.length * math.sin(math.radians(angle_degrees+60))
                lines.append(LineString([(branch_start_x, branch_start_y), (branch_end_right_x, branch_end_right_y)]))

        return MultiLineString(lines)


    # layers are:
    # 1: credit text
    # 2: snowflake
    # 3: sparkles
    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge --layer 2,3 linesimplify reloop linesort -t --layer 2,3 lmove 1,2 2 name --layer 2 white name --layer 3 sparkles")

if __name__ == "__main__":
    SnowflakeCardSketch.display()



