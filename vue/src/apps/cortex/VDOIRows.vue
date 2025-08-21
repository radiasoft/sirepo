<template>
    <tbody v-if="doi">
        <tr v-if="title">
            <td><div class="lead">{{ title }}</div></td>
        </tr>
        <tr>
            <td class="col-form-label">{{ doi.type }}</td>
            <td><a v-bind:href="doi.url" target="_blank">{{ doi.linkText }}</a></td>
        </tr>
        <template v-for="r in Object.keys(doi.rows)">
            <tr v-if="doi.rows[r]">
                <td class="col-form-label">{{ r }}</td>
                <td>{{ doi.rows[r] }}</td>
            </tr>
        </template>
    </tbody>
</template>

<script setup>
 defineProps({
     doi: Object,
     title: String,
 });
</script>
