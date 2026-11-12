<template>
    <div class="card mb-4 shadow-sm">
        <div v-if="title" class="d-flex align-items-center pe-3">
            <div class="lead ps-3 pt-2">{{ title }}</div>
            <div class="ms-auto pt-2"><slot name="header"></slot></div>
        </div>
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
