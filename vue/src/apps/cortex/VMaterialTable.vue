<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th
                    v-for="col in cols"
                    v-bind:key="col.name"
                >
                    <a href v-on:click.prevent="sortCol(col)">
                        {{ col.heading }}
                        <div class="sr-sort-icon">
                            {{ sortIcon(col) }}
                        </div>
                    </a>
                </th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr
                v-for="mat in state.materials"
                v-bind:key="mat.material_id"
            >
                <td
                    v-for="col in cols"
                    v-bind:key="col.name"
                >
                    {{ formatValue(mat, col) }}
                </td>
                <td class="sr-button-bar-td">
                    <div class="sr-button-bar-parent">
                        <div class="sr-button-bar">
                            <button
                                type="button"
                                v-on:click="removeMaterial(mat)"
                                class="btn btn-danger btn-sm"
                            >
                                <span class="bi bi-trash3"></span>
                            </button>
                        </div>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</template>

<script setup>
 import { onMounted, onUnmounted, reactive } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { db, DB_UPDATED } from '@/apps/cortex/db.js';

 const emit = defineEmits(['materialCount']);

 const _dateFormat = Intl.DateTimeFormat('en-US', {
     year: 'numeric',
     month: 'short',
     day: 'numeric',
     hour: 'numeric',
     minute: 'numeric',
 });
 const cols = [
     {
         name: 'material_name',
         heading: 'Material Name',
     },
     {
         name: 'created',
         heading: 'Date Uploaded',
         format: (v) => _dateFormat.format(v),
     },
 ];
 const state = reactive({
     sort: ['material_name', true],
     materials: [],
 });

 const formatValue = (material, col) => {
     const v = material[col.name];
     return col.format ? col.format(v) : v;
 };

 const removeMaterial = (material) => {
     //TODO(pjm): call db
 };

 const sortCol = (col) => {
     if (state.sort[0] === col.name) {
         state.sort[1] = ! state.sort[1];
     }
     else {
         state.sort = [col.name, true];
     }
     _sortMaterials();
 };

 const sortIcon = (col) => {
     if (state.sort[0] === col.name) {
         return state.sort[1] ? '▲' : '▼';
     }
     return '';
 }

 const _loadMaterials = async () => {
     emit('materialCount', undefined);
     state.materials = await db.loadMaterials();
     emit('materialCount', state.materials.length);
     _sortMaterials();
 };

 const _sortMaterials = () => {
     state.materials.sort(
         (a, b) => {
             let v;
             const col = state.sort[0];
             if (typeof a[col] === 'string') {
                 v = a[col].localeCompare(b[col]);
             }
             else if (a[col] < b[col]) {
                 v = -1;
             }
             else if (a[col] > b[col]) {
                 v = 1;
             }
             return state.sort[1] ? v : -v;;
         },
     );
 };

 onMounted(async () => {
     pubSub.subscribe(DB_UPDATED, _loadMaterials);
     await _loadMaterials();
 });

 onUnmounted(() => {
     pubSub.unsubscribe(DB_UPDATED, _loadMaterials);
 });
</script>

<style scoped>
 .sr-sort-icon {
     display: inline-block;
     min-width: 2em;
 }
</style>
