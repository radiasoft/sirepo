<template>
    <span class="bi bi-info-circle" ref="spanRef"></span>
</template>

<script setup>
 import { onMounted, onUnmounted, ref } from 'vue';
 import { Tooltip } from 'bootstrap';

 const props = defineProps({
     tooltip: String,
 });

 const spanRef = ref(null);
 let bsTooltip;

 onMounted(() => {
     bsTooltip = new Tooltip(spanRef.value, {
         title: props.tooltip,
         placement: 'bottom',
         container: 'body',
     });
 });

 onUnmounted(() => {
     if (bsTooltip) {
         bsTooltip.dispose();
     }
 });
</script>
