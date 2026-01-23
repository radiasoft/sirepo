//TODO(pjm): dropdown-menu should be a named slot
<template>
    <div class="card mb-4" v-bind:style="cardStyle">
        <div class="sr-panel-header card-header text-bg-info bg-opacity-25">
            {{ title }}
            <div class="sr-panel-options float-end">
                <a v-if="canEdit" href title="Edit" v-on:click.prevent="showModal"><span class="bi bi-pencil-fill"></span></a>
                <div v-if="downloadActions" class="dropdown-menu-end d-inline-block" title="Download">
                    <a href data-bs-toggle="dropdown"><span class="bi bi-cloud-download-fill"></span></a>
                    <ul class="dropdown-menu">
                        <li v-for="action in downloadActions">
                            <a href class="dropdown-item" v-on:click.prevent="action.onClick">{{ action.label }}</a>
                        </li>
                    </ul>
                </div>
                <a href
                   v-on:click.prevent="toggleFullscreen()"
                   v-if="canFullScreen && ! hidden"
                   v-bind:title="isFullscreen() ? 'Exit Full Screen' : 'Full Screen'"
                >
                    <span v-bind:class="{
                        'bi bi-fullscreen-exit': isFullscreen(),
                        'bi bi-fullscreen': ! isFullscreen()
                    }"></span>
                </a>
                <a href
                   v-on:click.prevent="toggleHidden()"
                   v-if="! isFullscreen()"
                   v-bind:title="hidden ? 'Show' : 'Hide'"
                >
                    <span v-bind:class="{
                        'bi bi-chevron-down': hidden,
                        'bi bi-chevron-up': ! hidden
                    }"></span>
                </a>
            </div>
        </div>
        <div class="card-body" v-show="! hidden">
            <slot></slot>
        </div>
    </div>
    <div v-if="canEdit">
        <VFormModal v-bind:viewName="viewName" v-bind:title="title" ref="modal"/>
    </div>
</template>

<script setup>
 import VFormModal from '@/components/VFormModal.vue'
 import { onBeforeUnmount, onMounted, ref } from 'vue';
 import { schema } from '@/services/schema.js';

 const props = defineProps({
     viewName: String,
     title: String,
     canFullScreen: Boolean,
     downloadActions: Array,
 });

 if (! schema.view[props.viewName]) {
     throw new Error(`Missing schema entry for ${props.viewName}`);
 }
 const canEdit = schema.view[props.viewName].advanced.length > 0;
 const cardStyle = ref({});
 const hidden = ref(false);
 const modal = ref(null);
 const title = props.title || schema.view[props.viewName].title;

 const onKeydown = (event) => {
     if (event.key == 'Escape' && isFullscreen()) {
         toggleFullscreen();
     }
 };

 const isFullscreen = () => !!cardStyle.value.position;

 const showModal = () => modal.value.showModal();

 const toggleFullscreen = () => {
     cardStyle.value = isFullscreen()
         ? {}
         : {
             position: 'fixed',
             left: 0,
             top: 0,
             width: '100%',
             height: '100%',
             overflow: 'hidden',
             zIndex: 1000,
         };
 };

 const toggleHidden = () => {
     hidden.value = ! hidden.value;
 };

 onBeforeUnmount(() => {
     document.removeEventListener('keydown', onKeydown);
 });

 onMounted(() => {
     document.addEventListener('keydown', onKeydown);
 });
</script>
