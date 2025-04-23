<!--
   An HTML SELECT element with a list of choices.
 -->
<template>
    <div>
        <select
            v-model="ui_ctx[field].value"
            class="form-select form-select-sm"
            :id="field"
        >
            <option
                v-for="v of ui_ctx[field].choices"
                :key="v.code"
                :value="v.code">{{ v.display }}
            </option>
        </select>
    </div>
</template>

<script setup>
 const props = defineProps({
     field: String,
     ui_ctx: Object,
 });
</script>
