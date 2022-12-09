import { ModelStates } from "../store/models";

export type SrState = 'completed' | 'srException' | 'error' | 'running' | 'pending' | 'canceled' | 'missing';

export type ResponseHasState = {
    state: SrState,
    [key: string]: any
}

export type BaseComputeParams = {
    pollInterval: number,
    callback: (resp: ResponseHasState) => void
}

export function pollCompute({ doFetch, pollInterval, callback }: BaseComputeParams & { doFetch: () => Promise<Response> }) {
    let iterate = () => {
        doFetch().then(async (resp) => {
            let respObj: ResponseHasState = await resp.json();
            let { state } = respObj;

            if (state === 'pending' || state === 'running') {
                setTimeout(iterate, pollInterval);
            }

            callback(respObj);
        })
    }

    iterate();
}

export type StatefulComputeParams = {
    simulationId: string,
    appName: string
} & BaseComputeParams

export function pollStatefulCompute({ pollInterval, method, simulationId, appName, callback }: StatefulComputeParams & { method: string }) {
    let doFetch = () => fetch('/stateful-compute', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            method,
            simulationId,
            simulationType: appName
        })
    });

    pollCompute({
        doFetch,
        pollInterval,
        callback: (respObj) => {
            let { state } = respObj;

            if(state === 'completed') {
                callback(respObj);
            }
        }
    })
}

export type ReportComputeParams = {
    forceRun: boolean
    models: ModelStates,
    report: string
} & StatefulComputeParams

export function pollRunReport({ appName, models, simulationId, report, pollInterval, callback, forceRun }: ReportComputeParams) {
    let doFetch = () => fetch('/run-simulation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            models,
            forceRun,
            report,
            simulationId,
            simulationType: appName
        })
    }).then(async (resp) => {
        return await resp.json() as ResponseHasState
    });

    doFetch().then(resp => {
        callback(resp);
        pollRunStatus({
            pollInterval,
            callback,
            simulationId,
            models,
            appName,
            report,
            forceRun
        });
    });
}

export type CancelComputeParams = {
    appName: string,
    models: ModelStates,
    simulationId: string,
    report: string
}

export function cancelReport({ appName, models, simulationId, report }: CancelComputeParams): Promise<Response> {
    return fetch('/run-cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            models,
            forceRun: false,
            report,
            simulationId,
            simulationType: appName
        })
    })
}

export type RunStatusParams = {
    appName: string,
    models: ModelStates,
    simulationId: string,
    report: string,
    forceRun: boolean
} & {[key: string]: any}

export function getRunStatusOnce({ appName, ...otherParams }: RunStatusParams): Promise<ResponseHasState> {
    let doStatus = () => fetch('/run-status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            simulationType: appName,
            ...otherParams
        }),
    });

    return new Promise<ResponseHasState>((resolve, reject) => {
        doStatus().then(async lastResp => resolve(await lastResp.json()));
    })
    
}

export type RunStatusPollParams = {
    callback: (simulationData: ResponseHasState) => void,
    pollInterval: number
} & RunStatusParams

export function pollRunStatus({ callback, pollInterval, ...otherParams }: RunStatusPollParams) {
    let iterate = (lastResp: ResponseHasState) => {
        let { nextRequest, state } = lastResp;

        callback(lastResp);

        if (!state || state === 'pending' || state === 'running') {
            setTimeout(() => getRunStatusOnce(nextRequest).then(iterate), pollInterval);
        }
    }

    getRunStatusOnce(otherParams).then(iterate);
}

export function getSimulationFrame(frameId: string) {
    return new Promise((resolve, reject) => {
        fetch(`/simulation-frame/${frameId}`).then(async (resp) => {
            let respObj = await resp.json();
            resolve(respObj);
        })
    })
}
