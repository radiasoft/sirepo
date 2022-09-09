import { useContext, useState, useEffect } from "react";
import { ContextSimulationInfoPromise, ContextAppName } from "./context";
import { Panel } from "./panel";

function pollRunReport({ appName, models, simulationId, report, pollInterval}) {
    return new Promise((resolve, reject) => {
        let doFetch = () => {
            fetch('/run-simulation', {
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
            }).then(async (resp) => {
                let simulationStatus = await resp.json();
                console.log("status", simulationStatus);
                let { state } = simulationStatus;
                console.log("polled report: " + state);
                if(state === 'completed') {
                    resolve(simulationStatus);
                } else if (state === 'pending') {
                    setTimeout(doFetch, pollInterval); // TODO
                } else {
                    reject();
                }
            })
        }
        doFetch();
    })
}

export function ReportLayout(layoutElement) {
    return {
        getDependencies: layoutElement.getDependencies,

        element: (props) => {
            let { config } = props;
            let { report } = config;
    
            let contextFn = useContext;
            let stateFn = useState;
            let effectFn = useEffect;
    
            let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);
            let appName = contextFn(ContextAppName);
    
            let [simulationData, updateSimulationData] = stateFn(undefined);
    
            effectFn(() => {
                let simulationDataPromise= new Promise((resolve, reject) => {
                    simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                        console.log("starting to poll report");
                        pollRunReport({
                            appName,
                            models,
                            simulationId,
                            report: report,
                            pollInterval: 500
                        }).then((simulationData) => {
                            console.log("finished polling report");
                            resolve(simulationData);
                        })
                    })
                });
        
                simulationDataPromise.then(updateSimulationData);
            }, [])
    
            
    
            let VisualComponent = simulationData ? layoutElement.element : undefined;
    
            return (
                <>
                    {VisualComponent && <VisualComponent config={config} simulationData={simulationData}></VisualComponent>}
                </>
            )
        }
    }
}
