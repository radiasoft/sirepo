
import * as d3 from 'd3';

export function useLegend(svgGroup, {
    padding = 8,
    rowH = 18,
    swatch = 12,
    offset = { x: 8, y: 8 },
} = {}) {

    const legendEl = svgGroup.append("g").attr("class", "legend").node();

    const update = ({ items = [], innerWidth = 0 } = {}) => {
        const g = d3.select(legendEl);
        g.selectAll("*").remove();

        // rows
        const rows = g
            .selectAll("g.legend-row")
            .data(items)
            .enter()
            .append("g")
            .attr("class", (d) => `legend-row ${d.className}`)
            .attr("transform", (_, i) => `translate(${padding},${padding + i * rowH})`);

        rows
            .append("line")
            .attr("x1", 0)
            .attr("y1", 8)
            .attr("x2", swatch)
            .attr("y2", 8);

        rows
            .append("text")
            .attr("x", swatch + 8)
            .attr("y", 10)
            .text((d) => d.label);

        // background
        const bg = g
            .insert("rect", ":first-child")
            .attr("class", "legend-bg")
            .attr("rx", 10)
            .attr("ry", 10);

        // measure
        const bbox = legendEl.getBBox();

        bg
            .attr("x", bbox.x - padding)
            .attr("y", bbox.y - padding)
            .attr("width", bbox.width + padding * 2)
            .attr("height", bbox.height + padding * 2);

        // position (top-right inside plot)
        const legendW = bbox.width + padding * 2;
        const lx = Math.max(0, innerWidth - legendW - offset.x);
        const ly = offset.y;

        g.attr("transform", `translate(${lx},${ly})`);
    };

    return { update };
}
