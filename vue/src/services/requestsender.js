import { appState } from '@/services/appstate.js';
import { msgRouter } from '@/services/msgrouter.js';
import { util } from '@/services/util.js';

class RequestSender {
    async uploadLibFile(file, fileType, confirm=false) {
         const formData = (values) => {
             const fd = new FormData();
             for (const [k, v] of Object.entries(values)) {
                 fd.append(k, v);
             }
             return fd;
         };

        const d = {
            file: file,
            file_type: fileType,
            simulation_id: appState.models.simulation.simulationId,
            simulation_type: appState.simulationType,
        };
        if (confirm) {
            d.confirm = confirm;
        }
        return await msgRouter.send(
            appState.schema.route.uploadLibFile,
            formData(d),
        );
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
        if (! util.isObject(resp.data) || resp.data.state === 'srException') {
            throw new Error(resp);
        }
        return resp.data;
    }
}

export const requestSender = new RequestSender();
