<script setup>
 import { nextTick, onMounted, onUpdated, onUnmounted, reactive, ref } from 'vue';
 import Masonry from 'masonry-layout'
 import VCard from '@/components/VCard.vue'
 import VCol from '@/components/layout/VCol.vue'
 import VForm from '@/components/VForm.vue'
 import { useModelStore } from '@/stores/models'

 const rowRef = ref(null);
 let masonry = null;

 const items = [
     { height: 150 },
     { height: 100 },
     { height: 100 },
     { height: 266 },
     { height: 150 },
     { height: 100 },
     { height: 150 },
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
 });

 onUnmounted(() => {
     if (masonry) {
         masonry.destroy();
     }
 });

 onUpdated(buildLayout);

 const store = useModelStore();

 const m = reactive({
     first_name: {
         label: 'First Name',
         value: store.dog.first_name,
         widget: 'static',
         visible: true,
         cols: 5,
     },
     last_name: {
         label: 'Last Name',
         value: store.dog.last_name,
         widget: 'text',
         enabled: true,
         visible: true,
         cols: 5,
     },
     balance: {
         label: 'Balance',
         value: store.dog.balance,
         widget: 'float',
         enabled: true,
         visible: true,
         cols: 3,
         tooltip: 'Account balance',
     },
     treats: {
         label: 'Treats',
         value: store.dog.treats,
         widget: 'select',
         enabled: true,
         choices: [
             '1x',
             '2x',
             '3x',
             '4x',
             '5x',
         ].map(v => ({ code: v, display: v })),
         visible: true,
         cols: 5,
     },
 });

 const v = [
     'first_name',
     'last_name',
     'balance',
     'treats',
 ];

</script>

<template>
    <div class="row" ref="rowRef">
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
                <VForm :ui_ctx="m" :layout="v" />
            </VCard>
        </VCol>
    </div>
</template>
