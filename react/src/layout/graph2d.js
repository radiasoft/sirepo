import { Graph2d } from "../component/graph2d";
import { View } from "./layout";

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

export class Graph2dFromApi extends View {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props) => {
        let { simulationData } = props;

        let config = apiResponseToGraph2dConfig(simulationData);

        return (
            <Graph2d {...config} {...props}/>
        )
    }
}
