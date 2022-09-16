export function pollCompute({ doFetch, pollInterval, callback }) {
    let doIteration = () => {
        doFetch().then(async (resp) => {
            let respObj = await resp.json();
            let { state } = respObj;
            console.log("polled stateful compute: " + state);

            if (state === 'pending' || state === 'running') {
                setTimeout(doIteration, pollInterval);
            }

            callback(respObj);
        })
    }

    doIteration();
}

export function pollStatefulCompute({ pollInterval, method, simulationId, appName, callback }) {
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

export function pollRunReport({ appName, models, simulationId, report, pollInterval, callback }) {
    let doFetch = () => fetch('/run-simulation', {
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
    });

    pollCompute({
        doFetch,
        pollInterval,
        callback: (respObj) => {
            let { state } = respObj;

            if(state === 'completed' || state === 'running') {
                callback(respObj);
            }
        }
    })
}
