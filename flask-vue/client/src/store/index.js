// store/index.js

import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    user: {
      username: 'matt',
      fullName: 'Matt Maribojoc',
    },
  },
  getters: {},
  mutations: {},
  actions: {},
});
