import os
import subprocess
import sys

import vpype_cli

script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# read in filenames from arguments
files = sys.argv[1:]

number = len(files)

if number not in [2,4]:
    raise ValueError("number of files must be 2 or 4")

# make directory if it doesn't exist
subprocess.Popen(
    ["mkdir", "-p", "output/grid"],
    stdout=subprocess.PIPE
)

cols = number // 2

vpype_cli.execute(f"""
    eval "files={repr(files)}"
    eval "cols={cols}; rows=2"
    grid -o 210mm 148mm "%cols%" "%rows%"
        read --no-fail "%files[_i] if _i < len(files) else ''%"
    end
    write output/grid/combined-grid.svg
""")

# convert the multilayer SVG to per-layer GCODE files
vpype_cli.execute(f"""
    read output/grid/combined-grid.svg
    pagerotate
    forlayer gwrite --profile idraw_v2 "output/grid/combined-grid-%_name%.gcode" end
""", global_opt="--config vpype.toml")  # note that we use a config file here to define the idraw_v2 profile