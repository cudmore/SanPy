#--hidden-import pkg_resources.py2_warn \
#--hidden-import pkg_resources.markers \

pyinstaller \
	--noconfirm \
	--clean \
	--onedir \
	--console \
 	--windowed \
    --icon ../sanpy/interface/icons/sanpy_transparent.icns \
	--path /Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/ \
	--name SanPy-Monterey \
    --hidden-import pkg_resources \
  	--hidden-import tables \
    --add-data "/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors:pyqtgraph/colors" \
	../sanpy/interface/sanpy_app.py
