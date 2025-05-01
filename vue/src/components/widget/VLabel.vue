<!--
   A form field label.
 -->
<template>
    <div class="text-end">
        <label
            class="col-form-label col-form-label-sm"
        >
            {{ ui_ctx[field_name].label }}
        <span v-if="ui_ctx[field_name].tooltip">
            <VTooltip :tooltip="ui_ctx[field_name].tooltip" />
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
</script>
