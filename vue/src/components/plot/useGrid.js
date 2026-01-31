
import * as d3 from 'd3';


export function useGrid(svgGroup, { ticksX = 6, ticksY = 6 } = {}) {
    const gx = svgGroup.append("g").attr("class", "sr-grid sr-grid-x").node();
    const gy = svgGroup.append("g").attr("class", "sr-grid sr-grid-y").node();

    const update = (xScale, yScale, innerWidth, innerHeight) => {
        d3.select(gx)
          .call(d3.axisLeft(yScale).ticks(ticksY).tickSize(-innerWidth).tickFormat(""));
        d3.select(gy)
          .attr("transform", `translate(0,${innerHeight})`)
          .call(d3.axisBottom(xScale).ticks(ticksX).tickSize(-innerHeight).tickFormat(""));
    };

    return { update };
}
