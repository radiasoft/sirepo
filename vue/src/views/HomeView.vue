<script setup>
 import { nextTick, onMounted, onUpdated, onUnmounted, reactive, ref } from 'vue';
 import Masonry from 'masonry-layout'
 import VCard from '@/components/VCard.vue'
 import VCol from '@/components/layout/VCol.vue'
 import VForm from '@/components/VForm.vue'
 import { appState } from '@/services/appstate.js';

 const rowRef = ref(null);
 let masonry;
 let resizeObserver;

 const items = [
     { height: 150, m: reactive(appState.getUIContext('dog')) },
     { height: 100, m: reactive(appState.getUIContext('dog')) },
     { height: 100, m: reactive(appState.getUIContext('dog')) },
     { height: 266, m: reactive(appState.getUIContext('dog')) },
     { height: 150, m: reactive(appState.getUIContext('dog')) },
     { height: 100, m: reactive(appState.getUIContext('dog')) },
     { height: 150, m: reactive(appState.getUIContext('dog')) },
 ];

 const buildLayout = () => {
     masonry = new Masonry(rowRef.value, {
         percentPosition: true,
         // transitionDuration: 0,
         // horizontalOrder: true,
     });
 };

 const callLayout = () => {
     nextTick(() => masonry.layout());
 };

 onMounted(() => {
     nextTick(buildLayout);
     resizeObserver = new ResizeObserver(() => {
         nextTick(() => masonry.layout());
     });
     //TODO(pjm): this assumes a static list of child panels
     for (const c of document.getElementById('sr-home-row').children) {
         resizeObserver.observe(c);
     }
 });

 onUnmounted(() => {
     if (masonry) {
         masonry.destroy();
     }
     if (resizeObserver) {
         resizeObserver.disconnect();
     }
 });

 onUpdated(buildLayout);

 const v = [
     'first_name',
     'last_name',
     'balance',
     'treats',
 ];

</script>

<template>
    <div id="sr-home-row" class="row" ref="rowRef">
        <VCol v-for="(item, index) in items">
            <VCard
                :title="'Heading ' + (index + 1)"
                @card-visibility-changed="callLayout()"
            >
                <div class="text-center"
                     style="border: 1px solic black; background-color: lightgrey"
                     :style="{lineHeight: item.height + 'px'}">
                    Content {{ index + 1 }}
                </div>
                <VForm :ui_ctx="item.m" :layout="v" />
            </VCard>
        </VCol>
    </div>
</template>
