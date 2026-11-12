<template>
    <div v-if="props.image">
        <img class="img-fluid" v-bind:src="props.image" v-bind:alt="props.alt" />
    </div>
</template>

<script setup>
 import { onUnmounted, ref } from 'vue';

 const props = defineProps({
     image: String,
     alt: String,
 });

 onUnmounted(() => {
     if (props.image) {
         URL.revokeObjectURL(props.image);
     }
 });
</script>
