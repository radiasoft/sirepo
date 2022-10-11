// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { useLayoutEffect, useRef, useState } from 'react';
import { Zoom } from '@visx/zoom';
import { Axis, ClipPath, Scale, Shape } from '@visx/visx';
import { LegendOrdinal } from "@visx/legend";
import { format } from "d3-format";
import "./graph2d.scss";


//TODO(pjm): use a library for this or put in a sirepo utility
function debounce(fn, ms) {
    let timer
    return _ => {
        clearTimeout(timer)
        timer = setTimeout(_ => {
            timer = null
            fn.apply(this, arguments)
        }, ms)
    };
}

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
    const [dim, setDim] = useState({
        width: 100,
        height: 100,
    });
    const [ticks, setTicks] = useState({
        xTicks: 5,
        yTicks: 5,
    });

    useLayoutEffect(() => {
        if (! ref || ! ref.current) {
            return;
        }

        const handleResize = debounce(() => {
            if (! ref || ! ref.current) {
                return;
            }
            const w = Number.parseInt(ref.current.offsetWidth);
            //TODO(pjm): use aspectRatio
            const h = Number.parseInt(w * 9 / 16);
            setDim({
                width: w,
                height: h,
            });
            setTicks({
                xTicks: Math.max(Math.round(w / 100), 2),
                yTicks: Math.max(Math.round(h / 50), 2),
            });
        }, 250);
        window.addEventListener('resize', handleResize);
        handleResize();
        return _ => {
            window.removeEventListener('resize', handleResize);
        };
    }, [ref]);

    let xAxisSize = 30;
    let yAxisSize = 40;

    let margin = 25;

    let graphHeight = dim.height - xAxisSize - margin * 2;
    let graphWidth = dim.width - yAxisSize - margin * 2;

    let graphX = yAxisSize + margin;
    let graphY = margin;

    function constrain(transformMatrix) {
        // no Y zoom
        transformMatrix.scaleY = 1;
        transformMatrix.translateY = 0;
        // constrain X zoom/pan within plot boundaries
        if (transformMatrix.scaleX < 1) {
            transformMatrix.scaleX = 1;
            transformMatrix.translateX = 0;
        }
        else {
            if (transformMatrix.translateX > 0) {
                transformMatrix.translateX = 0;
            }
            else if (graphWidth * transformMatrix.scaleX + transformMatrix.translateX < graphWidth) {
                transformMatrix.translateX = graphWidth - graphWidth * transformMatrix.scaleX;
            }
        }
        return transformMatrix;
    }

    return (
        <div ref={ref}>
        <Zoom
            height={dim.height}
            width={dim.width}
            constrain={constrain}
        >
            {(zoom) => {
                let xScale = Scale.scaleLinear({
                    domain: [xRange.min, xRange.max],
                    range: [0, graphWidth],
                });

                let yScale = Scale.scaleLinear({
                    //TODO(pjm): scale y range over visible points
                    domain: [yRange.min, yRange.max],
                    range: [graphHeight, 0],
                    nice: true
                });

                let xScaleZoom = Scale.scaleLinear({
                    domain: [xScale.invert((xScale(xRange.min) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                             xScale.invert((xScale(xRange.max) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),],
                    range: [0, graphWidth],

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
                let tickFormat = format(",.2e");

                return (
                    <>
                        <svg
                            ref={zoom.containerRef}
                            style={{'userSelect': 'none'}}
                            viewBox={`${0} ${0} ${dim.width} ${dim.height}`}
                        >
                            <ClipPath.RectClipPath id={"graph-clip"} width={graphWidth} height={graphHeight}/>
                            <g transform={`translate(${graphX} ${graphY})`} width={graphWidth} height={graphHeight}>
                                <Axis.AxisBottom
                                    stroke={"#888"}
                                    tickStroke={"#888"}
                                    scale={xScaleZoom}
                                    top={graphHeight}
                                    tickFormat={tickFormat}
                                    numTicks={ticks.xTicks}
                                    label={xLabel}
                                    labelClassName={"sr-x-axis-label"}
                                    labelOffset={15}
                                    tickLabelProps={() => ({
                                        fontSize: 13,
                                        textAnchor: "middle",
                                        verticalAnchor: "middle",
                                    })}
                                />
                                <Axis.AxisLeft
                                    stroke={"#888"}
                                    tickStroke={"#888"}
                                    scale={yScale}
                                    tickFormat={tickFormat}
                                    numTicks={ticks.yTicks}
                                    tickLabelProps={() => ({
                                        fontSize: 13,
                                        textAnchor: "end",
                                        verticalAnchor: "middle",
                                    })}
                                />
                                <g clipPath="url(#graph-clip)">
                                    <g transform={zoom.toString()} >
                                        {paths}
                                    </g>
                                </g>
                                <rect
                                    width={graphWidth}
                                    height={graphHeight}
                                    style={{'fill': 'none', 'cursor': cursor, 'pointerEvents': 'all'}}
                                ></rect>
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
