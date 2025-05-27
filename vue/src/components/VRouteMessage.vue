<template>
    <p>{{ message }}</p>
</template>

<script setup>
 // Used by error and single message routes
 import { ref } from 'vue';

 const message = ref('a simple message');
 //TODO(pjm): implement this switching the message depending on the current route name and params
</script>
