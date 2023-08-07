#
# Build an arm64 environment

# create and activate a conda environment
CONDA_SUBDIR=osx-arm64 conda create -y -n sanpy-pyinstaller-arm python=3.9

# (re)activate environment to get rid of
# "To make your changes take effect please reactivate your environment"
source /Users/cudmore/opt/miniconda3/etc/profile.d/conda.sh
conda activate sanpy-pyinstaller-arm

conda env config vars set CONDA_SUBDIR=osx-arm64

# NEED TO REACTIVATE ENV !!!
conda deactivate
conda activate sanpy-pyinstaller-arm

pip install --upgrade pip

# install required packages
# numpy 1.24 breaks PYQtGraph with numpy.float error

# pytable==5.11.0 is not available on conda
# 20230805, failures in build, was workin in May 2023
# rolled back pytables from 3.8.0 to 3.7.0 and now builds!

conda install -y numpy==1.23.4 \
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
                  pytables==3.7.0

pip install pyabf
pip install pyqtdarktheme

# install sanpy with no packages
pip install -e '../../.'

# install modified version of pyinstaller (removes .DS_Store)
pip install -e ~/Sites/pyinstaller/.

# build the app with pyinstaller
python macos_build.py

python notarizeSanpy.py dist_arm