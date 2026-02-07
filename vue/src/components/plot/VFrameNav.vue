<template>
    <div class="text-center" v-if="frameCount > 1">
        <button class="btn btn-outline-secondary sr-frame-nav-btn"
                v-bind:disabled="frameIndex == 1"
                v-on:click="goStart"><span class="bi bi-chevron-bar-left"></span></button>
        <button class="btn btn-outline-secondary sr-frame-nav-btn"
                v-bind:disabled="frameIndex == 1"
                v-on:click="goPrev"><span class="bi bi-chevron-left"></span></button>

        <button v-if="! isPlaying" class="btn btn-outline-secondary sr-frame-nav-btn"
                v-on:click="play"><span class="bi bi-play"></span></button>
        <button v-if="isPlaying" class="btn btn-outline-secondary sr-frame-nav-btn"
                v-on:click="pause"><span class="bi bi-pause"></span></button>

        <button class="btn btn-outline-secondary sr-frame-nav-btn"
                v-bind:disabled="frameIndex == frameCount"
                v-on:click="goNext"><span class="bi bi-chevron-right"></span></button>
        <button class="btn btn-outline-secondary sr-frame-nav-btn"
                v-bind:disabled="frameIndex == frameCount"
                v-on:click="goEnd"><span class="bi bi-chevron-bar-right"></span></button>
    </div>
</template>

<script setup>
 import { ref, onMounted, watch } from 'vue';

 const props = defineProps({
     frameCount: Number,
 });
 const emit = defineEmits(['frameChanged', 'isPlayingChanged']);
 const frameIndex = ref(1);
 const isPlaying = ref(false);

 const goEnd = () => {
     update(props.frameCount);
 };

 const goNext = () => {
     update(frameIndex.value + 1);
 };

 const goPrev = () => {
     update(frameIndex.value - 1);
 };

 const goStart = () => {
     update(1);
 };

 const play = () => {
     updateIsPlaying(true);
 };

 const pause = () => {
     updateIsPlaying(false);
 };

 const update = (newFrameIndex) => {
     if (newFrameIndex >= 1 && newFrameIndex <= props.frameCount && newFrameIndex !== frameIndex.value) {
         frameIndex.value = newFrameIndex;
         emit('frameChanged', frameIndex.value);
     }
 };

 const updateIsPlaying = (newIsPlaying) => {
     if (newIsPlaying != isPlaying.value) {
         isPlaying.value = newIsPlaying;
         emit('isPlayingChanged', isPlaying.value);
     }
 };

 onMounted(() => {
     frameIndex.value = props.frameCount;
 });

 watch(() => props.frameCount, () => {
     frameIndex.value = props.frameCount;
 });
</script>

<style scoped>
 .sr-frame-nav-btn {
     margin: 1ex;
 }
</style>
