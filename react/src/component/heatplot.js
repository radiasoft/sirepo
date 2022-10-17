// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { useRef, useLayoutEffect } from 'react';
import { useCanvas, useCanvasContext } from "./CanvasContext";
import { Canvas } from "./Canvas";
import { DynamicAxis } from "./axis";
import { constrainZoom, useRefSize, graphMetrics } from "./util";
import { Zoom } from '@visx/zoom';
import { Scale } from '@visx/visx';

function HeatplotImage({ xScaleDomain, yScaleDomain, xRange, yRange, width, height, zMatrix }) {
    const ctx = useCanvasContext();
    const cacheCanvas = document.createElement('canvas');
    cacheCanvas.width = zMatrix[0].length;
    cacheCanvas.height = zMatrix.length;
    const img = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);

    for (let yi = cacheCanvas.height - 1, p = -1; yi >= 0; --yi) {
        for (let xi = 0; xi < cacheCanvas.width; ++xi) {
            const v = zMatrix[yi][xi];
            //TODO(pjm): plot scale (linear, log, log10, etc.)
            // if (scaleFunction) {
            //     v = scaleFunction(v);
            // }
            //TODO(pjm): use colormap
            //const c = d3.rgb(colorScale(v));
            img.data[++p] = v > 0 ? 255 : 0;
            img.data[++p] = v > 0 ? 255 : 0;
            img.data[++p] = v > 0 ? 255 : 0;
            img.data[++p] = 255;
        }
    }
    cacheCanvas.getContext('2d').putImageData(img, 0, 0);
    // need to draw image before rendering
    useLayoutEffect(_ => {
        ctx.imageSmoothingEnabled = false;
        ctx.msImageSmoothingEnabled = false;
        ctx.drawImage(
            cacheCanvas,
            -(xScaleDomain[0] - xRange.min) / (xScaleDomain[1] - xScaleDomain[0]) * width,
            -(yRange.max - yScaleDomain[1]) / (yScaleDomain[1] - yScaleDomain[0]) * height,
            (xRange.max - xRange.min) / (xScaleDomain[1] - xScaleDomain[0]) * width,
            (yRange.max - yRange.min) / (yScaleDomain[1] - yScaleDomain[0]) * height,
        );
    });
    return null;
}

/**
 *
 * @param {{
 *  xRange,
 *  yRange,
 *  xLabel,
 *  yLabel,
 *  zMatrix
 * }} props
 * @returns
 */
export function Heatplot({xRange, yRange, xLabel, yLabel, zMatrix}) {
    const ref = useRef(null);
    const dim = useRefSize(ref, 1);
    if (! xRange) {
        return null;
    }
    const gm = graphMetrics(dim);

    function constrain(transformMatrix) {
        return constrainZoom(
            constrainZoom(transformMatrix, gm.graphWidth, 'X'),
            gm.graphHeight, 'Y',
        );
    }

    return (
        <div ref={ref}>
            <Zoom
                width={gm.graphWidth}
                height={gm.graphHeight}
                constrain={constrain}
            >
            {(zoom) => {

                function domain(range, translate, scale, sizeInPixels) {
                    const r = range.max - range.min;
                    const v0 = range.min - (translate * r) / (scale * sizeInPixels);
                    return [v0, v0 + r / scale];
                }
                function invert(range, v) {
                    return v.map(y => range.min + range.max - y).reverse();
                }
                const xScale = Scale.scaleLinear({
                    domain: domain(
                        xRange, zoom.transformMatrix.translateX, zoom.transformMatrix.scaleX, gm.graphWidth),
                    range: [0, gm.graphWidth],
                });
                const yScale = Scale.scaleLinear({
                    domain: invert(
                        yRange,
                        domain(
                            yRange, zoom.transformMatrix.translateY, zoom.transformMatrix.scaleY, gm.graphHeight)),
                    range: [gm.graphHeight, 0],
                });
                const cursor = zoom.transformMatrix.scaleX > 1 ? 'move' : 'zoom-in';
                return (
                    <>
                        <div style={{position: "relative"}}>
                            <Canvas
                                width={gm.graphWidth}
                                height={gm.graphHeight}
                                style={{
                                    position: "absolute",
                                    left: `${gm.graphX}px`,
                                    top: `${gm.graphY}px`,
                                }} >

                                <HeatplotImage
                                    xScaleDomain={xScale.domain()}
                                    yScaleDomain={yScale.domain()}
                                    xRange={xRange}
                                    yRange={yRange}
                                    width={gm.graphWidth}
                                    height={gm.graphHeight}
                                    zMatrix={zMatrix}
                                />
                            </Canvas>
                            <div>
                                <svg
                                    style={{
                                        position: "relative",
                                    }}
                                    width={dim.width}
                                    height={dim.height}
                                >
                                    <g transform={`translate(${gm.graphX}, ${gm.graphY})`}>
                                        <DynamicAxis
                                            orientation={"bottom"}
                                            scale={xScale}
                                            top={gm.graphHeight}
                                            label={xLabel}
                                            graphSize={gm.graphWidth}
                                        />
                                        <DynamicAxis
                                            orientation={"left"}
                                            scale={yScale}
                                            label={yLabel}
                                            graphSize={gm.graphHeight}
                                        />
                                        <svg width={gm.graphWidth} height={gm.graphHeight}>
                                            <rect
                                                ref={zoom.containerRef}
                                                width={gm.graphWidth}
                                                height={gm.graphHeight}
                                                style={{
                                                    touchAction: 'none',
                                                    fill: 'none',
                                                    cursor: cursor,
                                                    pointerEvents: 'all',
                                                }}
                                            ></rect>
                                        </svg>
                                    </g>
                                </svg>
                            </div>
                        </div>
                    </>
                )
            }}
            </Zoom>
        </div>
    )
}
