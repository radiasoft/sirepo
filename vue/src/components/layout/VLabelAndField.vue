<template>
    <div class="col-sm-5" v-if="visible">
        <VLabel
            :field_name="props.field_name"
            :ui_ctx="props.ui_ctx"
        />
    </div>
    <div :class="'col-sm-' + ui_ctx[props.field_name].cols" v-if="visible">
        <VFieldEditor
            :field_name="props.field_name"
            :ui_ctx="props.ui_ctx"
        />
    </div>
</template>

<script setup>
 import VFieldEditor from '@/components/layout/VFieldEditor.vue'
 import VLabel from '@/components/widget/VLabel.vue'
 import { ref, watch } from 'vue';

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });
 const visible = ref(true);

 watch(() => props.ui_ctx[props.field_name].visible, () => {
     visible.value = props.ui_ctx[props.field_name].visible;
 });

</script>
