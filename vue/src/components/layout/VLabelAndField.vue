<template>
    <div :class="columnClass('labelcols')" v-if="visible">
        <VLabel
            :field_name="props.field_name"
            :ui_ctx="props.ui_ctx"
        />
    </div>
    <div :class="columnClass('cols')" v-if="visible">
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

 const visible = ref(props.ui_ctx.fields[props.field_name].visible);

 const columnClass = (colField) => `col-sm-${props.ui_ctx.fields[props.field_name][colField] || 5}`;

 watch(() => props.ui_ctx.fields[props.field_name].visible, () => {
     visible.value = props.ui_ctx.fields[props.field_name].visible;
 });

</script>
