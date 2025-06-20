<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th
                    v-for="col in cols"
                    :key="col.name"
                >
                    <a href @click.prevent="sortCol(col)">
                        {{ col.heading }}
                        <div class="sr-sort-icon">
                            {{ sortIcon(col) }}
                        </div>
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr
                v-for="mat in state.materials"
                :key="mat.material_id"
            >
                <td
                    v-for="col in cols"
                    :key="col.name"
                >
                    {{ formatValue(mat, col) }}
                </td>
            </tr>
        </tbody>
    </table>
</template>

<script setup>
 import { appState, MODEL_SAVED_EVENT } from '@/services/appstate.js';
 import { onMounted, onUnmounted, reactive } from 'vue';
 import { pubSub } from '@/services/pubsub.js';
 import { db } from '@/apps/cortex/db.js';

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
         name: 'name',
         heading: 'Material Name',
     },
     {
         name: 'lastModified',
         heading: 'Date Uploaded',
         format: (v) => _dateFormat.format(v),
     },
 ];
 const state = reactive({
     sort: ['name', true],
     materials: [],
 });

 const formatValue = (material, col) => {
     const v = material[col.name];
     return col.format ? col.format(v) : v;
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
     pubSub.subscribe(MODEL_SAVED_EVENT, _loadMaterials);
     appState.clearModels();
     await _loadMaterials();
 });

 onUnmounted(() => {
     pubSub.unsubscribe(MODEL_SAVED_EVENT, _loadMaterials);
 });
</script>

<style scoped>
 .sr-sort-icon {
     display: inline-block;
     min-width: 2em;
 }
</style>
