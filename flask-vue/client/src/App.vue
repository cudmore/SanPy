<template>
  <div id="app">
    <div id="nav">
      <!-- <router-link to="/">Home</router-link> | -->
      |
      <router-link to="/analysis">Analysis</router-link> |
      <!-- <router-link to="/ping">Ping</router-link> | -->
      <!-- <router-link to="/filelist">filelist</router-link> | -->
      <!-- <router-link to="/myplotly">myplotly</router-link> | -->
      <router-link to="/about">About</router-link> |
    </div>
    <router-view/>
  </div>
</template>

<style>
#app {
  margin-top: 10px;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}

#nav {
  padding: 20px;
}

#nav a {
  font-weight: bold;
  color: #2c3e50;
}

#nav a.router-link-exact-active {
  color: #42b983;
}
</style>
