// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { useRef, useLayoutEffect } from 'react';
import { useCanvas, useCanvasContext } from "./canvascontext";
import { Canvas } from "./canvas";
import { DynamicAxis } from "./axis";
import { constrainZoom, useGraphContentBounds } from "../utility/component";
import { Zoom } from '@visx/zoom';
import { Scale } from '@visx/visx';

function HeatplotImage({ xScaleDomain, yScaleDomain, xRange, yRange, width, height, zMatrix }) {
    const ctx = useCanvasContext();
    const cacheCanvas = document.createElement('canvas');
    cacheCanvas.width = zMatrix[0].length;
    cacheCanvas.height = zMatrix.length;
    const img = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);

    let zmin = Math.min(...zMatrix.map(row => Math.min(...row)));
    let zmax = Math.max(...zMatrix.map(row => Math.max(...row)));

    console.log(`zmin: ${zmin}, zmax: ${zmax}`);

    let scaleZScalar = (v) => (v - zmin) / zmax;

    for (let yi = cacheCanvas.height - 1, p = -1; yi >= 0; --yi) {
        for (let xi = 0; xi < cacheCanvas.width; ++xi) {
            const v = zMatrix[yi][xi];
            //TODO(pjm): plot scale (linear, log, log10, etc.)
            // if (scaleFunction) {
            //     v = scaleFunction(v);
            // }
            //TODO(pjm): use colormap
            //const c = d3.rgb(colorScale(v));
            /*img.data[++p] = v > 0 ? 255 : 0;
            img.data[++p] = v > 0 ? 255 : 0;
            img.data[++p] = v > 0 ? 255 : 0;
            img.data[++p] = 255;*/

            let c =  Math.ceil(scaleZScalar(v) * 255);

            img.data[++p] = c;
            img.data[++p] = c;
            img.data[++p] = c;
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
 *  title,
 *  xRange,
 *  yRange,
 *  xLabel,
 *  yLabel,
 *  zMatrix
 * }} props
 * @returns
 */
export function Heatplot({title, xRange, yRange, xLabel, yLabel, zMatrix}) {
    const ref = useRef(null);
    //TODO(pjm): use props.aspectRatio if present
    const gc = useGraphContentBounds(ref, 1);
    if (! xRange) {
        return null;
    }

    function constrain(transformMatrix) {
        return constrainZoom(
            constrainZoom(transformMatrix, gc.width, 'X'),
            gc.height, 'Y',
        );
    }

    return (
        <div ref={ref}>
            <Zoom
                width={gc.width}
                height={gc.height}
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
                        xRange, zoom.transformMatrix.translateX, zoom.transformMatrix.scaleX, gc.width),
                    range: [0, gc.width],
                });
                const yScale = Scale.scaleLinear({
                    domain: invert(
                        yRange,
                        domain(
                            yRange, zoom.transformMatrix.translateY, zoom.transformMatrix.scaleY, gc.height)),
                    range: [gc.height, 0],
                });
                const cursor = zoom.transformMatrix.scaleX > 1 ? 'move' : 'zoom-in';
                return (
                    <>
                        <div style={{position: "relative"}}>
                            <Canvas
                                width={gc.width}
                                height={gc.height}
                                style={{
                                    position: "absolute",
                                    left: `${gc.x}px`,
                                    top: `${gc.y}px`,
                                }} >

                                <HeatplotImage
                                    xScaleDomain={xScale.domain()}
                                    yScaleDomain={yScale.domain()}
                                    xRange={xRange}
                                    yRange={yRange}
                                    width={gc.width}
                                    height={gc.height}
                                    zMatrix={zMatrix}
                                />
                            </Canvas>
                            <div>
                                <svg
                                    style={{
                                        position: "relative",
                                    }}
                                    width={gc.contentWidth}
                                    height={gc.contentWidth}
                                >
                                    <g transform={`translate(${gc.x}, ${gc.y})`}>
                                        {/* TODO(pjm): margin top should be larger if title is present */}
                                        <text
                                            x={gc.width / 2}
                                            y={-gc.y / 2 + 5}
                                            style={{
                                                fontSize: '18px',
                                                fontWeight: 'bold',
                                                textAnchor: 'middle',
                                            }}
                                        >{title}</text>
                                        <DynamicAxis
                                            orientation={"bottom"}
                                            scale={xScale}
                                            top={gc.height}
                                            label={xLabel}
                                            graphSize={gc.width}
                                        />
                                        <DynamicAxis
                                            orientation={"left"}
                                            scale={yScale}
                                            label={yLabel}
                                            graphSize={gc.height}
                                        />
                                        <svg width={gc.width} height={gc.height}>
                                            <rect
                                                ref={zoom.containerRef}
                                                width={gc.width}
                                                height={gc.height}
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
