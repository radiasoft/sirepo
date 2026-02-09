<template>
    <div class="card mb-4 shadow-sm">
        <div v-if="title" class="lead ps-3 pt-2">{{ title }}</div>
        <div class="card-body">
            <slot></slot>
        </div>
    </div>
</template>

<script setup>

 const props = defineProps({
     title: String,
 });

</script>
