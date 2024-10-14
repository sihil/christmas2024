#!/usr/bin/env zsh

set -euo pipefail

pyenv rehash

python_version=$(cat .python-version-number)

pyenv install -s "${python_version}"

# check if a pyenv venv christmas2024 exists and if not create it
if ! pyenv versions | grep "christmas2024"; then
    pyenv virtualenv "${python_version}" christmas2024
fi

pip install -r requirements.txt