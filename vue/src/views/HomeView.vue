<template>
    <VMasonry>
        <VCol v-for="(item, index) in items">
            <VCard
                :title="'Heading ' + (index + 1)"
            >
                <div class="text-center mb-3"
                     style="border: 1px solic black; background-color: lightgrey"
                     :style="{lineHeight: item.height + 'px'}">
                    Content {{ index + 1 }}
                </div>
                <VForm :viewName="viewName" fieldDef="basic" />
            </VCard>
        </VCol>
    </VMasonry>
</template>

<script setup>
 import VCard from '@/components/VCard.vue'
 import VCol from '@/components/layout/VCol.vue'
 import VForm from '@/components/VForm.vue'
 import VMasonry from '@/components/layout/VMasonry.vue'
 import { reactive } from 'vue';

 const viewName = "dog";

 const items = reactive([
     { height: 150 },
     { height: 100 },
     { height: 100 },
     { height: 266 },
     { height: 150 },
     { height: 100 },
     { height: 150 },
 ]);

</script>
