<template>
    <label
        v-bind:for="elId"
        class="btn btn-outline-secondary"
    >
        <slot></slot>
    </label>
    <input
        class="d-none"
        v-bind:id="elId"
        type="file"
        v-on:change="onFileChanged"
        v-bind:accept="mimeType"
        ref="fileInput"
    />
</template>

<script setup>
 import { ref } from 'vue';
 import { util } from '@/services/util.js';

 defineProps({
     mimeType: String,
 });
 const elId = util.uniqueId();
 const emit = defineEmits(['fileChanged']);
 let fileInput = ref(null);

 const onFileChanged = () => {
     if (fileInput.value && fileInput.value.files.length) {
         emit('fileChanged', fileInput.value.files);
     }
 };
</script>
