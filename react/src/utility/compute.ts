import { StoreState } from "../store/common";
import { ModelState } from "../store/models";
import { RouteHelper } from "./route";

export type SrState = 'completed' | 'srException' | 'error' | 'running' | 'pending' | 'canceled' | 'missing';

export type ResponseHasState = {
    state: SrState,
    [key: string]: any
}

export type BaseComputeParams = {
    callback: (resp: ResponseHasState) => void
}

export function pollCompute(routeHelper: RouteHelper, { doFetch, callback }: BaseComputeParams & { doFetch: () => Promise<Response> }) {
    let iterate = () => {
        doFetch().then(async (resp) => {
            let respObj: ResponseHasState = await resp.json();
            let { state } = respObj;

            if (state === 'pending' || state === 'running') {
                setTimeout(iterate, respObj.nextRequestSeconds * 1000);
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

export function pollStatefulCompute(routeHelper: RouteHelper, { method, simulationId, appName, callback }: StatefulComputeParams & { method: string }) {
    let doFetch = () => fetch(routeHelper.globalRoute("statefulCompute"), {
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

    pollCompute(routeHelper, {
        doFetch,
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
    models: StoreState<ModelState>,
    report: string
} & StatefulComputeParams

export function pollRunReport(routeHelper: RouteHelper, { appName, models, simulationId, report, callback, forceRun }: ReportComputeParams) {
    let doFetch = () => fetch(routeHelper.globalRoute("runSimulation"), {
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
        if (resp.nextRequest) {
            pollRunStatus(routeHelper, {
                callback: callback,
                ...resp.nextRequest,
            });
        }
    });
}

export type CancelComputeParams = {
    appName: string,
    models: StoreState<ModelState>,
    simulationId: string,
    report: string
}

export function cancelReport(routeHelper: RouteHelper, { appName, models, simulationId, report }: CancelComputeParams): Promise<Response> {
    return fetch(routeHelper.globalRoute("runCancel"), {
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
    models?: StoreState<ModelState>,
    simulationId: string,
    report: string,
    forceRun: boolean
} & {[key: string]: any}

export function getRunStatusOnce(routeHelper: RouteHelper, { appName, ...otherParams }: RunStatusParams): Promise<ResponseHasState> {
    let doStatus = () => fetch(routeHelper.globalRoute("runStatus"), {
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
} & RunStatusParams

export function pollRunStatus(routeHelper: RouteHelper, { callback, ...otherParams }: RunStatusPollParams) {
    let iterate = (lastResp: ResponseHasState) => {
        let { nextRequest, state, nextRequestSeconds } = lastResp;

        callback(lastResp);

        if (!state || state === 'pending' || state === 'running') {
            setTimeout(() => getRunStatusOnce(routeHelper, nextRequest).then(iterate), nextRequestSeconds * 1000);
        }
    }

    getRunStatusOnce(routeHelper, otherParams).then(iterate);
}

export function getSimulationFrame(routeHelper: RouteHelper, frameId: string) {
    return new Promise((resolve, reject) => {
        fetch(routeHelper.globalRoute("simulationFrame", { frame_id: frameId })).then(async (resp) => {
            let respObj = await resp.json();
            resolve(respObj);
        })
    })
}
