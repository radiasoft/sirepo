<template>
    <div class="row" v-for="f of layout">
        <div class="col-sm-5">
            <VLabel
                :field="f"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div :class="'col-sm-' + ui_ctx[f].cols">
            <VFieldEditor
                :field="f"
                :ui_ctx="ui_ctx"
            />
        </div>
    </div>

</template>

<script setup>
 import VFieldEditor from '@/components/layout/VFieldEditor.vue'
 import VLabel from '@/components/widget/VLabel.vue'

 const props = defineProps({
     layout: Object,
     ui_ctx: Object,
 });
</script>
