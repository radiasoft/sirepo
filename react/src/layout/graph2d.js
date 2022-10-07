import { useEffect, useContext } from "react";
import { Graph2d } from "../component/graph2d";
import { ContextPanelController } from "../context";
import { View } from "./layout";

export function apiResponseToGraph2dConfig(apiResponse) {
    let {
        plots,
        title,
        x_label: xLabel,
        x_points: xPoints,
        x_range: xRange,
        y_range: yRange,
        y_label: yLabel
    } = apiResponse;

    if(!plots) {
        return undefined; // fault tolerance. server behavior is inconsistent here
    }

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
            <>{config && <Graph2d {...config} {...props}/>}</>
        )
    }
}
