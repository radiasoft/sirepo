
import * as d3 from 'd3';


export function useGrid(svgGroup, { ticksX = 6, ticksY = 6 } = {}) {
    const gx = svgGroup.append("g").attr("class", "grid grid-x").node();
    const gy = svgGroup.append("g").attr("class", "grid grid-y").node();

    const update = (xScale, yScale, innerWidth, innerHeight) => {
        d3.select(gx)
          .style("display", null)
          .attr("transform", null)
          .call(d3.axisLeft(yScale).ticks(ticksY).tickSize(-innerWidth).tickFormat(""))
          .call((g) => g.select(".domain").remove());
        d3.select(gy)
          .style("display", null)
          .attr("transform", `translate(0,${innerHeight})`)
          .call(d3.axisBottom(xScale).ticks(ticksX).tickSize(-innerHeight).tickFormat(""))
          .call((g) => g.select(".domain").remove());
    };

    return { update };
}
