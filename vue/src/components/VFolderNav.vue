<template>
    <li :class="{active: folder == selected_folder}">
        <a href @click.prevent="selectFolder">
            <span :class="{
                'bi bi-chevron-right': ! folder.isOpen,
                'bi bi-chevron-down': folder.isOpen,
            }"></span> <span class="bi bi-folder2"></span>
            {{ folder.name }}
        </a>
        <ul v-if="folder.isOpen" v-for="item in getFolders()" :key="item.key" class="nav sr-nav-sidebar">
            <VFolderNav :folder="item" :selected_folder="selected_folder" @folderSelected="folderSelected" />
        </ul>
    </li>
</template>

<script setup>
 import { ref } from 'vue';
 import { simManager } from '@/services/simmanager.js';

 const props = defineProps({
     folder: Object,
     selected_folder: Object,
 });

 const emit = defineEmits(['folderSelected']);

 const folderSelected = (f) => {
     emit('folderSelected', f);
 };

 const getFolders = () => props.folder.children.filter((c) => c.isFolder);

 const selectFolder = () => {
     emit('folderSelected', props.folder);
 };
</script>
