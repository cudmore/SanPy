import Vue from 'vue';
import VueRouter from 'vue-router';
import Home from '../views/Home.vue';
import Ping from '../components/Ping.vue';
import Analysis from '../components/Analysis.vue';
import About from '../components/About.vue';
import FileList from '../components/FileList.vue';
import MyPlotly from '../components/MyPlotly.vue';

Vue.use(VueRouter);

const routes = [
  {
    path: '/analysis',
    name: 'Analysis',
    component: Analysis,
    // component: () => import(/* webpackChunkName: "about" */ '../views/Analysis.vue'),
  },
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/about',
    name: 'About',
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    // component: () => import(/* webpackChunkName: "about" */ '../views/About.vue'),
    component: About,
  },
  {
    path: '/ping',
    name: 'Ping',
    component: Ping,
  },
  {
    path: '/filelist',
    name: 'FileList',
    component: FileList,
  },
  {
    path: '/myplotly',
    name: 'MyPlotly',
    component: MyPlotly,
  },
];

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes,
});

export default router;
