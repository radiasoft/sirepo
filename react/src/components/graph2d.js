import { Zoom } from '@visx/zoom';
import { Axis, ClipPath, Scale, Shape } from '@visx/visx';

export function apiResponseToGraph2dConfig({
    plots, 
    title, 
    x_label: xLabel, 
    x_points: xPoints, 
    x_range: xRange,
    y_range: yRange,
    y_label: yLabel
}) {
    let tempPlots = plots.map(({ color, label, points }) => {
        let tempPoints = points.map((y, i) => { return { x: xPoints[i], y } })
        return {
            color,
            label,
            points: tempPoints
        }
    });

    let [xMin, xMax] = xRange;
    let [yMin, yMax] = yRange;

    return {
        title,
        plots: tempPlots,
        xLabel,
        yLabel,
        xRange: {
            min: xMin,
            max: xMax
        },
        yRange: {
            min: yMin,
            max: yMax
        }
    }
}

export let Graph2dFromApi = (simulationData) => {
    let config = apiResponseToGraph2dConfig(simulationData);

    return (props) => {
        return (
            <Graph2d {...config} {...props}/>
        )
    }
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
    let { width, height, plots, xRange, yRange, xLabel, yLabel } = props;

    const intHeight = 500;
    const intWidth = 500;

    let xAxisSize = 30;
    let yAxisSize = 30;

    let margin = 10;

    let graphHeight = intHeight - xAxisSize - margin * 2;
    let graphWidth = intWidth - yAxisSize - margin * 2;

    // TODO: make legend

    let graphX = yAxisSize + margin;
    let graphY = margin;

    return (
        
            <Zoom
            
            height={intHeight} 
            width={intWidth}
            scaleXMax={2}
            scaleXMin={1}
            scaleYMax={2}
            scaleYMin={1}
            
            
            >
                {(zoom) => {
                    let xScale = Scale.scaleLinear({
                        domain: [xRange.min, xRange.max],
                        range: [0, graphWidth],
                        round: true
                    });

                    let yScale = Scale.scaleLinear({
                        domain: [yRange.min, yRange.max],
                        range: [graphHeight, 0],
                        round: true
                    });

                    let xScaleZoom = Scale.scaleLinear({
                        domain: [xScale.invert((xScale(xRange.min) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),
                                xScale.invert((xScale(xRange.max) - zoom.transformMatrix.translateX) / zoom.transformMatrix.scaleX),],
                        range: [0, graphWidth],
                        round: true
                    });
                
                    let yScaleZoom = Scale.scaleLinear({
                        domain: [xScale.invert((yScale(yRange.min) - zoom.transformMatrix.translateY) / zoom.transformMatrix.scaleY),
                                xScale.invert((yScale(yRange.max) - zoom.transformMatrix.translateY) / zoom.transformMatrix.scaleY),],
                        range: [graphHeight, 0],
                        round: true
                    });

                    let toPath = (plot, index) => {
                        return (
                        <Shape.LinePath key={index} data={plot.points} x={d => xScale(d.x)} y={d => yScale(d.y)} stroke={plot.color}>
                            
                        </Shape.LinePath>
                        )
                    }

                    let paths = plots.map((plot, i) => toPath(plot, i));

                    return (
                        <svg
                        height={height}
                        width={width}
                        ref={zoom.containerRef}
                        style={{'textSelect': 'none', 'cursor': 'default'}}
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
                                    scale={yScaleZoom}
                                />
                                <g clipPath="url(#graph-clip)">
                                    <g transform={zoom.toString()} >
                                        {paths}
                                    </g>
                                </g>
                            </g>
                        </svg>
                    )
                }}
            </Zoom>
    )
}
