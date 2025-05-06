<template>
    <form @submit.prevent autocomplete="off" novalidate>
        <div class="row" v-for="f of layout">
            <VLabelAndField
                :field_name="f"
                :ui_ctx="ui_ctx"
            />
        </div>
        <div class="row" v-show="isFormDirty()">
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
 import { PubSub } from '@/services/pubsub.js';
 import { appState } from '@/services/appstate.js';
 import { onMounted, onUnmounted, reactive } from 'vue';

 const props = defineProps({
     viewName: String,
     fieldDef: String,
 });

 const ui_ctx = reactive(appState.getUIContext(props.viewName, props.fieldDef));

 //TODO(pjm): view layout may be complicated with columns and tabs
 const layout = ui_ctx.viewSchema[ui_ctx.fieldDef];

 const cancelChanges = () => ui_ctx.cancelChanges(ui_ctx);

 const isFormDirty = () => ui_ctx.isDirty();

 const isInvalid = () => ui_ctx.isInvalid();

 const onModelChanged = (names) => {
     //TODO(pjm): only call if named models are used by UIContext
     cancelChanges();
 };

 const saveChanges = () => {
     ui_ctx.saveChanges();
 };

 onMounted(() => {
     PubSub.subscribe(appState.MODEL_CHANGED_EVENT, onModelChanged);
 });

 onUnmounted(() => {
     PubSub.unsubscribe(appState.MODEL_CHANGED_EVENT, onModelChanged);
 });
</script>
