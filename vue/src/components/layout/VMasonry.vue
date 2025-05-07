<template>
    <div class="row" ref="rowRef">
        <slot></slot>
    </div>
</template>

<script setup>
 import Masonry from 'masonry-layout'
 import { nextTick, onMounted, onUnmounted, onUpdated, ref } from 'vue';

 const rowRef = ref(null);
 let masonry;
 let resizeObserver;

 const buildLayout = () => {
     masonry = new Masonry(rowRef.value, {
         percentPosition: true,
         // transitionDuration: 0,
         // horizontalOrder: true,
     });
     if (resizeObserver) {
         resizeObserver.disconnect();
     }
     else {
         //TODO(pjm): add debouncer
         resizeObserver = new ResizeObserver(() => masonry.layout());
     }
     for (const c of rowRef.value.children) {
         resizeObserver.observe(c);
     }
 };

 onMounted(() => nextTick(buildLayout));

 onUnmounted(() => {
     if (masonry) {
         masonry.destroy();
     }
     if (resizeObserver) {
         resizeObserver.disconnect();
     }
 });

 onUpdated(buildLayout);
</script>
