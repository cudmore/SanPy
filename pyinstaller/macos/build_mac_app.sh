#!/bin/zsh

# Usage: ./build_mac_app.sh <arch>
# arch must be 'osx-64' or 'osx-arm64'

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <arch>"
    echo "  <arch> must be 'osx-64' or 'osx-arm64'"
    exit 1
fi

arch="$1"

if [[ "$arch" != "osx-64" && "$arch" != "osx-arm64" ]]; then
    echo "Error: arch must be 'osx-64' or 'osx-arm64'"
    exit 1
fi

if [[ "$arch" == "osx-64" ]]; then
    CONDA_ENV_NAME="sanpy-pyinstaller-osx-64"
    CONDA_SUBDIR_VALUE="osx-64"
elif [[ "$arch" == "osx-arm64" ]]; then
    CONDA_ENV_NAME="sanpy-pyinstaller-osx-arm64"
    CONDA_SUBDIR_VALUE="osx-arm64"
fi

# Create the conda environment for the specified architecture
export CONDA_SUBDIR="$CONDA_SUBDIR_VALUE"
conda create -y -n "$CONDA_ENV_NAME" python=3.12

# Source conda
source /Users/cudmore/opt/miniconda3/etc/profile.d/conda.sh

# Activate the environment and set CONDA_SUBDIR as a persistent env var
conda activate "$CONDA_ENV_NAME"
conda env config vars set CONDA_SUBDIR="$CONDA_SUBDIR_VALUE"
conda deactivate
conda activate "$CONDA_ENV_NAME"

# Install dependencies
pip install --upgrade pip
pip install pyinstaller
pip install '../../.[gui]'


echo "Created conda environment: $CONDA_ENV_NAME"

# Call the Python build script with the arch argument
python macos_build.py

python notarizeSanpy.py
