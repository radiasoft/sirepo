<template>
    <RouterLink
        v-bind:to="{
            name: routeName,
            params: {
                materialId: materialId,
            },
        }"
    >
        <slot></slot>
    </RouterLink>
</template>

<script setup>
 import { RouterLink } from 'vue-router';

 const props = defineProps({
     materialId: Number,
     isPublic: Boolean,
 });

 const routeName = props.isPublic ? 'view' : 'material';
</script>
