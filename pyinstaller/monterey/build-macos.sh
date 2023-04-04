
# 20210526, build SanPy.app for macOS Catalina 10.15.7
#  Be sure to
#    source sanp_env/bin/activate
#  Requires
#    PyQt 5.15.2

# see here for code to dynamically load plugins
# https://stackoverflow.com/questions/56495814/how-to-load-plugins-in-an-app-build-with-pyinstaller

# 	--onedir \

#pyinstaller \
#	--clean \
#	--onedir \
#	--windowed \
#	--icon ../sanpy/interface/icons/sanpy_transparent.icns \
#	--noconfirm \
#	--path ../sanpy_env/lib/python3.7/site-packages \
#	--name SanPy \
#	../sanpy/interface/sanpy_app.py

# 	--add-binary "/opt/miniconda3/envs/sanpy-env/bin/ptrepack:." \

# 	--hidden-import tables.scripts \
#	--hidden-import tables.scripts.ptrepack \
#	--add-data "../sanpy/_ptrepack.py:." \

# on macos laptop, use
#   --path /Users/cudmore/Sites/SanPy/sanpy_env/lib/python3.9/site-packages/pyqtgraph/colors:pyqtgraph/colors" \

# on macos studio, use
#	--path /opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages \
#	--add-data "/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors:pyqtgraph/colors" \

pyinstaller \
	--noconfirm \
	--clean \
	--onedir \
	--windowed \
	--icon ../sanpy/interface/icons/sanpy_transparent.icns \
	--path /opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages \
	--name SanPy \
	--hidden-import pkg_resources.py2_warn \
	--hidden-import pkg_resources.markers \
	--hidden-import tables \
	--add-data "/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors:pyqtgraph/colors" \
	../sanpy/interface/sanpy_app.py
