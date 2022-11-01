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
import { useStopwatch } from "../hook/stopwatch";
import { AnimationReader } from "../data/report";
import { useShown, ValueSelector } from "../hook/shown";

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
                pollRunReport({
                    appName,
                    models,
                    simulationId,
                    report: report,
                    pollInterval: 500,
                    forceRun: false,
                    callback: (simulationData) => {
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

export class ManualRunReportLayout extends View {
    getFormDependencies = (config) => {
        let { reportLayout } = config;
        let layoutElement = this.layoutsWrapper.getLayoutForConfig(reportLayout);
        return layoutElement.getFormDependencies();
    }

    component = (props) => {
        let { config } = props;
        let { reportName, reportGroupName, reportLayout, frameIdFields, shown: shownConfig, frameCountFieldName } = config;
        
        let reportEventManager = useContext(ContextReportEventManager);
        let schema = useContext(ContextSchema);
        let modelsWrapper = useContext(ContextModelsWrapper);
        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);
        let appName = useContext(ContextAppName);
        let panelController = useContext(ContextPanelController);

        let reportEventsVersionRef = useRef(uuidv4())

        let shown = useShown(shownConfig, true, modelsWrapper, ValueSelector.Models);

        let frameIdDependencies = frameIdFields.map(f => new Dependency(f));

        let frameIdDependencyGroup = new HookedDependencyGroup({ 
            dependencies: frameIdDependencies,
            modelsWrapper,
            schemaModels: schema.models
        })

        let hookedFrameIdDependencies = frameIdDependencies.map(frameIdDependencyGroup.getHookedDependency);

        let [animationReader, updateAnimationReader] = useState(undefined);

        useEffect(() => {
            panelController.setShown(false);
        }, [0])

        useEffect(() => {
            let reportEventsVersion = uuidv4();
            reportEventsVersionRef.current = reportEventsVersion;
            
            reportEventManager.onReportData(reportGroupName, (simulationData) => {
                if(reportEventsVersionRef.current !== reportEventsVersion) {
                    return; // guard against concurrency with older versions
                }

                let { state } = simulationData;
                if(state == "completed") {
                    simulationInfoPromise.then(({simulationId}) => {
                        let { computeJobHash, computeJobSerial } = simulationData;
                        let frameCount = !!frameCountFieldName ? simulationData[frameCountFieldName] : 1;
                        let animationReader = new AnimationReader({
                            reportName,
                            simulationId,
                            appName,
                            computeJobSerial,
                            computeJobHash,
                            hookedFrameIdFields: hookedFrameIdDependencies,
                            frameCount
                        })
                        updateAnimationReader(animationReader);
                    })
                }
            })
        })

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {reportLayout && animationReader && <ReportAnimationController shown={shown} reportLayoutConfig={reportLayout} animationReader={animationReader}></ReportAnimationController>}
            </>
        )
    }
}

export function ReportAnimationController(props) {
    let { animationReader, reportLayoutConfig, shown } = props;
    let layoutsWrapper = useContext(ContextLayouts);
    let layoutElement = layoutsWrapper.getLayoutForConfig(reportLayoutConfig);

    let panelController = useContext(ContextPanelController);

    let [currentReportData, updateCurrentReportData] = useState(undefined);

    let reportDataCallback = (simulationData) => updateCurrentReportData(simulationData);
    let presentationIntervalMs = 1000;

    useEffect(() => {
        if(currentReportData === undefined) {
            animationReader.getNextFrame().then(reportDataCallback);
        }
    }, [0])

    useEffect(() => {
        let s = shown && !!currentReportData;
        panelController.setShown(s);
    }, [shown, !!currentReportData])

    let animationControlButtons = (
        <div className="d-flex flex-row justify-content-center w-100">
            <Button disabled={!animationReader.hasPreviousFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.seekBeginning();
                animationReader.getNextFrame().then(reportDataCallback);
            }}>
                <FontAwesomeIcon icon={Icon.faBackward}></FontAwesomeIcon>
            </Button>
            <Button disabled={!animationReader.hasPreviousFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.getPreviousFrame().then(reportDataCallback)
            }}>
                <FontAwesomeIcon icon={Icon.faBackwardStep}></FontAwesomeIcon>
            </Button>
            <Button disabled={!animationReader.hasNextFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.beginPresentation('forward', presentationIntervalMs, reportDataCallback)
            }}>
                <FontAwesomeIcon icon={Icon.faPlay}></FontAwesomeIcon>
            </Button>
            <Button disabled={!animationReader.hasNextFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.getNextFrame().then(reportDataCallback)
            }}>
                <FontAwesomeIcon icon={Icon.faForwardStep}></FontAwesomeIcon>
            </Button>
            <Button disabled={!animationReader.hasNextFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.seekEnd();
                animationReader.getNextFrame().then(reportDataCallback);
            }}>
                <FontAwesomeIcon icon={Icon.faForward}></FontAwesomeIcon>
            </Button>
        </div>
    )
    
    let LayoutComponent = layoutElement ? layoutElement.component : undefined;

    return (
        <>
            {
                LayoutComponent && shown && currentReportData && (
                    <>
                        <LayoutComponent config={reportLayoutConfig} simulationData={currentReportData}/>
                        {animationReader.getFrameCount() > 1 && animationControlButtons}
                    </>
                )
            }
        </>
    )
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
        let stopwatch = useStopwatch();

        let simulationPollingVersionRef = useRef(uuidv4())

        let startSimulation = () => {
            updateLastSimulationData(undefined);
            stopwatch.reset();
            stopwatch.start();
            let pollingVersion = uuidv4();
            simulationPollingVersionRef.current = pollingVersion;

            reportEventManager.onReportData(reportGroupName, (simulationData) => {
                if(simulationPollingVersionRef.current === pollingVersion) {
                    updateLastSimulationData(simulationData);
                    stopwatch.stop();
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
            debugger;
            updateLastSimulationData(undefined);
            stopwatch.reset();
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
            let elapsedTimeSeconds = stopwatch.isComplete() ? Math.ceil(stopwatch.getElapsedSeconds()) : undefined;
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
