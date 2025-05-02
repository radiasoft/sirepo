<template>
    <div id="sr-masonry-row" class="row" ref="rowRef">
        <slot></slot>
    </div>
</template>

<script setup>
 import { nextTick, onMounted, onUnmounted, onUpdated, ref } from 'vue';
 import Masonry from 'masonry-layout'

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
     //TODO(pjm): assumes only one VMasonry component layout on a page
     for (const c of document.getElementById('sr-masonry-row').children) {
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
