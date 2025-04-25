<template>
    <form>
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
        <div class="row" v-show="isFormDirty()">
            <div class="col-sm-12 text-center">
                <button type="button" class="btn btn-primary sr-button-save-cancel">Save</button>
                <button type="button" class="btn btn-outline-secondary sr-button-save-cancel">Cancel</button>
            </div>
        </div>
    </form>
</template>

<script setup>
 import VFieldEditor from '@/components/layout/VFieldEditor.vue'
 import VLabel from '@/components/widget/VLabel.vue'

 const props = defineProps({
     layout: Object,
     ui_ctx: Object,
 });

 const isFormDirty = () => {
     return true;
 };
</script>
