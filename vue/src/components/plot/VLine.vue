<template>
    <div ref="container" class="sr-chart-container"></div>
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
     data: Function,
 });

 const margin = { top: 26, right: 20, bottom: 44, left: 60 };
 const container = ref(null);
 let svg, g, paths, xLabel, yLabel, title;
 let xAxis, yAxis, zoomX, grid, legend, overlay;
 let resizeObserver;

 function init() {
     d3.select(container.value).select("svg").remove();
     svg = d3.select(container.value).append("svg").attr("class", "sr-plot");
     g = svg.append("g");
     overlay = useOverlay(g);
     //TODO(pjm): axes determin ticks based on size available
     xAxis = useAxis(g, 'x', 'axisBottom', { ticks: 6 });
     yAxis = useAxis(g, 'y', 'axisLeft', { ticks: 6 });
     grid = useGrid(overlay.clipped, { ticksX: xAxis.ticks, ticksY: yAxis.ticks });
     legend = useLegend(g);
     zoomX = useZoomX(overlay.overlay, {
         scaleExtent: [1, 50],
         onZoomX: render,
     });
     xLabel = g
       .append("text")
       .attr("text-anchor", "middle");
     yLabel = g
       .append("text")
       .attr("text-anchor", "middle")
       .attr("transform", "rotate(270)");
     paths = props.data().plots.map((p) => overlay.clipped.append("path").attr("class", "sr-line"));
     if (props.data().title) {
         title = svg.append("text")
                    .attr("class", "sr-main-title")
                    .text(props.data().title);
     }
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
     //TODO(pjm): only calculate domain and scale when data is first loaded
     zoomX.update(innerWidth, innerHeight);
     const domain = d3.extent(props.data().x_points);
     const x = zoomX.rescale(scale(
         'x',
         props.data().type === 'loglog',
         domain,
         [0, innerWidth],
     ));
     const y = scale(
         'y',
         ['loglog', 'semilog'].includes(props.data().type),
         props.data().y_range,
         [innerHeight, 0],
     );
     xAxis.update(x, `translate(0,${innerHeight})`);
     yAxis.update(y);
     grid.update(x, y, innerWidth, innerHeight);
     g.attr("transform", `translate(${margin.left},${margin.top})`);
     overlay.update(innerWidth, innerHeight, ! util.deepEquals(x.domain(), domain));
     legend.update({
         innerWidth,
         items: props.data().plots.map((p) => {
             return {
                 label: p.label,
                 color: p.color,
             };
         }),
         position: props.data().alignLegend || "left",
         show: props.data().plots.length > 1,
     });
     xLabel
       .attr("x", innerWidth / 2)
       .attr("y", innerHeight + margin.bottom - 6)
       .text(props.data().x_label);
     yLabel
         .attr("x", - innerHeight / 2)
         .attr("y", - margin.left + 12)
         .text(props.data().y_label);
     if (title) {
         title.attr("x", (width + margin.left) / 2).attr("y", margin.top / 2);
     }
     renderLines(x, y);
 }

 function renderLines(x, y) {
     const line = (plot) => d3
         .line()
         .x((d) => x(d))
         .y((d, idx) => y(plot.points[idx]));
     for (const [idx, p] of Object.entries(props.data().plots)) {
         paths[idx]
             .datum(props.data().x_points)
             .attr("d", line(p))
             .attr("vector-effect", "non-scaling-stroke")
             .attr("stroke", p.color);
     }
 }

 function scale(dimension, isLog, domain, range) {
     const s = d3[isLog ? 'scaleLog' : 'scaleLinear'](domain, range);
     if (dimension == 'y') {
        s.nice();
     }
     if (isLog) {
         s.base(10);
     }
     return s;
 }

 onMounted(() => {
     if (props.data) {
         init();
         render();
     }
     resizeObserver = new ResizeObserver(() => render());
     resizeObserver.observe(container.value);
 });

 onBeforeUnmount(() => {
     if (resizeObserver) {
         resizeObserver.disconnect();
     }
     if (zoomX) {
         zoomX.detach();
     }
 });

 watch(() => props.data, () => {
     if (props.data) {
         if (! svg) {
             init();
         }
         render();
     }
 });
</script>
