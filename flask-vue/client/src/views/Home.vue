<template>
  <div class="home">
    <img alt="Vue logo" width=100 src="../assets/logo.png">
    <HelloWorld msg="xxx Welcome to Your Vue.js App"/>
  </div>
</template>

/*
multi line comment
*/

<script>
// @ is an alias to /src
import HelloWorld from '@/components/HelloWorld.vue';

export default {
  name: 'Home',
  components: {
    HelloWorld,
  },
};
</script>
