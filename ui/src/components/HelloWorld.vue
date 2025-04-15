<script setup>
 defineProps({
     msg: {
         type: String,
         required: true,
     },
 })
</script>

<template>
    <div>Heading, {{ msg }}</div>
    <hr />
</template>

<style scoped>
</style>
