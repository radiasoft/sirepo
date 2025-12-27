
import * as d3 from 'd3';

export function useAxis(svgGroup, dimension, orientation, { ticks = 6, tickFormat = null, tickSizeOuter = 6 } = {}) {

    const g = svgGroup.append("g").attr("class", `${dimension}-axis`).node();

    const update = (scale, transform) => {
        const axis = d3[orientation](scale)
            .ticks(ticks)
            .tickSizeOuter(tickSizeOuter)
            .tickFormat(tickFormat);
        d3.select(g)
          .attr("transform", transform)
          .call(axis);
    };
    return { ticks, update };
}
