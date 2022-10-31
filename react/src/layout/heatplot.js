// import { React }
/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { Heatplot } from "../component/heatplot";
import { View } from "./layout";

function apiResponseToHeatplotConfig(apiResponse) {
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

export class HeatplotFromApi extends View {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props) => {
        let { simulationData } = props;

        let config = apiResponseToHeatplotConfig(simulationData);

        return (
            <>{config && <Heatplot {...config} {...props}/>}</>
        )
    }
}
