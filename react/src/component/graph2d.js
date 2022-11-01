// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { useRef } from 'react';
import { Zoom } from '@visx/zoom';
import { ClipPath, Scale, Shape } from '@visx/visx';
import { LegendOrdinal } from "@visx/legend";
import { DynamicAxis } from "./axis";
import { constrainZoom, useGraphContentBounds } from "../utility/component";

/**
 *
 * @param {{
 *  plots: [
 *      { color, label, points: [{ x: float, y:float }] }
 *  ],
 *  xRange,
 *  yRange,
 *  xLabel,
 *  yLabel
 * }} props
 * @returns
 */
export function Graph2d(props) {
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

    return (
        <div ref={ref}>
            <Zoom
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
                    //TODO(pjm): scale y range over visible points
                    domain: [yRange.min, yRange.max],
                    range: [gc.height, 0],
                    nice: true
                });

                let legendScale = Scale.scaleOrdinal({
                    domain: plots.map(plot => plot.label),
                    range: plots.map(plot => plot.color)
                })

                let strokeWidth = Math.max(2 / zoom.transformMatrix.scaleX, 1);

                let toPath = (plot, index) => {
                    return (
                        <Shape.LinePath key={index} data={plot.points} x={d => xScale(d.x)} y={d => yScale(d.y)} stroke={plot.color} strokeWidth={strokeWidth}>

                        </Shape.LinePath>
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
                                />
                                <g clipPath="url(#graph-clip)">
                                    <g transform={zoom.toString()} >
                                        {paths}
                                    </g>
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
