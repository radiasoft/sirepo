// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import React, { useRef } from 'react';
import { Zoom } from '@visx/zoom';
import { ClipPath, Scale, Shape } from '@visx/visx';
import { LegendOrdinal } from "@visx/legend";
import { DynamicAxis } from "./axis";
import { constrainZoom, useGraphContentBounds } from "../../utility/component";
import { Point2d, Range1d } from '../../types';

export type Graph2dPlot = {
    color: string,
    label: string,
    points: Point2d[]
}

export type Graph2dConfig = {
    title?: string,
    plots: Graph2dPlot[],
    xLabel: string,
    yLabel: string,
    xRange: Range1d,
    yRange: Range1d
}

export function Graph2d(props: Graph2dConfig) {
    let {plots, xRange, yRange, xLabel, yLabel } = props;
    const ref = useRef(null);
    //TODO(pjm): use props.aspectRatio if present
    const gc = useGraphContentBounds(ref, 9 / 16.0);

    function constrain(transformMatrix) {
        // no Y zoom
        transformMatrix.scaleY = 1;
        // TODO(garsuga): something is happening here. maybe this scale restriction needs to be more intelligent
        transformMatrix.scaleX = Math.min(250, transformMatrix.scaleX);
        transformMatrix.translateY = 0;
        return constrainZoom(transformMatrix, gc.width, 'X');
    }

    function visibleYDomain(xDomain, plots) {
        let start = 0;
        const p0 = plots[0].points;
        for (let i = 0; i < p0.length; i++) {
            if (p0[i].x > xDomain[0]) {
                start = Math.max(start, i - 1);
                break;
            }
        }
        let end = p0.length - 1;
        for (let i = end; i >= 0; i--) {
            if (p0[i].x < xDomain[1]) {
                end = Math.min(end, i + 1);
                break;
            }
        }

        let range = [p0[start].y, p0[start].y];
        for (const p of plots) {
            for (let i = start; i <= end; i++) {
                const y = p.points[i].y;
                if (y < range[0]) {
                    range[0] = y;
                }
                else if (y > range[1]) {
                    range[1] = y;
                }
            }
        }
        return range;
    }

    return (
        <div ref={ref}>
            <Zoom<SVGRectElement>
                width={gc.width}
                height={gc.height}
                constrain={constrain}
            >
            {(zoom) => {
                let xScale = Scale.scaleLinear({
                    domain: [xRange.min, xRange.max],
                    range: [0, gc.width],
                });
                xScale.domain([
                    xScale.invert((xScale(xRange.min) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                    xScale.invert((xScale(xRange.max) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                ]);

                let yScale = Scale.scaleLinear({
                    domain: zoom.transformMatrix.scaleX == 1
                        ? [yRange.min, yRange.max]
                        : visibleYDomain(xScale.domain(), plots),
                    range: [gc.height, 0],
                    nice: true
                });

                let legendScale = Scale.scaleOrdinal({
                    domain: plots.map(plot => plot.label),
                    range: plots.map(plot => plot.color)
                })

                let toPath = (plot, index) => {
                    return (
                        <Shape.LinePath key={index} data={plot.points} x={(d: Point2d) => xScale(d.x)} y={(d: Point2d) => yScale(d.y)} stroke={plot.color} strokeWidth={2}/>
                    )
                }

                let paths = plots.map((plot, i) => toPath(plot, i));
                let cursor = zoom.transformMatrix.scaleX > 1 ? 'ew-resize' : 'zoom-in';
                return (
                    <>
                        <svg
                            style={{'userSelect': 'none'}}
                            viewBox={`${0} ${0} ${gc.contentWidth} ${gc.contentHeight}`}
                        >
                            <ClipPath.RectClipPath id={"graph-clip"} width={gc.width} height={gc.height}/>
                            <g transform={`translate(${gc.x} ${gc.y})`} width={gc.width} height={gc.height}>
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
                                <g clipPath="url(#graph-clip)">
                                    {paths}
                                </g>
                                {/* zoom container must be contained within svg so visx localPoint() works correctly */}
                                <svg><rect
                                    ref={zoom.containerRef}
                                    width={gc.width}
                                    height={gc.height}
                                    style={{
                                        touchAction: 'none',
                                        fill: 'none',
                                        cursor: cursor,
                                        pointerEvents: 'all',
                                    }}
                                ></rect></svg>
                            </g>
                        </svg>
                        <LegendOrdinal scale={legendScale} direction="column"/>
                    </>
                )
            }}
            </Zoom>
        </div>
    )
}
