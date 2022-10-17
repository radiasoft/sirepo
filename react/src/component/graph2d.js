// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { useRef } from 'react';
import { Zoom } from '@visx/zoom';
import { ClipPath, Scale, Shape } from '@visx/visx';
import { LegendOrdinal } from "@visx/legend";
import { DynamicAxis } from "./axis";
import { constrainZoom, useRefSize, plotSizeInfo } from "./util";

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
    const dim = useRefSize(ref, 9 / 16.0);
    const ps = plotSizeInfo(dim);

    function constrain(transformMatrix) {
        // no Y zoom
        transformMatrix.scaleY = 1;
        transformMatrix.translateY = 0;
        return constrainZoom(transformMatrix, ps.graphWidth, 'X');
    }

    return (
        <div ref={ref}>
            <Zoom
                width={ps.graphWidth}
                height={ps.graphHeight}
                constrain={constrain}
            >
            {(zoom) => {
                let xScale = Scale.scaleLinear({
                    domain: [xRange.min, xRange.max],
                    range: [0, ps.graphWidth],
                });
                xScale.domain([
                    xScale.invert((xScale(xRange.min) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                    xScale.invert((xScale(xRange.max) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                ]);

                let yScale = Scale.scaleLinear({
                    //TODO(pjm): scale y range over visible points
                    domain: [yRange.min, yRange.max],
                    range: [ps.graphHeight, 0],
                    nice: true
                });

                let legendScale = Scale.scaleOrdinal({
                    domain: plots.map(plot => plot.label),
                    range: plots.map(plot => plot.color)
                })

                let toPath = (plot, index) => {
                    return (
                        <Shape.LinePath key={index} data={plot.points} x={d => xScale(d.x)} y={d => yScale(d.y)} stroke={plot.color} strokeWidth={2}>

                        </Shape.LinePath>
                    )
                }

                let paths = plots.map((plot, i) => toPath(plot, i));
                const cursor = zoom.transformMatrix.scaleX > 1 ? 'ew-resize' : 'zoom-in';

                return (
                    <>
                        <svg
                            style={{'userSelect': 'none'}}
                            viewBox={`${0} ${0} ${dim.width} ${dim.height}`}
                        >
                            <ClipPath.RectClipPath id={"graph-clip"} width={ps.graphWidth} height={ps.graphHeight}/>
                            <g transform={`translate(${ps.graphX} ${ps.graphY})`} width={ps.graphWidth} height={ps.graphHeight}>
                                <DynamicAxis
                                    orientation={"bottom"}
                                    scale={xScale}
                                    top={ps.graphHeight}
                                    label={xLabel}
                                    plotSize={dim.width}
                                />
                                <DynamicAxis
                                    orientation={"left"}
                                    scale={yScale}
                                    label={yLabel}
                                    plotSize={dim.height}
                                />
                                <g clipPath="url(#graph-clip)">
                                    <g transform={zoom.toString()} >
                                        {paths}
                                    </g>
                                </g>
                                {/* zoom container must be contained within svg so visx localPoint() works correctly */}
                                <svg><rect
                                    ref={zoom.containerRef}
                                    width={ps.graphWidth}
                                    height={ps.graphHeight}
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
