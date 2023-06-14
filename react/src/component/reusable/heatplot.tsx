import React, { useRef, useLayoutEffect, useState, useContext } from 'react';
import { Canvas, CCanvas } from "./canvas";
import { ColorBar } from './colorbar';
import { DynamicAxis } from "./axis";
import { Range1d } from '../../types';
import { Scale } from '@visx/visx';
import { Zoom } from '@visx/zoom';
import { constrainZoom, createColorScale, useGraphContentBounds } from "../../utility/component";
import { rgb } from 'd3-color';
import { useWindowSize } from '../../hook/breakpoint';

export type HeatPlotConfig = {
    title: string,
    zMatrix: number[][],
    xLabel: string,
    yLabel: string,
    xRange: Range1d,
    yRange: Range1d,
    zRange: Range1d
}

export type HeatPlotConfigExtras = {
    colorMap: string
}

function HeatplotImage({ xScaleDomain, yScaleDomain, xRange, yRange, width, height, zMatrix, colorScale, colorMap }) {
    const ctx = useContext(CCanvas).getCanvasContext();
    const [cache, setCache] = useState<{canvas: HTMLCanvasElement, zMatrix: number[][], colorMap: string}>(null);

    if (! cache || cache.zMatrix !== zMatrix || cache.colorMap !== colorMap) {
        const cacheCanvas = document.createElement('canvas');
        cacheCanvas.width = zMatrix[0].length;
        cacheCanvas.height = zMatrix.length;
        const img = ctx.getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);

        for (let yi = cacheCanvas.height - 1, p = -1; yi >= 0; --yi) {
            for (let xi = 0; xi < cacheCanvas.width; ++xi) {
                const v = zMatrix[yi][xi];
                //TODO(pjm): plot scale (linear, log, log10, etc.)
                let c = rgb(colorScale(v));
                img.data[++p] = c.r;
                img.data[++p] = c.g;
                img.data[++p] = c.b;
                img.data[++p] = 255;
            }
        }
        cacheCanvas.getContext('2d').putImageData(img, 0, 0);
        setCache({
            canvas: cacheCanvas,
            zMatrix,
            colorMap,
        });
    }
    // need to draw image before rendering
    useLayoutEffect(() => {
        ctx.imageSmoothingEnabled = false;
        //ctx.msImageSmoothingEnabled = false; // TODO: evaluate, this claims to be missing on type
        ctx.drawImage(
            cache.canvas,
            -(xScaleDomain[0] - xRange.min) / (xScaleDomain[1] - xScaleDomain[0]) * width,
            -(yRange.max - yScaleDomain[1]) / (yScaleDomain[1] - yScaleDomain[0]) * height,
            (xRange.max - xRange.min) / (xScaleDomain[1] - xScaleDomain[0]) * width,
            (yRange.max - yRange.min) / (yScaleDomain[1] - yScaleDomain[0]) * height,
        );
    });
    return null;
}

export function Heatplot({title, xRange, yRange, zRange, xLabel, yLabel, zMatrix, colorMap }: HeatPlotConfig & HeatPlotConfigExtras) {
    const ref = useRef(null);
    useWindowSize(); // needs to resize when window does
    colorMap = colorMap || 'viridis';
    const showColorBar = colorMap !== 'contrast';
    //TODO(pjm): use props.aspectRatio if present
    const gc = useGraphContentBounds(ref, 1, showColorBar ? 80 : 0);
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
            <Zoom<SVGRectElement>
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
                if (zRange.min === zRange.max && zRange.min === 0) {
                    zRange.max = 1000;
                }
                const colorScale = createColorScale(zRange, colorMap);
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
                                    colorScale={colorScale}
                                    colorMap={colorMap}
                                />
                            </Canvas>
                            <div>
                                <svg
                                    style={{
                                        position: "relative",
                                    }}
                                    width={gc.contentWidth}
                                    height={gc.contentHeight}
                                >
                                    { showColorBar &&
                                        <g transform={`translate(${gc.x + gc.width + 15}, ${gc.y})`}>
                                            <ColorBar
                                                range={zRange}
                                                height={gc.height}
                                                colorMap={colorMap}
                                            />
                                        </g>
                                    }
                                    <g transform={`translate(${gc.x}, ${gc.y})`}>
                                        {/* TODO(pjm): margin top should be larger if title is present */}
                                        <text
                                            x={gc.width / 2}
                                            y={-gc.y / 2}
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
                                            top={0}
                                        />
                                        <svg width={gc.width} height={gc.height}>
                                            <rect
                                                ref={zoom.containerRef}
                                                width={gc.width}
                                                height={gc.height}
                                                style={{
                                                    touchAction: 'none',
                                                    fill: 'none',
                                                    cursor: zoom.transformMatrix.scaleX > 1
                                                        ? 'move'
                                                        : 'zoom-in',
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
