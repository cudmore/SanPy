#
# build an x86 app

CONDA_SUBDIR=osx-64 conda create -y -n sanpy-pyinstaller-i386 python=3.11
#conda create -y -n sanpy-pyinstaller-i386 python=3.9

# to get rid of
# "To make your changes take effect please reactivate your environment"
source /Users/cudmore/opt/miniconda3/etc/profile.d/conda.sh
conda activate sanpy-pyinstaller-i386

conda env config vars set CONDA_SUBDIR=osx-64

conda deactivate
conda activate sanpy-pyinstaller-i386

pip install --upgrade pip

# pip install  '../../.[gui]'
pip install -e '../../.[gui]'

# 20231122, switched back to most recent pyinstaller
# this is my modified version to not copy .DS_Store files
#pip install -e ~/Sites/pyinstaller/.

# pip install --upgrade pyinstaller
#pip install ../../pyinstaller_20231122/pyinstaller/.

pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip

python macos_build.py

python notarizeSanpy.py dist_x86
