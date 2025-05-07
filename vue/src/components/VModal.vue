<template>
    <div v-if="modalCreated" class="modal fade" :id="viewName" tabindex="-1" ref="modal">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header text-bg-info bg-opacity-25">
                    <span class="sr-panel-header lead">{{ title }}</span>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <VForm :viewName="viewName" fieldDef="advanced" ref="form" @dismissModal="closeModal"/>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
 import VForm from '@/components/VForm.vue'
 import { Modal } from "bootstrap";
 import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

 const props = defineProps({
     title: String,
     viewName: String,
 });

 let bootstrapModal = null;
 const form = ref(null);
 const modal = ref(null);
 const modalCreated = ref(false);

 const blurActiveElement = () => {
     // work around "Block aria-hidden" console warning when bootstrap modal is closed
     if (document.activeElement instanceof HTMLElement) {
         document.activeElement.blur();
     }
 };

 const cancelChanges = () => form.value.cancelChanges();

 const closeModal = () => bootstrapModal.hide();

 const showModal = () => {
     if (! modalCreated.value) {
         modalCreated.value = true;
         nextTick(() => {
             bootstrapModal = new Modal(modal.value);
             modal.value.addEventListener('hidden.bs.modal', cancelChanges);
             modal.value.addEventListener('hide.bs.modal', blurActiveElement);
             bootstrapModal.show();
         });
         return;
     }
     bootstrapModal.show();
 };

 onBeforeUnmount(() => {
     if (bootstrapModal) {
         bootstrapModal.hide();
         modal.value.removeEventListener('hidden.bs.modal', cancelChanges);
         modal.value.removeEventListener('hide.bs.modal', blurActiveElement);
         bootstrapModal.dispose();
     }
 });

 defineExpose({ showModal });
</script>
