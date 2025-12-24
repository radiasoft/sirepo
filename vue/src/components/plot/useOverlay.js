
import * as d3 from 'd3';
import { util } from '@/services/util.js';

export function useOverlay(svgGroup) {
    const clipId = util.uniqueId();
    svgGroup.append("defs").append("clipPath").attr("id", clipId).append("rect");
    const clipped = svgGroup.append("g").attr("clip-path", `url(#${clipId})`);
    const overlay = svgGroup
        .append("rect")
        .attr("class", "overlay")
        .attr("fill", "transparent");

    const update = (innerWidth, innerHeight, isZoomed) => {
        svgGroup.select(`#${clipId} rect`).attr("width", innerWidth).attr("height", innerHeight);
        overlay.attr("width", innerWidth).attr("height", innerHeight);
        overlay.style("cursor", isZoomed ? "ew-resize" : "zoom-in");
    };

    return { clipped, overlay, update };
}
