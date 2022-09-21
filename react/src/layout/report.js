import { useContext, useState, useRef, useEffect } from "react";
import { Dependency } from "../data/dependency";
import { ContextSimulationInfoPromise, ContextAppName, ContextRelativeFormDependencies, ContextModelsWrapper, ContextLayouts, ContextReportEventManager } from "../context";
import { useDependentValues } from "../hook/dependency";
import { View } from "./layout";
import { cancelReport, pollRunReport } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';
import { useStore } from "react-redux";
import { ProgressBar, Stack, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";

export class AutoRunReportLayout extends View {
    getFormDependencies = (config) => {
        let { reportLayout } = config;
        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        return layoutElement.getFormDependencies();
    }

    component = (props) => {
        let { config } = props;
        let { report, reportLayout, dependencies } = config;

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let appName = useContext(ContextAppName);
        let modelsWrapper = useContext(ContextModelsWrapper);

        let formDependencies = useContext(ContextRelativeFormDependencies);
        let reportDependencies = dependencies.map(dependencyString => new Dependency(dependencyString));

        let dependentValues = useDependentValues(modelsWrapper, [...formDependencies, ...reportDependencies]);

        let [simulationData, updateSimulationData] = useState(undefined);

        let simulationPollingVersionRef = useRef(uuidv4())

        useEffect(() => {
            updateSimulationData(undefined);
            let pollingVersion = uuidv4();
            simulationPollingVersionRef.current = pollingVersion;
            simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                console.log("starting to poll report");
                pollRunReport({
                    appName,
                    models,
                    simulationId,
                    report: report,
                    pollInterval: 500,
                    callback: (simulationData) => {
                        console.log("polling report yielded new data", simulationData);
                        // guard concurrency
                        if(simulationPollingVersionRef.current == pollingVersion) {
                            updateSimulationData(simulationData);
                        } else {
                            console.log("polling data was not from newest request");
                        }
                    }
                })
            })
        }, dependentValues)    

        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);

        let VisualComponent = simulationData ? layoutElement.component : undefined;

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {VisualComponent && <VisualComponent key={simulationPollingVersionRef.current} config={reportLayout} simulationData={simulationData}></VisualComponent>}
            </>
        )
    }
}

export class ManualRunReportLayout extends View {
    getFormDependencies = (config) => {
        let { reportLayout } = config;
        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        return layoutElement.getFormDependencies();
    }


}

export class SimulationStartLayout extends View {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props) => {
        let { config } = props;
        let { reportName } = config;

        let reportEventManager = useContext(ContextReportEventManager);
        let appName = useContext(ContextAppName);
        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let modelsWrapper = useContext(ContextModelsWrapper);

        let store = useStore();

        let [lastSimulationData, updateLastSimulationData] = useState(undefined);
        let [lastSimulationStartTime, updateLastSimulatonStartTime] = useState(undefined);

        let simulationPollingVersionRef = useRef(uuidv4())

        let startSimulation = () => {
            updateLastSimulationData(undefined);
            updateLastSimulatonStartTime(new Date());
            let pollingVersion = uuidv4();
            simulationPollingVersionRef.current = pollingVersion;

            reportEventManager.onReportData(reportName, (simulationData) => {
                if(simulationPollingVersionRef.current === pollingVersion) {
                    updateLastSimulationData(simulationData);
                }
            })

            simulationInfoPromise.then(({simulationId}) => {
                reportEventManager.startReport({
                    appName,
                    models: modelsWrapper.getModels(store.getState()),
                    simulationId,
                    report: reportName
                })
            })   
        }

        let endSimulation = () => {
            updateLastSimulationData(undefined);
            updateLastSimulatonStartTime(undefined);
            simulationPollingVersionRef.current = uuidv4();

            simulationInfoPromise.then(({simulationId}) => {
                cancelReport({
                    appName,
                    models: modelsWrapper.getModels(store.getState()),
                    simulationId,
                    report: reportName
                })
            })   
        }

        let endSimulationButton = <Button variant="primary" onClick={endSimulation}>End Simulation</Button>;
        let startSimulationButton = <Button variant="primary" onClick={startSimulation}>Start Simulation</Button>

        if(lastSimulationData) {
            let { state } = lastSimulationData;

            let getStateBasedElement = (state) => {
                switch(state) {
                    case 'pending':
                        return (
                            <Stack gap={2}>
                                <span><FontAwesomeIcon fixedWidth icon={Icon.faHourglass}/>{` Pending...`}</span>
                                {endSimulationButton}
                            </Stack>
                        )
                    case 'running':
                        return (
                            <Stack gap={2}>
                                <span>{`Running`}</span>
                                <ProgressBar animated now={100}></ProgressBar>
                                {endSimulationButton}
                            </Stack>
                        )
                    case 'completed':
                        let elapsedTimeSeconds = Math.ceil(((new Date()) - lastSimulationStartTime) / 1000)
                        return (    
                            <Stack gap={2}>
                                <span>{'Simulation Completed'}</span>
                                <span>{`Elapsed time: ${elapsedTimeSeconds} seconds`}</span>
                                {startSimulationButton}
                            </Stack>
                        )
                }
            }

            return (
                <>{getStateBasedElement(state)}</>
            )
        }
        return <>{startSimulationButton}</>
    }
}
