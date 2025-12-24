
import * as d3 from 'd3';

export function useAxis(svgGroup, dimension, orientation, { ticks = 6, tickFormat = null, tickSizeOuter = 6 } = {}) {

    const g = svgGroup.append("g").attr("class", `${dimension}-axis`).node();

    const update = (scale, transform) => {
        const axis = d3[orientation === "bottom" ? "axisBottom" : "axisLeft"](scale)
            .ticks(ticks).tickSizeOuter(tickSizeOuter);
        if (tickFormat) {
            axis.tickFormat(tickFormat);
        }
        const sel = d3.select(g);
        if (transform) {
            sel.attr("transform", transform);
        }
        sel.call(axis);
    };
    return { ticks, update };
}
