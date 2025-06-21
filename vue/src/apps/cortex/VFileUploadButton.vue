<template>
    <label
        v-bind:for="elementId"
        class="btn btn-outline-secondary"
    >
        <slot></slot>
    </label>
    <input
        style="display: none"
        v-bind:id="elementId"
        type="file"
        v-on:change="onFileChanged"
        v-bind:accept="mimeType"
        ref="fileInput"
    />
</template>

<script setup>
 import { ref } from 'vue';

 defineProps({
     mimeType: String,
 });
 const elementId = 'dropZoneFile';
 const emit = defineEmits(['fileChanged']);
 let fileInput = ref(null);

 const onFileChanged = () => {
     if (fileInput.value && fileInput.value.files.length) {
         emit('fileChanged', fileInput.value.files);
     }
 };
</script>
