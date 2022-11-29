import { ModelStates } from "../store/models";

export type BaseComputeParams = {
    pollInterval: number,
    callback: (resp: any) => void
}

export function pollCompute({ doFetch, pollInterval, callback }: BaseComputeParams & { doFetch: () => Promise<Response> }) {
    let iterate = () => {
        doFetch().then(async (resp) => {
            let respObj = await resp.json();
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
    });

    let doPoll = (nextRequest) => fetch('/run-status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            ...nextRequest
        })
    });

    let iterate = async (lastResp) => {
        let respObj = await lastResp.json();
        let { nextRequest, state } = respObj;

        callback(respObj);

        if (!state || state === 'pending' || state === 'running') {
            setTimeout(() => doPoll(nextRequest).then(iterate), pollInterval);
        }
    }

    doFetch().then(iterate);
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
    callback: (resp: any) => void,
    forceRun: boolean
}

export function runStatus({ appName, models, simulationId, report, callback, forceRun }: RunStatusParams) {
    let doStatus = () => fetch('/run-status', {
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
        }),
    });
    doStatus().then(async lastResp => callback(await lastResp.json()));
}

export function getSimulationFrame(frameId: string) {
    return new Promise((resolve, reject) => {
        fetch(`/simulation-frame/${frameId}`).then(async (resp) => {
            let respObj = await resp.json();
            resolve(respObj);
        })
    })
}
