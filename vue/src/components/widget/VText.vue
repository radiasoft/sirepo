<!--
   An HTML INPUT field. Submits a value when the enter key is pressed within the input field.
 -->
<template>
    <div>
        <input
            v-model="rawValue"
            type="text"
            autocomplete="off"
            class="form-control form-control-sm"
            :class="{
                'sr-invalid': isInvalid,
                'text-end': isNumeric,
            }"
            :readonly="! ui_ctx[field_name].enabled"
            @keydown="onKeydown()"
        />
    </div>
</template>

<script setup>
 import { ref, watch } from 'vue';
 import { useValidation } from '@/components/widget/validation/useValidation.js'
 import { useNumberValidation } from '@/components/widget/validation/useNumberValidation.js'

 const props = defineProps({
     field_name: String,
     ui_ctx: Object,
 });

 const field = () => props.ui_ctx[props.field_name];
 const isNumeric = ['integer', 'float'].includes(field().widget);
 const { isInvalid, parsedValue, rawValue } = isNumeric
     ? useNumberValidation(field())
     : useValidation(field());

 //TODO(pjm): move to a utility
 const formatExponential = (value) => {
     if (Math.abs(value) >= 10000 || (value != 0 && Math.abs(value) < 0.001)) {
         value = (+value).toExponential(9).replace(/\.?0+e/, 'e');
     }
     return value;
 };

 const formatRawValue = () => {
     rawValue.value = field().val;
     if (field().widget === 'float') {
         rawValue.value = formatExponential(rawValue.value);
     }
 }

 const onKeydown = () => {
     field().isDirty = true;
 };

 watch(() => field().val, () => {
     if (field().val !== parsedValue.value) {
         rawValue.value = field().val;
     }
 });

 watch(() => field().isDirty, () => {
     // reset rawValue when isDirty is cleared
     if (! field().isDirty) {
         formatRawValue();
     }
 });

 watch(parsedValue, () => {
     field().isInvalid = isInvalid.value;
     if (! isInvalid.value) {
         field().val = parsedValue.value;
     }
 });

 formatRawValue();

</script>
