<template>
  <div class="container">
    <div>
      <b-table
        :items="filelist"
        :fields="fields"
        :sort-by.sync="sortBy"
        :sort-desc.sync="sortDesc"
        :head-variant="headVariant"
        label-sort-asc=""
        label-sort-desc=""
        label-sort-clear=""
        sort-icon-left
        bordered
        small
        striped
        :hover=true
        @row-clicked="myRowClickHandler"
      ></b-table>
    </div>
  </div> <!-- container -->
</template>

<script>
import axios from 'axios';

export default {
  components: {
    // MyPlotly,
  },
  data() {
    return {
      // specify the columns to show in table
      // fields: ['file', 'recordingDur_sec', 'recording_kHz'],
      headVariant: 'dark',
      sortBy: 'file',
      sortDesc: false,
      fields: [
        {
          key: 'file',
          label: 'File',
          sortable: true,
        },
        {
          key: 'recordingDur_sec',
          label: 'Dur(s)',
          sortable: true,
        },
        {
          key: 'recording_kHz',
          label: 'kHz',
          sortable: true,
          // Variant applies to the whole column, including the header and footer
          // variant: 'danger'
        },
      ],
      filelist: [],
      username: [],
    };
  },
  methods: {
    fileList() {
      const path = 'http://localhost:5000/filelist';
      axios.get(path)
        .then((res) => {
          this.filelist = res.data.fileList;
          this.username = this.$store.state.user.username;
        })
        .catch((error) => {
          // eslint-disable-next-line
          console.error(error);
        });
    },
    myRowClickHandler(item, index) {
      // 'item' will be the row data from items
      // `index` will be the visible row number (available in the v-model 'shownItems')
      console.log('myRowClickHandler'); // This will be the item data for the row
      console.log(item); // This will be the item data for the row
      console.log(index); // This will be the item data for the row
      // this.$set(item, '_showDetails', !item._showDetails);
      // this.$set(item, '_showDetails', true);
      // load from index
      this.$root.$emit('myPlotlyLoadFile', index, item);
    },

  },
  created() {
    this.fileList();
  },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
</style>
