<template>
  <div class='container'>
    <!-- <Plotly :data='data' :layout='layout' :display-mode-bar='true'></Plotly> -->
    <div id='myplot' :key="componentKey"></div>
    MyPlotly.vue username: {{username}}
    <div v-if="loading">
        <!-- here put a spinner or whatever you want to indicate that a request is in progress -->
        <h3>Loading Trace ...</h3>
    </div>
    <div v-else>
        <!-- request finished -->
    </div>
    <!-- MyPlotly.vue data: {{data}} -->
  </div>
</template>

<script>
import axios from 'axios';
// import { Plotly } from 'vue-plotly';
import Plotly from 'plotly.js-dist/plotly';

export default {
  // props: {
  //  username: String, // trying to pass a parameter
  // },
  props: ['username'],
  // components: {
  //   Plotly,
  // },
  data() {
    return {
      loading: false,
      componentKey: 0,
      pdata: [{
        x: [], // [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        y: [], // [10, 15, 13, 17, 20, 2, 12.6, 13, 40, 30],
        // type: 'scatter',
        type: 'scattergl',
      }],
      layout: {
        title: '',
      },
    };
  },
  mounted() {
    // console.log(this.$store.state.user.username);
    console.log('mounted', this.$store.state.user.fullName);
  },
  methods: {
    forceRerender() {
      this.componentKey += 1;
    },
    getxy() {
      this.loading = true;
      const path = 'http://localhost:5000/getxy/2';
      console.log('getxy() is fetching');
      // const start = window.performance.now();
      axios.get(path)
        .then((res) => {
          console.log('  finished 0');
          this.pdata[0].x = res.data.sweepX;
          console.log('  finished 1');
          this.pdata[0].y = res.data.sweepY;
          console.log('  finished 2');
          this.plot_channel();
          // this.username = this.$store.state.user.username;
          // console.log('this.data.x:', this.data[0].x);
          // console.log('this.data.y:', this.data[0].y);
          console.log('  finished 3 this.username:', this.username);
        })
        .catch((error) => {
          // eslint-disable-next-line
          console.error(error);
        })
        .finally(() => {
          this.loading = false;
        });
      // this.forceRerender();
    },
    plot_channel() {
      console.log('plot_channel()');
      const channel = 'xyz';
      this.layout.title = channel;
      // window.pdata = this.pdata;
      // this.pdata[0].y = csv.getColoumnByName(channel);
      // window.ppplot = this.plot;
      // Plotly.plot('myplot', this.pdata);
      Plotly.react('myplot', this.pdata);
      // this.forceRerender();
    },
    react() {
      console.log('react()');
      return Plotly.react('myplot', this.pdata);
    },
  },
  created() {
    this.getxy();
  },
};
</script>
