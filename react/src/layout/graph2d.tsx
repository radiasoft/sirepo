import React from "react";
import { Graph2d, Graph2dConfig } from "../component/reusable/graph2d";
import { LayoutProps, View } from "./layout";

export type Graph2dPlotApi = {
    color: string,
    field: string,
    label: string,
    points: number[]
}

export type Graph2dConfigApi = {
    plots: Graph2dPlotApi[],
    title?: string,
    subtitle?: string,
    x_label: string,
    state: string, // TODO: enumerate
    x_points: number[],
    x_range: [number, number],
    y_label: string,
    y_range: [number, number]

}

export function apiResponseToGraph2dConfig(cfg: Graph2dConfigApi): Graph2dConfig {
    let {
        plots,
        title,
        x_label: xLabel,
        x_points: xPoints,
        x_range: xRange,
        y_range: yRange,
        y_label: yLabel
    } = cfg;

    if(!plots) {
        return undefined; // fault tolerance. server behavior is inconsistent here
    }

    let tempPlots = plots.map(({ color, label, points, field }) => {
        let tempPoints = points.map((y, i) => { return { x: xPoints[i], y } })
        return {
            color,
            label,
            field,
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

export class Graph2dFromApi extends View<undefined> {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props: LayoutProps<undefined> & { simulationData: Graph2dConfigApi }) => {
        let { simulationData } = props;

        let config = apiResponseToGraph2dConfig(simulationData);

        return (
            <>{config && <Graph2d {...config}/>}</>
        )
    }
}
