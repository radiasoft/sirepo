<template>
    <div
        v-if="modalCreated"
        class="modal fade"
        tabindex="-1"
        ref="modal"
        :data-bs-backdrop="canDismiss ? 'true' : 'static'"
    >
        <div class="modal-dialog" :class="'modal-' + size">
            <div class="modal-content">
                <div class="modal-header text-bg-info bg-opacity-25" :class="'text-bg-' + themeColor">
                    <span class="sr-panel-header lead">{{ title }}</span>
                    <button v-if="canDismiss" type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <slot></slot>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
 import { Modal } from "bootstrap";
 import { nextTick, onBeforeUnmount, ref } from 'vue';

 const props = defineProps({
     title: String,
     // themeColor: primary, secondary, success, danger, warning, info
     themeColor: {
         type: String,
         default: 'info',
     },
     // size: lg, md, sm, default
     size: {
         type: String,
         default: 'lg'
     },
     canDismiss: {
         type: Boolean,
         default: true,
     },
 });

 const emit = defineEmits(['modalClosed']);

 let bootstrapModal = null;
 const modal = ref(null);
 const modalCreated = ref(false);

 const blurActiveElement = () => {
     // work around "Block aria-hidden" console warning when bootstrap modal is closed
     if (document.activeElement instanceof HTMLElement) {
         document.activeElement.blur();
     }
 };

 const closeModal = () => bootstrapModal.hide();

 const modalClosed = () => emit('modalClosed');

 const modalShown = () => {
     // focus on the first input field and select the text
     const f = modal.value.querySelector('.form-control');
     if (f && f.focus) {
         f.focus();
         if (f.select) {
             f.select();
         }
     }
 };

 const showModal = () => {
     if (! modalCreated.value) {
         modalCreated.value = true;
         nextTick(() => {
             bootstrapModal = new Modal(modal.value);
             modal.value.addEventListener('hidden.bs.modal', modalClosed);
             modal.value.addEventListener('hide.bs.modal', blurActiveElement);
             modal.value.addEventListener('shown.bs.modal', modalShown);
             bootstrapModal.show();
         });
         return;
     }
     bootstrapModal.show();
 };

 onBeforeUnmount(() => {
     if (bootstrapModal) {
         bootstrapModal.hide();
         modal.value.removeEventListener('hidden.bs.modal', modalClosed);
         modal.value.removeEventListener('hide.bs.modal', blurActiveElement);
         modal.value.removeEventListener('shown.bs.modal', modalShown);
         // cleanup modal after .3s hide transition has completed
         setTimeout(() => bootstrapModal.dispose(), 1000);
     }
 });

 defineExpose({ closeModal, showModal });
</script>
