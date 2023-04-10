import React from "react";
import { Graph2d, Graph2dConfig } from "../../component/reusable/graph2d";
import { Point2d } from "../../types";
import { LayoutProps } from "../layout";
import { ReportVisual, ReportVisualProps } from "../report";

export type Histogram2dConfigApi = {
    points: number[],
    title: string,
    x_label: string,
    x_range: number[],
    y_label: string
}

export function apiResponseHistogramToGraph2dConfig(cfg: Histogram2dConfigApi): Graph2dConfig {
    if(!cfg || !cfg.x_range) return undefined;
    
    // TODO: put in schema or get from server
    let color = "#006699";
    let [xMin, xMax, numPoints] = cfg.x_range;
    let xStep = (xMax - xMin) / numPoints;

    let yMin = Math.min(...cfg.points);
    let yMax = Math.max(...cfg.points);

    let points = cfg.points.flatMap((v, i): Point2d[] => {
        return [
            {
                x: xMin + (xStep * i),
                y: v
            },
            {
                x: xMin + (xStep * (i + 1)),
                y: v
            }
        ]
    })
    return {
        title: cfg.title,
        plots: [
            {
                color,
                label: undefined,
                points
            }
        ],
        xLabel: cfg.x_label,
        yLabel: cfg.y_label,
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

export class Histogram2dFromApi extends ReportVisual<undefined, {}, Histogram2dConfigApi, Graph2dConfig> {
    getConfigFromApiResponse(apiReponse: Histogram2dConfigApi): Graph2dConfig {
        return apiResponseHistogramToGraph2dConfig(apiReponse);
    }

    canShow(apiResponse: Histogram2dConfigApi): boolean {
        return !!this.getConfigFromApiResponse(apiResponse);
    }

    component = (props: LayoutProps<{}> & ReportVisualProps<Graph2dConfig>) => {
        let { data, model } = props;
        if(!data) {
            throw new Error("histogram2d received falsy data prop");
        }

        // TODO: extras from model

        return (
            <Graph2d {...data}/>
        )
    }
}
