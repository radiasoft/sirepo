<template>
    <VMasonry>
        <VCol v-for="(item, index) in items">
            <VCard
                :title="'Heading ' + (index + 1)"
            >
                <div class="text-center"
                     style="border: 1px solic black; background-color: lightgrey"
                     :style="{lineHeight: item.height + 'px'}">
                    Content {{ index + 1 }}
                </div>
                <VForm :ui_ctx="item.m" :layout="v" />
            </VCard>
        </VCol>
    </VMasonry>
</template>

<script setup>
 import VCard from '@/components/VCard.vue'
 import VCol from '@/components/layout/VCol.vue'
 import VForm from '@/components/VForm.vue'
 import VMasonry from '@/components/layout/VMasonry.vue'
 import { appState } from '@/services/appstate.js';
 import { reactive } from 'vue';

 const items = reactive([
     { height: 150, m: reactive(appState.getUIContext('dog')) },
     { height: 100, m: reactive(appState.getUIContext('dog')) },
     { height: 100, m: reactive(appState.getUIContext('dog')) },
     { height: 266, m: reactive(appState.getUIContext('dog')) },
     { height: 150, m: reactive(appState.getUIContext('dog')) },
     { height: 100, m: reactive(appState.getUIContext('dog')) },
     { height: 150, m: reactive(appState.getUIContext('dog')) },
 ]);

 const v = [
     'first_name',
     'last_name',
     'balance',
     'treats',
 ];

</script>
