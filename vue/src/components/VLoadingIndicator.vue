<template>
    <div
        xstyle="margin-left: 2em; margin-top: 1ex;"
        class="lead text-center mt-2"
        v-if="message && ready"
    >
        <img src="/static/img/sirepo_animated.gif" /> {{ message }}
    </div>
</template>

<script setup>
 import { ref, onMounted } from 'vue';

 const props = defineProps({
     message: String,
 });
 const ready = ref(false);

 onMounted(() => {
     setTimeout(
         () => ready.value = true,
         500,
     );
 });
</script>
