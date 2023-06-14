import { MiddlewareAPI, Store } from "redux";
import { SimulationInfo, SimulationInfoRaw } from "../../component/simulation";
import { StoreState } from "../../store/common";
import { modelActions, ModelState } from "../../store/models";
import { StoreTypes } from "../data";
import { ConfigurableMiddleware } from "./middleware"

export type SaveMiddlewareConfig = {
    debounceDelaySeconds: number,
    maxIntervalSeconds: number
}

const saveModelsToServer = (simulationInfo: SimulationInfo, store: MiddlewareAPI): Promise<Response> => {
    console.log("simulationInfo", simulationInfo)
    let newInfo = {
        version: simulationInfo.version,
        simulationId: simulationInfo.simulationId,
        simulationType: simulationInfo.simulationType,
        models: store.getState()[StoreTypes.Models.name]
    }; // clone, no mutations
    return fetch("/save-simulation", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(newInfo)
    }).then(async resp => {
        let simInfo: SimulationInfoRaw = await resp.json();
        store.dispatch(modelActions.updateModel({
            name: "simulation",
            value: simInfo.models["simulation"]
        }))

        return resp;
    })
}

export const saveMiddleware: ConfigurableMiddleware<SaveMiddlewareConfig> = (config, schema, simulationInfo) => {
    let saveTimeout = undefined;
    let firstUpdateInSave = undefined;
    return store => next => action => {
        if(action.type === "models/updateModel" && action.payload.name !== "simulation") {
            if(firstUpdateInSave === undefined) {
                firstUpdateInSave = Date.now();
            }
            if(saveTimeout !== undefined) {
                clearTimeout(saveTimeout);
            }

            let timeUntilSave = Math.min(config.debounceDelaySeconds, Math.min(0, config.maxIntervalSeconds - ((Date.now() - firstUpdateInSave) / 1000)))

            saveTimeout = setTimeout(() => {
                firstUpdateInSave = undefined;
                saveModelsToServer(store.getState()[StoreTypes.Models.name].simulation, store)
            }, timeUntilSave)
        }
        return next(action);
    }
}
