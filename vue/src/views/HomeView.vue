<script setup>
 import Masonry from 'masonry-layout'
 import VCard from '@/components/VCard.vue'
 import VCol from '@/components/VCol.vue'
 import { nextTick, onMounted, onUpdated, reactive, ref } from 'vue';
 import VLabel from '@/components/widget/VLabel.vue'
 import VStatic from '@/components/widget/VStatic.vue'
 import VText from '@/components/widget/VText.vue'
 import VSelect from '@/components/widget/VSelect.vue'

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

 onUpdated(buildLayout);

 const m = reactive({
     first_name: {
         label: 'First Name',
         value: 'Scooby',
     },
     last_name: {
         label: 'Last Name',
         value: 'Doo',
         widget: 'string',
         enabled: true,
     },
     balance: {
         label: 'Balance',
         value: 1.25,
         widget: 'float',
         enabled: true,
     },
     treats: {
         label: 'Treats',
         value: '2x',
         widget: 'enum',
         enabled: true,
         choices: [
             '1x',
             '2x',
             '3x',
             '4x',
             '5x',
         ].map(v => ({ code: v, display: v })),
     },
 });

</script>

<template>
    <div class="row" ref="rowRef">
        <VCol v-for="(item, index) in items">
            <VCard
                :title="'Heading ' + (index + 1)"
                @card-visibility-changed="callLayout()"
            >
                <div class="text-center"
                     :style="{lineHeight: item.height + 'px'}">
                    Content {{ index + 1 }}
                </div>
                <div class="row mb-3">
                    <div class="col-sm-5">
                    <VLabel
                        :field="'first_name'"
                        :ui_ctx="m"
                    />
                    </div>
                    <div class="col-sm-7">
                    <VStatic
                        :field="'first_name'"
                        :ui_ctx="m"
                    />
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-sm-5">
                    <VLabel
                        field="last_name"
                        :ui_ctx="m"
                    />
                    </div>
                    <div class="col-sm-7">
                    <VText
                        field="last_name"
                        :ui_ctx="m"
                    />
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-sm-5">
                    <VLabel
                        field="balance"
                        :ui_ctx="m"
                    />
                    </div>
                    <div class="col-sm-5">
                    <VText
                        field="balance"
                        :ui_ctx="m"
                    />
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-sm-5">
                    <VLabel
                        field="treats"
                        :ui_ctx="m"
                    />
                    </div>
                    <div class="col-sm-7">
                    <VSelect
                        field="treats"
                        :ui_ctx="m"
                    />
                    </div>
                </div>
            </VCard>
        </VCol>
    </div>
</template>


/*
  div mb-3
    label col-form-label col-form-label-sm for=...
    select form-select form-select-sm
*/
