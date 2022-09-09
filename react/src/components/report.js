import { useContext, useState, useEffect } from "react";
import { Dependency, useDependentValues } from "../dependency";
import { ContextSimulationInfoPromise, ContextAppName, ContextRelativeFormDependencies, ContextModels } from "./context";

function pollRunReport({ appName, models, simulationId, report, pollInterval}, callback) {
    /*return new Promise((resolve, reject) => {
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
                } else if (state === 'pending' || state === 'running') {
                    setTimeout(doFetch, pollInterval); // TODO
                } else {
                    reject();
                }
            })
        }
        doFetch();
    })*/

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
                callback(simulationStatus);
            } else if (state === 'pending' || state === 'running') {
                setTimeout(doFetch, pollInterval); // TODO
                if(state === 'running') {
                    callback(simulationStatus);
                }
            } else {
                throw new Error("simulation status could not be handled: ", simulationStatus);
            }
        })
    }
    doFetch();
}

export function AutoRunReportLayout(layoutElement) {
    return {
        getDependencies: layoutElement.getDependencies,

        element: (props) => {
            let { config } = props;
            let { report } = config;

            let dependencyStrings = config.dependencies;
    
            let contextFn = useContext;
            let stateFn = useState;
            let effectFn = useEffect;
            let dependentValuesFn = useDependentValues;
    
            let simulationInfoPromise = contextFn(ContextSimulationInfoPromise);
            let appName = contextFn(ContextAppName);
            let modelsWrapper = contextFn(ContextModels);

            let formDependencies = contextFn(ContextRelativeFormDependencies);
            let reportDependencies = dependencyStrings.map(dependencyString => new Dependency(dependencyString));

            let dependentValues = dependentValuesFn(modelsWrapper, [...formDependencies, ...reportDependencies]);

            console.log("dependentValues", dependentValues);
    
            let [simulationData, updateSimulationData] = stateFn(undefined);
    
            effectFn(() => {
                updateSimulationData(undefined);
                let simulationDataPromise = new Promise((resolve, reject) => {
                    simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                        console.log("starting to poll report");
                        /*pollRunReport({
                            appName,
                            models,
                            simulationId,
                            report: report,
                            pollInterval: 500
                        }).then((simulationData) => {
                            console.log("finished polling report");
                            resolve(simulationData);
                        })*/
                        pollRunReport({
                            appName,
                            models,
                            simulationId,
                            report: report,
                            pollInterval: 500
                        }, (simulationData) => {
                            console.log("polling report yielded new data");
                            resolve(simulationData);
                        })
                    })
                });
        
                simulationDataPromise.then(updateSimulationData);
            }, dependentValues)
    
            
    
            let VisualComponent = simulationData ? layoutElement.element : undefined;
            //let VisualComponent = layoutElement.element;
    
            return (
                <>
                    {VisualComponent && <VisualComponent config={config} simulationData={simulationData}></VisualComponent>}
                </>
            )
        }
    }
}
