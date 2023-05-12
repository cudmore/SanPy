#
# Build an arm64 environment

# create and activate a conda environment

CONDA_SUBDIR=osx-arm64 conda create -y -n sanpy-pyinstaller-arm python=3.9
#conda create -y -n sanpy-pyinstaller-arm python=3.9

# to get rid of
# "To make your changes take effect please reactivate your environment"
source /Users/cudmore/opt/miniconda3/etc/profile.d/conda.sh
conda activate sanpy-pyinstaller-arm

conda env config vars set CONDA_SUBDIR=osx-arm64

# NEED TO REACTIVATE ENV !!!
conda deactivate
conda activate sanpy-pyinstaller-arm

pip install --upgrade pip

# install required packages
conda install -y numpy \
                  pandas==1.5.3 \
                  scipy \
                  scikit-image==0.19.3 \
                  tifffile \
                  h5py \
                  requests \
                  matplotlib \
                  seaborn \
                  pyqt \
                  qtpy \
                  pyqtgraph \
                  pytables

pip install pyabf
pip install pyqtdarktheme

# install sanpy with no packages
pip install -e '../../.'

# install modified version of pyinstaller (removes .DS_Store)
pip install -e ~/Sites/pyinstaller/.

# build the app with pyinstaller
python macos_build.py

