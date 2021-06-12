
# 20210526, build SanPy.app for macOS Catalina 10.15.7
#  Be sure to
#    source sanp_env/bin/activate
#  Requires
#    PyQt 5.15.2

# see here for code to dynamically load plugins
# https://stackoverflow.com/questions/56495814/how-to-load-plugins-in-an-app-build-with-pyinstaller

# 	--onedir \

pyinstaller \
	--clean \
	--onedir \
	--windowed \
	--icon ../sanpy/interface/icons/sanpy_transparent.icns \
	--noconfirm \
	--path ../sanpy_env/lib/python3.7/site-packages \
	--name SanPy \
	../sanpy/interface/sanpy_app.py
