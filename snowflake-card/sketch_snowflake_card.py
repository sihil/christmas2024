import vsketch


class SnowflakeCardSketch(vsketch.SketchClass):
    # Sketch parameters:
    # radius = vsketch.Param(2.0)
    # Sketch parameters
    segments = vsketch.Param(6, min_value=3, max_value=12)
    iterations = vsketch.Param(4, min_value=1, max_value=6)
    size = vsketch.Param(100, min_value=1, max_value=200)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a5", landscape=True)
        vsk.scale("cm")

        # Draw the main snowflake structure
        for i in range(self.segments):
            angle = i * (360 / self.segments)
            vsk.pushMatrix()
            vsk.rotate(angle, degrees=True)
            self.draw_branch(vsk, self.size, self.iterations)
            vsk.popMatrix()

    def draw_branch(self, vsk: vsketch.Vsketch, length: float, depth: int) -> None:
        if depth == 0:
            return

        # Draw main branch
        vsk.line(0, 0, length, 0)

        # Draw sub-branches
        new_length = length * 0.4

        vsk.pushMatrix()
        vsk.translate(length * 0.3, 0)
        vsk.rotate(45, degrees=True)
        self.draw_branch(vsk, new_length, depth - 1)
        vsk.rotate(-90, degrees=True)
        self.draw_branch(vsk, new_length, depth - 1)
        vsk.popMatrix()

        # Draw branch tip
        vsk.pushMatrix()
        vsk.translate(length, 0)
        vsk.rotate(45, degrees=True)
        self.draw_branch(vsk, new_length, depth - 1)
        vsk.rotate(-90, degrees=True)
        self.draw_branch(vsk, new_length, depth - 1)
        vsk.popMatrix()

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    SnowflakeCardSketch.display()



