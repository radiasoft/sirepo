<script setup>
 import Masonry from 'masonry-layout'
 import VCard from '@/components/VCard.vue'
 import VCol from '@/components/VCol.vue'
 import { nextTick, onMounted, onUpdated, ref } from 'vue';

 const masonry = ref(null);

 const items = [
     { height: 150 },
     { height: 100 },
     { height: 100 },
     { height: 266 },
     { height: 150 },
     { height: 100 },
     { height: 150 },
 ];

 const layout = () => {
     masonry.value = new Masonry(masonry.value, {
         percentPosition: true,
     })
 };

 onMounted(() => {
     nextTick(layout);
 });

 onUpdated(layout);
</script>

<template>
    <div class="row" ref="masonry">
        <VCol v-for="(item, index) in items">
            <VCard
                :title="'Heading ' + (index + 1)"
                :height="item.height">
                Content {{ index + 1 }}
            </VCard>
        </VCol>
    </div>
</template>
