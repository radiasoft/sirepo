import { Middleware } from "redux";
import { SimulationInfo, SimulationInfoRaw } from "../../component/simulation";
import { Schema } from "../../utility/schema";
import { saveMiddleware } from "./save";
import { shadowBeamlineSortingMiddleware } from "./shadow/beamline";
import { shadowBeamlineWatchpointReportsMiddleware } from "./shadow/watchpoint";

export type ConfigurableMiddleware<C> = (config: C, schema: Schema, simulationInfo: SimulationInfoRaw) => Middleware

export const Middlewares: {[key: string]: ConfigurableMiddleware<any>} = {
    shadowWatchpointsFromBeamline: shadowBeamlineWatchpointReportsMiddleware,
    shadowBeamlineSorting: shadowBeamlineSortingMiddleware,
    save: saveMiddleware
}

export function middlewaresForSchema(schema: Schema, simulationInfo: SimulationInfoRaw): Middleware[] {
    return (schema.middleware || []).map(sm => Middlewares[sm.type](sm.config, schema, simulationInfo));
}
