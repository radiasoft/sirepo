import { useContext, useState, useRef, useEffect } from "react";
import { Dependency } from "../data/dependency";
import { LayoutProps, Layout } from "./layout";
import { cancelReport, getSimulationFrame, pollRunReport } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';
import { useStore } from "react-redux";
import { ProgressBar, Stack, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { useStopwatch } from "../hook/stopwatch";
import { AnimationReader, CReportEventManager } from "../data/report";
import { useShown } from "../hook/shown";
import React from "react";
import { CPanelController } from "../data/panel";
import { LAYOUTS } from "./layouts";
import { CModelsWrapper, getModelValues } from "../data/wrapper";
import { ModelsAccessor } from "../data/accessor";
import { CFormController } from "../data/formController";
import { CAppName, CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { ValueSelectors } from "../hook/string";
import { SchemaView } from "../utility/schema";


export type ReportVisualProps<L> = { data: L };
export abstract class ReportVisual<C = unknown, P = unknown, A = unknown, L = unknown> extends Layout<C, P & ReportVisualProps<L>> {
    abstract getConfigFromApiResponse(apiReponse: A): L;
    abstract canShow(apiResponse: A): boolean;
}

export type AutoRunReportConfig = {
    reportLayout: SchemaView,
    report: string,
    dependencies: string[]
}

export class AutoRunReportLayout extends Layout<AutoRunReportConfig, {}> {
    reportLayout: ReportVisual;
    
    constructor(config: AutoRunReportConfig) {
        super(config);

        this.reportLayout = LAYOUTS.getLayoutForSchemaView(config.reportLayout) as ReportVisual;
    }

    getFormDependencies = () => {
        return this.reportLayout.getFormDependencies();
    }

    component = (props: LayoutProps<{}>) => {
        let { report, reportLayout, dependencies } = this.config;

        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let appName = useContext(CAppName);
        let modelsWrapper = useContext(CModelsWrapper);
        let formController = useContext(CFormController);

        let reportDependencies = dependencies.map(dependencyString => new Dependency(dependencyString));

        let dependentValuesAccessor = new ModelsAccessor(modelsWrapper, [...formController.getDependencies(), ...reportDependencies]);
        let dependentValues = dependentValuesAccessor.getValues().map(dv => dv.value);

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

        let reportVisualConfig = this.reportLayout.getConfigFromApiResponse(simulationData);
        let canShow = this.reportLayout.canShow(simulationData);
        let LayoutComponent = this.reportLayout.component;

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {canShow && <LayoutComponent key={simulationPollingVersionRef.current} data={reportVisualConfig}/>}
                {!canShow && <ProgressBar animated now={100}/>}
            </>
        )
    }
}

export type ManualRunReportConfig = {
    reportLayout: SchemaView,
    reportName: string,
    reportGroupName: string,
    frameIdFields: string[],
    shown: string,
    frameCountFieldName: string
}

export class ManualRunReportLayout extends Layout<ManualRunReportConfig, {}> {
    reportLayout: ReportVisual;
    
    constructor(config: ManualRunReportConfig) {
        super(config);

        this.reportLayout = LAYOUTS.getLayoutForSchemaView(config.reportLayout) as ReportVisual;
    }

    getFormDependencies = () => {
        return this.reportLayout.getFormDependencies();
    }

    component = (props: LayoutProps<{}>) => {
        let { reportName, reportGroupName, frameIdFields, shown: shownConfig, frameCountFieldName } = this.config;
        
        let reportEventManager = useContext(CReportEventManager);
        let modelsWrapper = useContext(CModelsWrapper);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let appName = useContext(CAppName);
        let panelController = useContext(CPanelController);

        let reportEventsVersionRef = useRef(uuidv4())

        let shown = useShown(shownConfig, true, modelsWrapper, ValueSelectors.Models);

        let frameIdDependencies = frameIdFields.map(f => new Dependency(f));

        let frameIdAccessor = new ModelsAccessor(modelsWrapper, frameIdDependencies);

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
                            frameIdValues: frameIdAccessor.getValues().map(fv => fv.value),
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
                {this.reportLayout && animationReader && <ReportAnimationController shown={shown} reportLayout={this.reportLayout} animationReader={animationReader}></ReportAnimationController>}
            </>
        )
    }
}

export function ReportAnimationController(props: { animationReader: AnimationReader, reportLayout: ReportVisual, shown: boolean}) {
    let { animationReader, reportLayout, shown } = props;

    let panelController = useContext(CPanelController);

    let [currentReportData, updateCurrentReportData] = useState(undefined);

    let reportDataCallback = (simulationData) => updateCurrentReportData(simulationData);
    let presentationIntervalMs = 1000;

    useEffect(() => {
        if(currentReportData === undefined) {
            animationReader.getNextFrame().then(reportDataCallback);
        }
    }, [0])

    useEffect(() => {
        let s = shown && !!currentReportData && reportLayout.canShow(currentReportData);
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

    let LayoutComponent = reportLayout.component;
    let canShowReport = reportLayout.canShow(currentReportData);
    let reportLayoutConfig = reportLayout.getConfigFromApiResponse(currentReportData);

    return (
        <>
            {
                canShowReport && shown && currentReportData && (
                    <>
                        <LayoutComponent data={reportLayoutConfig}/>
                        {animationReader.getFrameCount() > 1 && animationControlButtons}
                    </>
                )
            }
        </>
    )
}

export type SimulationStartConfig = {
    reportGroupName: string
}

export class SimulationStartLayout extends Layout<SimulationStartConfig, {}> {
    getFormDependencies = () => {
        return [];
    }

    component = (props: LayoutProps<{}>) => {
        let { reportGroupName } = this.config;

        let reportEventManager = useContext(CReportEventManager);
        let appName = useContext(CAppName);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let modelsWrapper = useContext(CModelsWrapper);
        let schema = useContext(CSchema);
        let modelNames = Object.keys(schema.models);

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
                    models: getModelValues(modelNames, modelsWrapper, store.getState()),
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
                    models: getModelValues(modelNames, modelsWrapper, store.getState()),
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
                throw new Error("state was not handled for run-status: " + state);
            }

            return (
                <>{getStateBasedElement(state)}</>
            )
        }
        return <>{startSimulationButton}</>
    }
}
