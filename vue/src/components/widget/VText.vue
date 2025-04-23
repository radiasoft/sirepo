<!--
   An HTML INPUT field. Submits a value when the enter key is pressed within the input field.
 -->
<template>
    <div>
        <input
            v-model="rawValue"
            autocomplete="off"
            class="form-control form-control-sm"
            :class="{'sr-invalid': isInvalid, 'text-end': isNumeric}"
            :readonly="! ui_ctx[field].enabled"
            :id="field"
        />
    </div>
</template>

<script setup>
 import { ref, watch } from 'vue';
 import { useValidation } from '@/components/widget/validation/useValidation.js'
 import { useNumberValidation } from '@/components/widget/validation/useNumberValidation.js'

 const props = defineProps({
     field: String,
     ui_ctx: Object,
 });
 const isNumeric = ['integer', 'float'].includes(props.ui_ctx[props.field].widget);

 const { isInvalid, parsedValue, rawValue } = isNumeric
     ? useNumberValidation(props.ui_ctx[props.field])
     : useValidation(props.ui_ctx[props.field]);
 rawValue.value = props.ui_ctx[props.field].value;

 watch(props.ui_ctx[props.field], () => {
     rawValue.value = props.ui_ctx[props.field].value;
 });

 watch(parsedValue, () => {
     if (! isInvalid.value) {
         props.ui_ctx[props.field].value = parsedValue.value;
     }
 });

</script>
