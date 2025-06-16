<template>
    <form @submit.prevent autocomplete="off" novalidate>
        <div class="row" v-for="f of layout">
            <VLabelAndField
                :field_name="f"
                :ui_ctx="ui_ctx"
            />
        </div>
        <slot></slot>
        <div class="row" v-show="showButtons()">
            <div class="col-sm-12 text-center">
                <button
                    class="btn btn-primary sr-button-save-cancel"
                    :disabled="isInvalid()"
                    @click="saveChanges"
                >
                    Save
                </button>
                <button
                    type="button"
                    class="btn btn-outline-secondary sr-button-save-cancel"
                    @click="cancelChanges"
                >
                    Cancel
                </button>
            </div>
        </div>
    </form>
</template>

<script setup>
 import VLabelAndField from '@/components/layout/VLabelAndField.vue'
 import { appResources } from '@/services/appresources.js';
 import { appState, MODEL_CHANGED_EVENT } from '@/services/appstate.js';
 import { onMounted, onUnmounted, reactive } from 'vue';
 import { pubSub } from '@/services/pubsub.js';

 const props = defineProps({
     viewName: String,
     fieldDef: String,
     wantButtons: {
         type: Boolean,
         default: true,
     },
 });

 const emit = defineEmits(['dismissModal']);

 const ui_ctx = reactive(appState.getUIContext(props.viewName, props.fieldDef));

 //TODO(pjm): view layout may be complicated with columns and tabs
 const layout = ui_ctx.viewSchema[ui_ctx.fieldDef];

 const cancelChanges = () => {
     ui_ctx.cancelChanges(ui_ctx);
     emit('dismissModal');
 };

 const isInvalid = () => ui_ctx.isInvalid();

 const onModelChanged = (names) => {
     //TODO(pjm): only call if named models are used by UIContext
     cancelChanges();
 };

 const saveChanges = async () => {
     await ui_ctx.saveChanges();
     emit('dismissModal');
 };

 const showButtons = () => props.wantButtons && ui_ctx.isDirty();

 onMounted(() => {
     pubSub.subscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODEL_CHANGED_EVENT, onModelChanged);
 });

 appResources.initViewLogic(props.viewName, ui_ctx);

 defineExpose({ cancelChanges });
</script>
