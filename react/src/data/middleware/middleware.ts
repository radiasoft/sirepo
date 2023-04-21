import { Middleware } from "redux";
import { Schema } from "../../utility/schema";
import { shadowBeamlineSortingMiddleware } from "./shadow/beamline";
import { shadowBeamlineWatchpointReportsMiddleware } from "./shadow/watchpoint";

export type ConfigurableMiddleware<C> = (config: C, schema: Schema) => Middleware

export const Middlewares: {[key: string]: ConfigurableMiddleware<any>} = {
    shadowWatchpointsFromBeamline: shadowBeamlineWatchpointReportsMiddleware,
    shadowBeamlineSorting: shadowBeamlineSortingMiddleware
}

export function middlewaresForSchema(schema: Schema): Middleware[] {
    console.log("schema middleware", schema.middleware);
    return (schema.middleware || []).map(sm => Middlewares[sm.type](sm.config, schema));
}
