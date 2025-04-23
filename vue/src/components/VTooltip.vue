<template>
    <span class="bi bi-info-circle-fill" ref="spanRef"></span>
</template>

<script setup>
 import { onMounted, ref } from 'vue';

 const props = defineProps({
     tooltip: String,
 });

 const spanRef = ref(null);

 onMounted(() => {
 });


</script>
