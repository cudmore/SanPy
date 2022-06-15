#--hidden-import pkg_resources.py2_warn \
#--hidden-import pkg_resources.markers \

pyinstaller \
	--noconfirm \
	--clean \
	--onedir \
	--windowed \
	--icon ../sanpy/interface/icons/sanpy_transparent.icns \
	--path /Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/ \
	--name SanPy \
	--hidden-import tables \
    --hidden-import pkg_resources \
    --add-data "/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors:pyqtgraph/colors" \
	../sanpy/interface/sanpy_app.py
