<template>
  <div class='container'>
    <!-- <Plotly :data='data' :layout='layout' :display-mode-bar='true'></Plotly> -->
    <!-- <div id='myplot' :key="componentKey"></div> -->
    <div id='myplot'></div>
    MyPlotly.vue username: {{username}}
    MyPlotly.vue filename: {{filename}}
    <div v-if="loading">
        <!-- here put a spinner or whatever you want to indicate that a request is in progress -->
        <h3>Loading Traces ...</h3>
    </div>
    <div v-else>
        <!-- request finished -->
    </div>
    <!-- MyPlotly.vue data: {{data}} -->
  </div>
</template>

<script>
import axios from 'axios';
// import AdmZip from 'adm-zip';
// import { Plotly } from 'vue-plotly';
import Plotly from 'plotly.js-dist/plotly';

// const AdmZip = require('adm-zip');

export default {
  // props: {
  //  username: String, // trying to pass a parameter
  // },
  props: ['username', 'filename'],
  // components: {
  //   Plotly,
  // },
  data() {
    return {
      loading: false,
      // componentKey: 0,
      pdata: [{
        x: [], // [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        y: [], // [10, 15, 13, 17, 20, 2, 12.6, 13, 40, 30],
        // type: 'scatter', (or 'scattergl', 'lines')
        type: 'scatter',
        mode: 'lines',
      }],
      layout: {
        title: '',
      },
    };
  },
  mounted() {
    // console.log(this.$store.state.user.username);
    console.log('myPlotlyView.mounted() mounted', this.$store.state.user.fullName);
    this.$root.$on('myPlotlyLoadFile', (rowIdx, item) => {
      // set global filename
      console.log('myPlotlyLoadFile() item:', item);
      // this.loading = true; // does not work
      this.getxy2(rowIdx);
      // this.loading = false; // does not work
      // const filename = item.file; // from FileList
      // this.$root.$emit('analysis_setFileName', filename);
    });
    // not sure why I need this, plotly is supposed to react on pdata change ???
    this.$watch('pdata', () => {
      this.react();
    }, { deep: !this.watchShallow });
  },
  /*
  watch: {
    // whenever pdata changes, this function will run
    pdata(newData, oldData) {
      console.log('newData:', newData);
      console.log('oldData:', oldData);
      this.react();
    },
  },
  */
  methods: {
    forceRerender() {
      console.log('forceRender');
      // this.componentKey += 1;
    },
    getxy2(rowIdx) {
      this.loading = true;
      const path = 'http://localhost:5000/getxy2/' + rowIdx; // eslint-disable-line prefer-template
      console.log('=== getxy2() is fetching path:', path);
      // const start = window.performance.now();
      // replace this with 'arraybuffer' and response.data will be a buffer
      // { responseType: 'arraybuffer', decompress: true })
      let t0 = performance.now();
      let t1 = 0;
      axios.get(path,
        { responseType: 'arraybuffer' })
        .then((res) => {
          t1 = performance.now();
          console.log('  1) got response in ' + (t1 - t0) + ' ms.'); // eslint-disable-line prefer-template
          t0 = performance.now();

          // console.log('  getxy2 res is:');
          // console.log(res);

          // const dataHead = res.data.slice(0, 10);
          // console.log(dataHead);

          // const dataInFloat = new Float64Array(res.data);
          const dataInFloat = new Float32Array(res.data);
          // console.log('dataInFloat.length');
          // console.log(dataInFloat.length);

          const numInHeader = dataInFloat[0];
          const waveLength = dataInFloat[1];

          this.pdata[0].x = dataInFloat.slice(numInHeader, waveLength + 1);
          this.pdata[0].y = dataInFloat.slice(numInHeader + waveLength, (2 * waveLength) + 1);

          t1 = performance.now();
          console.log('  2) converted response in ' + (t1 - t0) + ' ms.'); // eslint-disable-line prefer-template
          t0 = performance.now();

          // Don't need to replot, plotly react(s) to changes in data
          // this.plot_channel();
          // this.username = this.$store.state.user.username;

          t1 = performance.now();
          console.log('  3) plotted response in ' + (t1 - t0) + ' ms.'); // eslint-disable-line prefer-template
          console.log('  getxy2() finished this.username:', this.username);
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
      console.log('i am reacting with react()');
      return Plotly.react('myplot', this.pdata);
    },
  },
  created() {
    this.getxy2(0);
  },
};
</script>
