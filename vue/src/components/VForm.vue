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
 import { onMounted, onUnmounted } from 'vue';

 const props = defineProps({
     ui_ctx: Object,
 });

 const layout = props.ui_ctx._view.basic;

 const cancelChanges = () => {
     loadFromModel('dog');
 };

 const isFormDirty = () => {
     for (const f in props.ui_ctx) {
         if (props.ui_ctx[f].isDirty) {
             return true;
         }
     }
     return false;
 };

 const isInvalid = () => {
     for (const f in props.ui_ctx) {
         if (props.ui_ctx[f].visible && props.ui_ctx[f].isInvalid) {
             return true;
         }
     }
     return false;
 };

 const loadFromModel = (name) => {
     const m = appState.models[name];
     for (const f in m) {
         if (f in props.ui_ctx) {
             props.ui_ctx[f].val = m[f];
             props.ui_ctx[f].isDirty = false;
         }
     }
 };

 const onModelChanged = (names) => {
     loadFromModel(names[0]);
 };

 const saveChanges = () => {
     appState.saveChanges({
         dog: {
             first_name: props.ui_ctx.first_name.val,
             last_name: props.ui_ctx.last_name.val,
             balance: props.ui_ctx.balance.val,
             treats: props.ui_ctx.treats.val,
         },
     });
 };

 onMounted(() => {
     PubSub.subscribe("modelChanged", onModelChanged);
 });

 onUnmounted(() => {
     PubSub.unsubscribe("modelChanged", onModelChanged);
 });
</script>
