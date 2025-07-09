
<template>
    <div class="progress">
        <div
            class="progress-bar"
            v-bind:class="{ 'progress-bar-striped progress-bar-animated': percentComplete === 0 }"
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            v-bind:aria-valuenow="percentComplete"
            v-bind:style="{ width: (percentComplete || 100) + '%' }"
        ></div>
    </div>
</template>

<script setup>
 const props = defineProps({
     percentComplete: Number,
 });
</script>
