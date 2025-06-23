<!--
   An HTML INPUT field.
 -->
<template>
    <div>
        <input
            v-model="rawValue"
            type="text"
            autocomplete="off"
            class="form-control form-control-sm"
            :class="{
                'sr-invalid': isInvalid || error,
                [$attrs.class]: $attrs.class,
            }"
            :disabled="! enabled"
            :readonly="! enabled"
            @input="onInput"
        />
        <div v-if="error" class="invalid-feedback">
            {{ error }}
        </div>
    </div>
</template>

<script setup>
 import { ref, watch } from 'vue';
 import { useWidget } from '@/components/widget/useWidget.js';

 const props = defineProps({
     field_name: {
         type: String,
         required: true,
     },
     ui_ctx: {
         type: Object,
         required: true,
     },
     validation: {
         type: Function,
         required: true,
     },
     inputClass: String,
     formatter: Function,
     defaultCols: Number,
 });

 const { enabled, error, field, onInput } = useWidget(props.ui_ctx, props.field_name);

 const { isInvalid, parsedValue, rawValue } = props.validation(field());

 const formatRawValue = () => {
     rawValue.value = field().val;
     if (props.formatter) {
         rawValue.value = props.formatter(rawValue.value);
     }
 }

 watch(() => field().val, () => {
     if (field().val !== parsedValue.value) {
         formatRawValue();
     }
 });

 watch(() => field().dirty, () => {
     // reset rawValue when dirty is cleared
     if (! field().dirty) {
         formatRawValue();
     }
 });

 watch(parsedValue, () => {
     field().invalid = isInvalid.value;
     if (! isInvalid.value) {
         field().val = parsedValue.value;
     }
 });

 if (props.defaultCols && ! field().cols) {
     field().cols = props.defaultCols;
 }

 formatRawValue();
</script>
