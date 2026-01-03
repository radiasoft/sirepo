
import * as d3 from 'd3';

export function useLegend(svgGroup) {
    const legendEl = svgGroup.append("g").attr("class", "sr-legend").node();
    const rowHeight = 18;
    const padding = 8;
    const swatch = 12;

    const update = ({
        items = [],
        innerWidth = 0,
        position = "right",
    } = {}) => {
        const g = d3.select(legendEl);
        g.selectAll("*").remove();
        const rows = g
            .selectAll("g.sr-legend-row")
            .data(items)
            .enter()
            .append("g")
            .attr("class", "sr-legend-row")
            .attr("transform", (_, i) => `translate(${padding},${padding + i * rowHeight})`);
        rows
            .append("line")
            .attr("x1", 0)
            .attr("y1", 8)
            .attr("x2", swatch)
            .attr("y2", 8)
            .attr("stroke", (d) => d.color);
        rows
            .append("text")
            .attr("x", swatch + 8)
            .attr("y", 10)
            .text((d) => d.label);
        const bg = g
            .insert("rect", ":first-child")
            .attr("class", "sr-legend-bg")
            .attr("rx", 10)
            .attr("ry", 10);
        const bbox = legendEl.getBBox();
        bg
            .attr("x", bbox.x - padding)
            .attr("y", bbox.y - padding)
            .attr("width", bbox.width + padding * 2)
            .attr("height", bbox.height + padding * 2);
        const legendW = bbox.width + padding * 2;
        const lx = position === "right"
                 ? Math.max(0, innerWidth - legendW - padding)
                 : padding;
        const ly = padding;
        g.attr("transform", `translate(${lx},${ly})`);
    };

    return { update };
}
