<template>
  <div class="home">
    <RouteMap /> 
  </div>
</template>

<script>
// Make sure this path is correct if your components folder is inside src
import RouteMap from '@/components/RouteMap.vue'; 

export default {
  name: 'IndexPage', // Use a standard page name
  components: {
    RouteMap,
  },
};
</script>