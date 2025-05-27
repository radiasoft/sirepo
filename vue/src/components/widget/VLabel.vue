<!--
   A form field label.
 -->
<template>
    <div :class="labelClass()">
        <label
            class="col-form-label col-form-label-sm"
        >
            {{ ui_ctx.fields[field_name].label }}
        <span v-if="ui_ctx.fields[field_name].tooltip">
            <VTooltip :tooltip="ui_ctx.fields[field_name].tooltip" />
        </span>
        </label>
    </div>
</template>

<script setup>
 import VTooltip from '@/components/VTooltip.vue'

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 const labelClass = () => {
     if (props.ui_ctx.fields[props.field_name].labelcols === 12) {
         return 'sr-form-longlabel';
     }
     return 'sr-form-label';
 };
</script>
