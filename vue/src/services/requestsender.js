import { appState } from '@/services/appstate.js';
import { msgRouter } from '@/services/msgrouter.js';

class RequestSender {
    #isObject(value) {
        return value !== null && typeof value === 'object';
    }

    async sendRequest(routeName, requestData) {
        if (typeof(routeName) != 'string') {
            throw new Error(`Invalid routeName, expecting string: ${routeName}`);
        }
        if (requestData.responseType) {
            throw new Error(`requestData.responseType not yet supported: ${requestData.responseType}`);
        }
        const r = appState.schema.route[routeName];
        requestData[
            r.includes('<simulation_type>')
                ? 'simulation_type'
                : 'simulationType'
        ] = appState.simulationType;
        if (appState.isLoadedRef.value && ! requestData.simulationId) {
            requestData.simulationId = appState.models.simulation.simulationId;
        }
        const resp = await msgRouter.send(r, requestData, {});
        if (! this.#isObject(resp.data) || resp.data.state === 'srException') {
            throw new Error(resp);
        }
        return resp.data;
    }
}

export const requestSender = new RequestSender();
