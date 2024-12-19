# Christmas card 2024

This is the code for our generative Christmas card 2024. It uses vsketch for coding up the snowflakes and vpype 
for generating output suitable gcode for my iDraw 2.0 plotter.

## Running

The main sketch is snowflake-card. If you're on a mac then you can probably install pyenv and pyenv-virtualenv and then
run `./setup.sh` to get the dependencies installed.

Once installed you can run `vsk run snowflake-card` from the root of the project.

I normally select and output a number I like and then join them together into a set of A3 gcode files using 
multicard.py with something like `python ./multicards.py --input-size a5 snowflake-card/output/snowflake_card_liked_*`
(where there are four files matching that pattern).
