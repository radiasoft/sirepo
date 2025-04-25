<script setup>
 import { onMounted, onBeforeUnmount, ref } from 'vue';

 defineProps({
     title: String,
 });

 const emit = defineEmits(['card-visibility-changed']);
 const cardStyle = ref({});
 const hidden = ref(false);

 const onKeydown = (event) => {
     if (event.key == 'Escape' && isFullscreen()) {
         toggleFullscreen();
     }
 };

 const isFullscreen = () => !!cardStyle.value.position;

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
     emit('card-visibility-changed');
 };

 onBeforeUnmount(() => {
     document.removeEventListener('keydown', onKeydown);
 });

 onMounted(() => {
     document.addEventListener('keydown', onKeydown);
 });

</script>

<template>
    <div class="card mb-4" :style="cardStyle">
        <div class="sr-panel-header card-header lead text-bg-info bg-opacity-25">
            {{ title }}
            <div class="sr-panel-options float-end">
                <a href title="Edit"><span class="bi bi-pencil-fill"></span></a>
                <div class="dropdown-menu-end" style="display: inline-block" title="Download">
                    <a href data-bs-toggle="dropdown"><span class="bi bi-cloud-download-fill"></span></a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#">Action</a></li>
                        <li><a class="dropdown-item" href="#">Another action</a></li>
                        <li><a class="dropdown-item" href="#">Something else here</a></li>
                    </ul>
                </div>
                <a href
                   @click.prevent="toggleFullscreen()"
                   v-if="! hidden"
                   :title="isFullscreen() ? 'Exit Full Screen' : 'Full Screen'"
                >
                    <span :class="{
                                  'bi bi-fullscreen-exit': isFullscreen(),
                                  'bi bi-fullscreen': ! isFullscreen()
                                  }"></span>
                </a>
                <a href
                   @click.prevent="toggleHidden()"
                   v-if="! isFullscreen()"
                   :title="hidden ? 'Show' : 'Hide'"
                >
                    <span :class="{
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
</template>
