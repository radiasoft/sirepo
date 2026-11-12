<template>
    <div class="container-xl sr-fixed-lg">
        <VCortexCard title="Admin Batch Runs">
            <p class="text-muted small">
                Runs the selected simulations one at a time as the batch user.
                Results replace the material's current results for its owner.
            </p>
            <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
                <span v-for="r in REPORTS" v-bind:key="r.name" class="form-check">
                    <input
                        class="form-check-input"
                        type="checkbox"
                        v-bind:id="'batch-report-' + r.name"
                        v-bind:value="r.name"
                        v-bind:disabled="batch.is_running"
                        v-model="selectedReports"
                    />
                    <label class="form-check-label" v-bind:for="'batch-report-' + r.name">{{ r.label }}</label>
                </span>
                <input
                    type="text"
                    class="form-control form-control-sm w-auto ms-auto"
                    placeholder="Filter by name or owner"
                    v-model="filter"
                />
                <button
                    type="button"
                    class="btn btn-primary btn-sm"
                    v-bind:disabled="! canRun()"
                    v-on:click="run"
                >
                    Run batch ({{ selectedIds.length }} selected)
                </button>
                <button
                    v-if="batch.is_running"
                    type="button"
                    class="btn btn-outline-danger btn-sm"
                    v-on:click="cancel"
                >
                    Cancel
                </button>
            </div>
            <div v-if="error" class="alert alert-danger">{{ error }}</div>
            <div v-if="batch.jobs.length" class="mb-3">
                {{ doneCount() }} of {{ batch.jobs.length }} runs finished<span v-if="batch.is_running">...</span>
            </div>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>
                            <input
                                class="form-check-input"
                                type="checkbox"
                                v-bind:disabled="batch.is_running"
                                v-bind:checked="allVisibleSelected()"
                                v-on:change="toggleAll($event.target.checked)"
                            />
                        </th>
                        <th>Material Name</th>
                        <th>Owner</th>
                        <th>{{ MATERIAL_TYPE_HEADING }}</th>
                        <th>Last Completed</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="m in pageItems" v-bind:key="m.material_id">
                        <td>
                            <input
                                class="form-check-input"
                                type="checkbox"
                                v-bind:disabled="batch.is_running"
                                v-bind:value="m.material_id"
                                v-model="selectedIds"
                            />
                        </td>
                        <td>{{ m.material_name }}</td>
                        <td>{{ m.uid }}</td>
                        <td>{{ materialTypeName(m.is_plasma_facing) }}</td>
                        <td>{{ m.completed ? util.formatDate(m.completed) : '' }}</td>
                        <td>
                            <div v-for="j in jobsFor(m)" v-bind:key="j.report">
                                <span class="text-muted">{{ labels[j.report] }}:</span>
                                <span v-bind:class="stateClass(j)">{{ j.state }}</span>
                                <span v-if="j.error" class="text-danger small">&nbsp;{{ j.error }}</span>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
            <VPager
                v-model:page="page"
                v-bind:pageCount="pageCount"
                v-bind:range="pageRange"
                v-bind:total="visible.length"
            />
        </VCortexCard>
    </div>
</template>

<script setup>
 import VCortexCard from '@/apps/cortex/VCortexCard.vue';
 import VPager from '@/apps/cortex/VPager.vue';
 import { MATERIAL_TYPE_HEADING, materialTypeName } from '@/apps/cortex/materialType.js';
 import { REPORTS } from '@/apps/cortex/reports.js';
 import { db } from '@/apps/cortex/db.js';
 import { onMounted, onUnmounted, reactive, ref } from 'vue';
 import { usePagedList } from '@/apps/cortex/usePagedList.js';
 import { util } from '@/services/util.js';

 // POSIT: the job states are those of sirepo.sim_api.cortex.batch
 const JOB_DONE = ['completed', 'error', 'canceled'];
 const POLL_MS = 5000;
 const labels = Object.fromEntries(REPORTS.map(r => [r.name, r.label]));
 const batch = reactive({ is_running: false, jobs: [] });
 const error = ref('');
 const materials = ref([]);
 const selectedIds = ref([]);
 const selectedReports = ref(REPORTS.map(r => r.name));
 const { filter, page, pageCount, pageItems, pageRange, visible } = usePagedList(
     materials,
     (m, f) => m.material_name.toLowerCase().includes(f) || m.uid.toLowerCase().includes(f),
 );
 let pollTimer = null;

 const allVisibleSelected = () => {
     const v = visible.value;
     return v.length > 0 && v.every(m => selectedIds.value.includes(m.material_id));
 };

 const cancel = async () => {
     await _update(db.batchCancel());
 };

 const canRun = () => ! batch.is_running && selectedIds.value.length > 0 && selectedReports.value.length > 0;

 const doneCount = () => batch.jobs.filter(j => JOB_DONE.includes(j.state)).length;

 const jobsFor = (material) => batch.jobs.filter(j => j.material_id === material.material_id);

 const run = async () => {
     error.value = '';
     await _update(db.batchRun(selectedIds.value, selectedReports.value));
 };

 const stateClass = (job) => ({
     'text-danger': job.state === 'error',
     'text-success': job.state === 'completed',
     'fw-bold': job.state === 'running',
 });

 const toggleAll = (checked) => {
     const v = visible.value.map(m => m.material_id);
     selectedIds.value = checked
         ? [...new Set([...selectedIds.value, ...v])]
         : selectedIds.value.filter(id => ! v.includes(id));
 };

 const _poll = () => {
     if (pollTimer) {
         return;
     }
     pollTimer = setTimeout(async () => {
         pollTimer = null;
         await _update(db.batchStatus());
     }, POLL_MS);
 };

 const _update = async (request) => {
     const r = await request;
     if (r.error) {
         error.value = r.error;
         return;
     }
     batch.is_running = r.is_running;
     batch.jobs = r.jobs;
     if (r.is_running) {
         _poll();
     }
     else {
         // results may have changed
         materials.value = await db.batchListMaterials();
     }
 };

 onMounted(async () => {
     materials.value = await db.batchListMaterials();
     await _update(db.batchStatus());
 });

 onUnmounted(() => {
     clearTimeout(pollTimer);
 });

</script>
