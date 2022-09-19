import { Zoom } from '@visx/zoom';
import { Axis, ClipPath, Scale, Shape } from '@visx/visx';

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
    let { width, height, plots, xRange, yRange, xLabel, yLabel } = props;

    const intWidth = 500;
    //TODO(pjm): aspect ratio
    const intHeight = Number.parseInt(intWidth * 9 / 16);

    let xAxisSize = 30;
    let yAxisSize = 30;

    let margin = 10;

    let graphHeight = intHeight - xAxisSize - margin * 2;
    let graphWidth = intWidth - yAxisSize - margin * 2;

    // TODO: make legend

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
        <Zoom
            height={intHeight}
            width={intWidth}
            constrain={constrain}
        >
            {(zoom) => {
                let xScale = Scale.scaleLinear({
                    domain: [xRange.min, xRange.max],
                    range: [0, graphWidth],
                    round: true
                });

                let yScale = Scale.scaleLinear({
                    //TODO(pjm): scale y range over visible points
                    domain: [yRange.min, yRange.max],
                    range: [graphHeight, 0],
                    round: true,
                    nice: true,
                });

                let xScaleZoom = Scale.scaleLinear({
                    domain: [xScale.invert((xScale(xRange.min) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                             xScale.invert((xScale(xRange.max) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),],
                    range: [0, graphWidth],
                    round: true
                });

                let toPath = (plot, index) => {
                    return (
                        <Shape.LinePath key={index} data={plot.points} x={d => xScale(d.x)} y={d => yScale(d.y)} stroke={plot.color}>

                        </Shape.LinePath>
                    )
                }

                let paths = plots.map((plot, i) => toPath(plot, i));
                const cursor = zoom.transformMatrix.scaleX > 1 ? 'ew-resize' : 'zoom-in';

                return (
                    <svg
                        height={height}
                        width={width}
                        ref={zoom.containerRef}
                        style={{'userSelect': 'none'}}
                        viewBox={`${0} ${0} ${intWidth} ${intHeight}`}
                    >
                        <ClipPath.RectClipPath id={"graph-clip"} width={graphWidth} height={graphHeight}/>
                        <g transform={`translate(${graphX} ${graphY})`} width={graphWidth} height={graphHeight}>
                            <Axis.AxisBottom
                                stroke={"#888"}
                                tickStroke={"#888"}
                                scale={xScaleZoom}
                                top={graphHeight}
                            />
                            <Axis.AxisLeft
                                stroke={"#888"}
                                tickStroke={"#888"}
                                scale={yScale}
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
                )
            }}
        </Zoom>
    )
}
