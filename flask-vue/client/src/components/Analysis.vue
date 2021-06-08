<template>
  <div class="container">
    <div class="row">
      <div class="col-sm-10">
        <file-list :username='username'></file-list>
    </div> <!-- col -->
    </div> <!-- row -->

    <div class="row">
      <div>
        <!-- <my-plotly :myusername="robert.cudmore" /> -->
        <my-plotly :username='username'></my-plotly>
        FileList.vue username:{{username}}
      </div>
    </div>

  </div> <!-- container -->
</template>

<script>
import FileList from '@/components/FileList.vue';
import MyPlotly from '@/components/MyPlotly.vue';

export default {
  components: {
    FileList,
    MyPlotly,
  },
  data() {
    return {
      username: '',
    };
  },
};
</script>
