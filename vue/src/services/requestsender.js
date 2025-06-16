import { appState } from '@/services/appstate.js';
import { msgRouter } from '@/services/msgrouter.js';

class RequestSender {
    #isObject(value) {
        return value !== null && typeof value === 'object';
    }

    async #sendWithSimulationFields(url, data) {
        data.simulationId = data.simulationId || appState.models.simulation.simulationId;
        data.simulationType = appState.schema.simulationType;
        return await this.sendRequest(url, data);
    }

    async sendAnalysisJob(data) {
        return await this.#sendWithSimulationFields('analysisJob', data);
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
        const resp = await msgRouter.send(r, requestData, {});
        // POSIT: typeof [] returns true
        if (! this.#isObject(resp.data) || resp.data.state === 'srException') {
            throw new Error(resp);
        }
        //TODO(pjm): may need to also provide resp.status
        return resp.data;
    }

    async sendStatefulCompute(data) {
        return await this.#sendWithSimulationFields('statefulCompute', data);
    }

    async sendStatelessCompute(data) {
        return await this.#sendWithSimulationFields('statelessCompute', data);
    }
}

export const requestSender = new RequestSender();
