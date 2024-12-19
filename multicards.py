import argparse
import os
import subprocess
import sys

import vpype_cli

script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# read in input size from --input_size option using argparse
parser = argparse.ArgumentParser()
parser.add_argument("--input-size", choices=["a5", "a4"], required=True)
parser.add_argument("files", nargs="+")
args = parser.parse_args()

input_size = args.input_size

# read in filenames from arguments
files = args.files

number = len(files)

if input_size == "a5":
    assert number == 4, "4 files required for A5 input"
elif input_size == "a4":
    assert number == 2, "2 files required for A4 input"

# make directory if it doesn't exist
subprocess.Popen(
    ["mkdir", "-p", "output/grid"],
    stdout=subprocess.PIPE
)

if input_size == "a5":
    vpype_cli.execute(f"""
        eval "files={repr(files)}"
        eval "cols=2; rows=2"
        grid -o 210mm 148mm "%cols%" "%rows%"
            read --no-fail "%files[_i] if _i < len(files) else ''%"
        end
        write output/grid/combined-grid.svg
    """)
elif input_size == "a4":
    vpype_cli.execute(f"""
        eval "files={repr(files)}"
        eval "cols=1; rows=2"
        grid -o 297mm 210mm "%cols%" "%rows%"
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