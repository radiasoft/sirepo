import { SimulationInfo } from "../../component/simulation";
import { StoreState } from "../../store/common";
import { ModelState } from "../../store/models";
import { StoreTypes } from "../data";
import { ConfigurableMiddleware } from "./middleware"

export type SaveMiddlewareConfig = {
    debounceDelaySeconds: number,
    maxIntervalSeconds: number
}

const saveModelsToServer = (simulationInfo: SimulationInfo, models: StoreState<ModelState>): Promise<Response> => {
    simulationInfo = {...simulationInfo}; // clone, no mutations
    simulationInfo.models = models;
    return fetch("/save-simulation", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(simulationInfo)
    })
}

export const saveMiddleware: ConfigurableMiddleware<SaveMiddlewareConfig> = (config, schema, simulationInfo) => {
    let saveTimeout = undefined;
    let firstUpdateInSave = undefined;
    return store => next => action => {
        if(action.type === "models/updateModel") {
            if(firstUpdateInSave === undefined) {
                firstUpdateInSave = Date.now();
            }
            if(saveTimeout !== undefined) {
                clearTimeout(saveTimeout);
            }

            let timeUntilSave = Math.min(config.debounceDelaySeconds, Math.min(0, config.maxIntervalSeconds - (Date.now() - firstUpdateInSave) / 1000))

            saveTimeout = setTimeout(() => {
                firstUpdateInSave = undefined;
                console.log("simulationInfo", simulationInfo);
                console.log("models", store.getState()[StoreTypes.Models.name])
                saveModelsToServer(simulationInfo, store.getState()[StoreTypes.Models.name])
            }, timeUntilSave)
        }
        return next(action);
    }
}
