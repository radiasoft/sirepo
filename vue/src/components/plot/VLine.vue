<template>
    <div>
        <div ref="container" class="chart-container">
        </div>
    </div>
    <button v-on:click="makeData">Random</button>
</template>

<script setup>
 import * as d3 from 'd3';
 import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
 import { useAxis } from '@/components/plot/useAxis.js';
 import { useGrid } from '@/components/plot/useGrid.js';
 import { useLegend } from '@/components/plot/useLegend.js';
 import { useOverlay } from '@/components/plot/useOverlay.js';
 import { useZoomX } from '@/components/plot/useZoomX.js';
 import { util } from '@/services/util.js';

 const props = defineProps({
     viewName: String,
 });

 const margin = { top: 16, right: 20, bottom: 44, left: 44 };
 const data = ref(null);

 const container = ref(null);
 let svg, g, paths, xLabel;
 let xAxis, yAxis, zoomX, grid, legend, overlay;
 let resizeObserver;

 function init() {
     d3.select(container.value).select("svg").remove();
     svg = d3.select(container.value).append("svg");
     g = svg.append("g");
     overlay = useOverlay(g);
     //TODO(pjm): axes determin ticks based on size available
     xAxis = useAxis(g, 'x', 'bottom', { ticks: 6 });
     yAxis = useAxis(g, 'y', 'left', { ticks: 6 });
     grid = useGrid(overlay.clipped, { ticksX: xAxis.ticks, ticksY: yAxis.ticks });
     legend = useLegend(g, {
         padding: 8,
         rowH: 18,
         swatch: 12,
     });
     zoomX = useZoomX(overlay.overlay, {
         scaleExtent: [1, 50],
         onZoomX: render,
     });
     xLabel = g
       .append("text")
       .attr("class", "x-label")
       .attr("text-anchor", "middle");
 }

 function makeData() {
     overlay.clipped.selectAll("path").remove();
     //TODO(pjm): build paths based on input data, not a/b
     paths = {
         a: overlay.clipped.append("path").attr("class", "line line-a"),
         b: overlay.clipped.append("path").attr("class", "line line-b"),
     };
     data.value = d3.range(200).map((i) => {
         return {
             x: i + 20,
             a: 30 + 10 * Math.sin(i / 10) + (Math.random() - 0.5) * 7,
             b: 26 + 8 * Math.cos(i / 12) + (Math.random() - 0.5) * 7,
         };
     });
     render();
 }

 function getBounds() {
     const rect = container.value.getBoundingClientRect();
     return [Math.max(320, Math.floor(rect.width)), Math.max(220, Math.floor(rect.height))];
 }

 function render() {
     if (!container.value || !svg) {
         return;
     }
     const [width, height] = getBounds();
     svg.attr("width", width).attr("height", height);

     const innerWidth = Math.max(0, width - margin.left - margin.right);
     const innerHeight = Math.max(0, height - margin.top - margin.bottom);
     zoomX.update(innerWidth, innerHeight);
     const domain = d3.extent(data.value, (d) => d.x);
     const x = zoomX.rescale(d3
         .scaleLinear()
         .domain(domain)
         .range([0, innerWidth])
     );
     const y = d3.scaleLinear().domain([
         d3.min(data.value, (d) => Math.min(d.a, d.b)),
         d3.max(data.value, (d) => Math.max(d.a, d.b)),
     ]).nice().range([innerHeight, 0]);
     xAxis.update(x, `translate(0,${innerHeight})`);
     yAxis.update(y);
     grid.update(x, y, innerWidth, innerHeight);
     g.attr("transform", `translate(${margin.left},${margin.top})`);
     overlay.update(innerWidth, innerHeight, ! util.deepEquals(x.domain(), domain));
     legend.update({
         innerWidth,
         items: [
             { label: "Height [cm]", className: "legend-a" },
             { label: "Weight [lbs]", className: "legend-b" },
         ],
     });
     xLabel
       .attr("x", innerWidth / 2)
       .attr("y", innerHeight + margin.bottom - 6)
       .text("Age [years]");
     renderLines(x, y);
 }

 function renderLines(x, y) {
     const line = (key) => d3
         .line()
         .x((d) => x(d.x))
         .y((d) => y(d[key]));
     paths.a.datum(data.value).attr("d", line("a")).attr("vector-effect", "non-scaling-stroke");
     paths.b.datum(data.value).attr("d", line("b")).attr("vector-effect", "non-scaling-stroke");
 }

 onMounted(() => {
     init();
     makeData()
     resizeObserver = new ResizeObserver(() => render());
     resizeObserver.observe(container.value);
 });

 onBeforeUnmount(() => {
     if (resizeObserver && container.value) {
         resizeObserver.unobserve(container.value);
     }
     resizeObserver = null;
     zoomX.detach();
 });

 // Re-render when data changes
 watch(data, () => render(), { deep: true });
</script>

//TODO(pjm): move style to global css and use sr prefix
<style scoped>
 .chart-container {
     width: 100%;
     height: 420px;
     background: #fff;
     box-sizing: border-box;
 }

 /* D3 styling */
 :deep(.line) {
     fill: none;
     stroke-width: 2;
 }

 :deep(.line-a) {
     stroke: #1f77b4;
 }

 :deep(.line-b) {
     stroke: #ff7f0e;
 }

 :deep(.grid line) {
     stroke: #e6e6e6;
 }

 :deep(.grid path) {
     stroke: none;
 }

 :deep(.x-axis path),
 :deep(.y-axis path),
 :deep(.x-axis line),
 :deep(.y-axis line) {
     stroke: #bbb;
 }

 /* legend */
 :deep(.legend-bg) {
     fill: rgba(255, 255, 255, 0.85);
     stroke: #ddd;
 }

 :deep(.legend text) {
     font-size: 12px;
     fill: #333;
     dominant-baseline: middle;
 }

 :deep(.legend-row line) {
     stroke-width: 3;
     stroke-linecap: round;
 }

 :deep(.legend-row.legend-a line) {
     stroke: #1f77b4;
 }

 :deep(.legend-row.legend-b line) {
     stroke: #ff7f0e;
 }
</style>
