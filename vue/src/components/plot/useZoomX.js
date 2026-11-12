
import * as d3 from 'd3';

export function useZoomX(svg, {
    scaleExtent = [1, 50],
    onZoomX,
} = {}) {
    let zoom;
    let currentTransform = d3.zoomIdentity;

    const attach = () => {
        const z = d3
            .zoom()
            .scaleExtent(scaleExtent)
            .on("zoom", (event) => {
                const t = event.transform;
                currentTransform = d3.zoomIdentity.translate(t.x, 0).scale(t.k, 1);
                onZoomX();
            });
        const sel = d3.select(svg.node());
        sel.call(z).on("dblclick.zoom", null);
        sel.on("dblclick", resetZoom);
        zoom = z;
    };

    const detach = () => {
        d3.select(svg)
          .on("zoom", null)
          .on("dblclick", null);
    };

    const rescale = (base) => {
        return currentTransform.rescaleX(base);
    };

    const resetZoom = () => {
        currentTransform = d3.zoomIdentity;
        d3.select(svg.node()).call(zoom.transform, d3.zoomIdentity);
    };

    const update = (width, height) => {
        zoom
            .translateExtent([
                [0, 0],
                [width, height],
            ])
            .extent([
                [0, 0],
                [width, height],
            ]);
    };

    attach();

    return { detach, rescale, update };
}
