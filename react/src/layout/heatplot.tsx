// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { Heatplot, HeatPlotConfig } from "../component/reusable/heatplot";
import { LayoutProps, Layout } from "./layout";
import React from "react";
import { ReportVisual, ReportVisualProps } from "./report";

export type HeatplotConfigApi = {
    title: string,
    x_label: string,
    x_range: [number, number],
    y_label: string,
    y_range: [number, number],
    z_matrix: number[][]
}

function apiResponseToHeatplotConfig(apiResponse: HeatplotConfigApi): HeatPlotConfig {
    if(!apiResponse) return undefined;

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

export class HeatplotFromApi extends ReportVisual<undefined, {}, HeatplotConfigApi, HeatPlotConfig> {
    getConfigFromApiResponse(apiReponse: HeatplotConfigApi): HeatPlotConfig {
        return apiResponseToHeatplotConfig(apiReponse);
    }

    canShow(apiResponse: HeatplotConfigApi): boolean {
        return !!this.getConfigFromApiResponse(apiResponse);
    }

    getFormDependencies = () => {
        return [];
    }

    component = (props: LayoutProps<{}> & ReportVisualProps<HeatPlotConfig>) => {
        let { data } = props;

        return (
            <>{data && <Heatplot {...data} {...props}/>}</>
        )
    }
}
