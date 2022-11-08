// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { Heatplot, HeatPlotConfig } from "../component/reusable/heatplot";
import { LayoutProps, View } from "./layout";
import React from "react";

export type HeatplotConfigApi = {
    title: string,
    x_label: string,
    x_range: [number, number],
    y_label: string,
    y_range: [number, number],
    z_matrix: number[][]
}

function apiResponseToHeatplotConfig(apiResponse: HeatplotConfigApi): HeatPlotConfig {
    let {
        title,
        x_label: xLabel,
        x_range: xRange,
        y_range: yRange,
        y_label: yLabel,
        z_matrix: zMatrix
    } = apiResponse;

    if (! xRange) {
        return undefined;
    }
    let [xMin, xMax] = xRange;
    let [yMin, yMax] = yRange;
    return {
        title,
        zMatrix,
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

export class HeatplotFromApi extends View<undefined> {
    getFormDependencies = (config: undefined) => {
        return [];
    }

    component = (props: { simulationData: HeatplotConfigApi } & LayoutProps<undefined>) => {
        let { simulationData } = props;

        let config = apiResponseToHeatplotConfig(simulationData);

        return (
            <>{config && <Heatplot {...config} {...props}/>}</>
        )
    }
}
