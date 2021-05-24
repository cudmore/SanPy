The browser based web application provides the same interface for analysis as the desktop application.

<IMG SRC="../img/app2-interface.png" width=700 border=1>


Once data is analyzed, Pooling allows browsing detection parameters across any number of files.


<IMG SRC="../img/pymy-pooling.png" width=700 border=1>

### Install the web application

Please note, this is experimental and does not have all functions implemented. Please use the desktop version instead.

```
cd SanPy/dash
pip install -r requirements.txt
```

### Running the web applications

Run the web application to analyze raw data

```
cd SanPy/dash
python app2.py
```

The web application for analysis is available at

```
http://localhost:8000
```

Run the web application to browse and pool saved analysis

```
cd SanPy/dash
python bBrowser_app.py
```

The web application for browsing and pooling saved analysis is available at

```
http://localhost:8050
```
