<template>
    <div class="d-flex align-items-center gap-3">
        <span v-if="! compact" class="text-muted small">{{ range }} of {{ total }}</span>
        <div class="btn-group btn-group-sm" v-bind:class="{ 'ms-auto': ! compact }">
            <button
                type="button"
                class="btn btn-outline-secondary"
                v-bind:disabled="page <= 1"
                v-on:click="emit('update:page', page - 1)"
            >
                Previous
            </button>
            <button
                type="button"
                class="btn btn-outline-secondary"
                v-bind:disabled="page >= pageCount"
                v-on:click="emit('update:page', page + 1)"
            >
                Next
            </button>
        </div>
    </div>
</template>

<script setup>
 defineProps({
     page: { type: Number, required: true },
     pageCount: { type: Number, required: true },
     // only the buttons
     compact: { type: Boolean, default: false },
     range: { type: String, default: '' },
     total: { type: Number, default: 0 },
 });
 const emit = defineEmits(['update:page']);
</script>
