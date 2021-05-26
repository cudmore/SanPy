
# 20210526, build SanPy.app for macOS Catalina 10.15.7
#  Be sure to
#    source sanp_env/bin/activate
#  Requires
#    PyQt 5.15.2

pyinstaller \
	--clean \
	--onedir \
	--windowed \
	--icon ../sanpy/interface/icons/sanpy_transparent.icns \
	--noconfirm \
	--path ../sanpy_env/lib/python3.7/site-packages \
	--name SanPy \
	../sanpy/interface/app.py
