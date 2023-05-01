import { ConfigurableMiddleware } from "./middleware"

export type SaveMiddlewareConfig = {
    minIntervalSeconds: number,
    maxIntervalSeconds: number
}

export const saveMiddleware: ConfigurableMiddleware<SaveMiddlewareConfig> = (config, schema) => {
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

            let timeUntilSave = Math.min(config.minIntervalSeconds, Math.min(0, config.maxIntervalSeconds - (Date.now() - firstUpdateInSave) / 1000))

            saveTimeout = setTimeout(() => {
                firstUpdateInSave = undefined;
                
            }, timeUntilSave)
        }
        return next(action);
    }
}
