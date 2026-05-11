<template>
 <div v-bind:class="colClass">
     <slot></slot>
 </div>
</template>

<script setup>
 const props = defineProps({
     maxCols: {
         type: Number,
         default: 4,
     },
 });
 const colClass = {
     1: "col-sm-12",
     2: "col-md-6",
     3: "col-md-6 col-xxl-4",
     4: "col-md-6 col-xl-4 col-xxl-3",
 }[props.maxCols];
</script>
