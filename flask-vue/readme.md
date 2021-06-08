## Flask app to have proper client-server

For now using this to test Rest API of sanpy.bbAnalysis.

Remember, I can retrieve directly from the command-line with curl:

```
curl http://0.0.0.0:5000/
curl http://0.0.0.0:5000/filelist
curl http://0.0.0.0:5000/getxy/1
```

Following: https://testdriven.io/blog/developing-a-single-page-app-with-flask-and-vuejs/

Once this is all done, deploy on heroku or AWS with: https://testdriven.io/blog/deploying-flask-to-heroku-with-docker-and-gitlab/

Another deploy flask/vue to heroku: https://dev.to/ulrikson/deploying-a-flask-vue-app-to-heroku-3bf8

```
# make virtual env
cd server
python3 -m venv flask_env
source flask_env/bin/activate
# will install sanpy with '-e ../../.'
pip install -r requirements.txt
```

```
# install vue/cli
npm install -g @vue/cli
```

```
# initialize folder 'frontend'
vue create client
```

I chose these options

```
Vue CLI v3.7.0
? Please pick a preset: Manually select features
? Check the features needed for your project: Babel, Router, Linter
? Use history mode for router? Yes
? Pick a linter / formatter config: Airbnb
? Pick additional lint features: Lint on save
? Where do you prefer placing config for Babel, PostCSS, ESLint, etc.? In package.json
? Save this as a preset for future projects? (y/N) No
```

Run the server, this will be at: http://127.0.0.1:8080/

```
cd client
npm run serve
```

Install axios and bootstrap-vue (in frontend folder)

```
cd frontend
npm install axios --save

# i don't know which to use???
#npm install bootstrap --save
#npm install bootstrap-vue --save
npm install vuex --save
#npm install vue-plotly
plotly.js-dist
```

Modify frontend/src/main.js

```
```
