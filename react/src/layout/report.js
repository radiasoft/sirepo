import { useContext, useState, useRef, useEffect } from "react";
import { Dependency, HookedDependencyGroup } from "../data/dependency";
import { ContextPanelController, ContextSimulationInfoPromise, ContextAppName, ContextRelativeFormDependencies, ContextModelsWrapper, ContextLayouts, ContextReportEventManager, ContextSchema } from "../context";
import { useDependentValues } from "../hook/dependency";
import { View } from "./layout";
import { cancelReport, getSimulationFrame, pollRunReport } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';
import { useStore } from "react-redux";
import { ProgressBar, Stack, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { useEvaluatedInterpString } from "../hook/string";

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
                    forceRun: false,
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
        let inProgress = !simulationData || !simulationData.state || simulationData.state !== 'completed'

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {VisualComponent && <VisualComponent key={simulationPollingVersionRef.current} config={reportLayout} simulationData={simulationData}/>}
                {inProgress && <ProgressBar animated now={100}/>}
            </>
        )
    }
}

function getFrameId({
    frameIndex,
    reportName,
    simulationId,
    appName,
    computeJobHash,
    computeJobSerial,
    hookedDependendies
}) {
    let frameIdElements = [
        frameIndex,
        reportName,
        simulationId,
        appName,
        computeJobHash,
        computeJobSerial,
        ...((hookedDependendies || []).map(v => v.value))
    ]

    return frameIdElements.join('*');
}

export class ManualRunReportLayout extends View {
    getFormDependencies = (config) => {
        let { reportLayout } = config;
        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        return layoutElement.getFormDependencies();
    }

    component = (props) => {
        let { config } = props;
        let { reportName, reportGroupName, reportLayout, frameIdFields, shown: shownConfig } = config;
        
        let reportEventManager = useContext(ContextReportEventManager);
        let schema = useContext(ContextSchema);
        let modelsWrapper = useContext(ContextModelsWrapper);
        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let appName = useContext(ContextAppName);

        let [reportData, updateReportData] = useState(undefined);

        let reportEventsVersionRef = useRef(uuidv4())

        let shown = true;

        if(shownConfig) {
            shown = useEvaluatedInterpString(modelsWrapper, shownConfig);
        }

        let frameIdDependencies = frameIdFields.map(f => new Dependency(f));

        let frameIdDependencyGroup = new HookedDependencyGroup({ 
            dependencies: frameIdDependencies,
            modelsWrapper,
            schemaModels: schema.models
        })

        let hookedFrameIdDependencies = frameIdDependencies.map(frameIdDependencyGroup.getHookedDependency);

        useEffect(() => {
            let reportEventsVersion = uuidv4();
            reportEventsVersionRef.current = reportEventsVersion;
            
            reportEventManager.onReportData(reportGroupName, (simulationData) => {
                if(reportEventsVersionRef.current !== reportEventsVersion) {
                    return; // guard against concurrency with older versions
                }

                updateReportData(undefined);

                let { state } = simulationData;
                if(state == "completed") {
                    simulationInfoPromise.then(({simulationId}) => {
                        let { frameCount, computeJobHash, computeJobSerial } = simulationData;
                        let frameId = getFrameId({
                            frameIndex: frameCount - 1, // pick last frame for now
                            reportName,
                            simulationId,
                            computeJobHash,
                            computeJobSerial,
                            appName,
                            hookedDependendies: hookedFrameIdDependencies
                        })

                        getSimulationFrame(frameId).then(simulationData => {
                            updateReportData(simulationData);
                        });
                    })
                }
            })
        })

        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        let panelController = useContext(ContextPanelController);

        useEffect(() => {
            panelController.setShown(shown && !!reportData);
        }, [shown, !!reportData])

        let VisualComponent = reportData ? layoutElement.component : undefined;

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {VisualComponent && shown && <VisualComponent key={reportEventsVersionRef.current} config={reportLayout} simulationData={reportData}></VisualComponent>}
            </>
        )
    }
}

export class SimulationStartLayout extends View {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props) => {
        let { config } = props;
        let { reportGroupName } = config;

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

            reportEventManager.onReportData(reportGroupName, (simulationData) => {
                if(simulationPollingVersionRef.current === pollingVersion) {
                    updateLastSimulationData(simulationData);
                }
            })

            simulationInfoPromise.then(({simulationId}) => {
                reportEventManager.startReport({
                    appName,
                    models: modelsWrapper.getModels(store.getState()),
                    simulationId,
                    report: reportGroupName
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
                    report: reportGroupName
                })
            })   
        }

        let endSimulationButton = <Button variant="primary" onClick={endSimulation}>End Simulation</Button>;
        let startSimulationButton = <Button variant="primary" onClick={startSimulation}>Start Simulation</Button>

        if(lastSimulationData) {
            let { state } = lastSimulationData;

            let getStateBasedElement = (state) => {
                let elapsedTimeSeconds = Math.ceil(((new Date()) - lastSimulationStartTime) / 1000)
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
                        
                        return (    
                            <Stack gap={2}>
                                <span>{'Simulation Completed'}</span>
                                <span>{`Elapsed time: ${elapsedTimeSeconds} ${'second' + (elapsedTimeSeconds !== 1 ? 's' : '')}`}</span>
                                {startSimulationButton}
                            </Stack>
                        )
                    case 'error':
                        return (    
                            <Stack gap={2}>
                                <span>{'Simulation Error'}</span>
                                <span>{`Elapsed time: ${elapsedTimeSeconds} ${'second' + (elapsedTimeSeconds !== 1 ? 's' : '')}`}</span>
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
