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
  },
  created() {
    this.fileList();
  },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
</style>
