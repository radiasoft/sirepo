import { useContext, useState, useRef, useEffect, ReactElement } from "react";
import { Dependency } from "../data/dependency";
import { LayoutProps, Layout } from "./layout";
import { cancelReport, pollRunReport, ResponseHasState } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';
import { useStore } from "react-redux";
import { ProgressBar, Stack, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { useStopwatch } from "../hook/stopwatch";
import { AnimationReader, CReportEventManager, SimulationFrame } from "../data/report";
import { useShown } from "../hook/shown";
import React from "react";
import { CPanelController } from "../data/panel";
import { LAYOUTS } from "./layouts";
import { CModelsWrapper, getModelValues } from "../data/wrapper";
import { ModelsAccessor } from "../data/accessor";
import { CFormController } from "../data/formController";
import { CAppName, CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { ValueSelectors } from "../hook/string";
import { SchemaLayout } from "../utility/schema";
import { CRouteHelper } from "../utility/route";
import { ModelState } from "../store/models";


export type ReportVisualProps<L> = { data: L, model: ModelState };
export abstract class ReportVisual<C = unknown, P = unknown, A = unknown, L = unknown> extends Layout<C, P & ReportVisualProps<L>> {
    abstract getConfigFromApiResponse(apiReponse: A): L;
    abstract canShow(apiResponse: A): boolean;
}

export type AutoRunReportConfig = {
    reportLayout: SchemaLayout,
    report: string,
    dependencies: string[]
}

export class AutoRunReportLayout extends Layout<AutoRunReportConfig, {}> {
    reportLayout: ReportVisual;

    constructor(config: AutoRunReportConfig) {
        super(config);

        this.reportLayout = LAYOUTS.getLayoutForSchema(config.reportLayout) as ReportVisual;
    }

    getFormDependencies = () => {
        return this.reportLayout.getFormDependencies();
    }

    component = (props: LayoutProps<{}>) => {
        let { report, dependencies } = this.config;

        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let appName = useContext(CAppName);
        let routeHelper = useContext(CRouteHelper);
        let modelsWrapper = useContext(CModelsWrapper);
        let formController = useContext(CFormController);

        let reportDependencies = dependencies.map(dependencyString => new Dependency(dependencyString));

        let dependentValuesAccessor = new ModelsAccessor(modelsWrapper, [...formController.getDependencies(), ...reportDependencies]);
        let dependentValues = dependentValuesAccessor.getValues().map(dv => dv.value);

        let [simulationData, updateSimulationData] = useState(undefined);

        let simulationPollingVersionRef = useRef(uuidv4())
        let [model, updateModel] = useState(undefined);

        useEffect(() => {
            updateSimulationData(undefined);
            let pollingVersion = uuidv4();
            simulationPollingVersionRef.current = pollingVersion;
            simulationInfoPromise.then(({ models, simulationId, simulationType, version }) => {
                updateModel(models[report]);
                pollRunReport(routeHelper, {
                    appName,
                    models,
                    simulationId,
                    report: report,
                    forceRun: false,
                    callback: (simulationData) => {
                        // guard concurrency
                        if(simulationPollingVersionRef.current === pollingVersion) {
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
                {canShow && <LayoutComponent key={simulationPollingVersionRef.current} data={reportVisualConfig} model={model} />}
                {!canShow && <ProgressBar animated now={100}/>}
            </>
        )
    }
}

export type ManualRunReportConfig = {
    reportLayout: SchemaLayout,
    reportName: string,
    reportGroupName: string,
    frameIdFields: string[],
    shown: string,
}

export class ManualRunReportLayout extends Layout<ManualRunReportConfig, {}> {
    reportLayout: ReportVisual;

    constructor(config: ManualRunReportConfig) {
        super(config);

        this.reportLayout = LAYOUTS.getLayoutForSchema(config.reportLayout) as ReportVisual;
    }

    getFormDependencies = () => {
        return this.reportLayout.getFormDependencies();
    }

   //TODO(pjm): private method naming convention?
    _reportStatus(reportName, simulationData) {
        if (simulationData.reports) {
            for (const r of simulationData.reports) {
                if (r.modelName === reportName) {
                    return {
                        frameCount: r.frameCount || r.lastUpdateTime || 0,
                        hasAnimationControls: ! r.lastUpdateTime,
                    };
                }
            }
        }
        return {
            frameCount: 0,
            hasAnimationControls: false,
        };
    }

    component = (props: LayoutProps<{}>) => {
        let { reportName, reportGroupName, frameIdFields, shown: shownConfig } = this.config;

        let reportEventManager = useContext(CReportEventManager);
        let modelsWrapper = useContext(CModelsWrapper);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let appName = useContext(CAppName);
        let routeHelper = useContext(CRouteHelper);
        let panelController = useContext(CPanelController);

        let reportEventsVersionRef = useRef(uuidv4())

        let shown = useShown(shownConfig, true, modelsWrapper, ValueSelectors.Models);

        let frameIdDependencies = frameIdFields.map(f => new Dependency(f));

        let frameIdAccessor = new ModelsAccessor(modelsWrapper, frameIdDependencies);

        let [animationReader, updateAnimationReader] = useState<AnimationReader>(undefined);
        let [model, updateModel] = useState(undefined);

        useEffect(() => {
            let s = animationReader && animationReader.frameCount > 0 && shown;
            panelController.setShown(s);
        }, [shown, animationReader?.frameCount])

        useEffect(() => {
            reportEventManager.addListener(reportEventsVersionRef.current, reportGroupName, {
                onStart: () => {
                    updateAnimationReader(undefined);
                    panelController.setShown(false);
                },
                onReportData: (simulationData: ResponseHasState) => {
                    simulationInfoPromise.then(({models, simulationId}) => {
                        let { computeJobHash, computeJobSerial } = simulationData;
                        const s = this._reportStatus(reportName, simulationData);
                        if (!animationReader || s.frameCount !== animationReader?.frameCount) {
                            if (s.frameCount > 0) {
                                let newAnimationReader = new AnimationReader(routeHelper, {
                                    reportName,
                                    simulationId,
                                    appName,
                                    computeJobSerial,
                                    computeJobHash,
                                    frameIdValues: frameIdAccessor.getValues().map(fv => fv.value),
                                    frameCount: s.frameCount,
                                    hasAnimationControls: s.hasAnimationControls,
                                });
                                updateModel(models[reportName]) // TODO: needs safe access
                                updateAnimationReader(newAnimationReader);
                            } else {
                                updateAnimationReader(undefined);
                            }
                        }
                    })
                }
            })
            return () => {
                reportEventManager.clearListenersForKey(reportEventsVersionRef.current)
            };
        })

        // set the key as the key for the latest request sent to make a brand new report component for each new request data
        return (
            <>
                {this.reportLayout && 
                animationReader && 
                <ReportAnimationController animationReader={animationReader}>
                    {
                        (data) => {
                            let LayoutComponent = this.reportLayout.component;
                            let canShowReport = this.reportLayout.canShow(data);
                            let reportLayoutConfig = this.reportLayout.getConfigFromApiResponse(data);
                            return (
                                <>
                                {
                                    canShowReport && <LayoutComponent data={reportLayoutConfig} model={model}/>
                                }
                                </>
                            )
                        }
                    }
                </ReportAnimationController>
                }
            </>
        )
    }
}

export function ReportAnimationController(props: { animationReader: AnimationReader, children: (data: unknown) => ReactElement }) {
    let { animationReader } = props;
    let [currentFrame, updateCurrentFrame] = useState<SimulationFrame>(undefined);
    let reportDataCallback = (simulationData) => updateCurrentFrame(simulationData);
    let presentationIntervalMs = 1000;

    useEffect(() => {
        animationReader.seekEnd();
        animationReader.getNextFrame().then(reportDataCallback);
    }, [animationReader?.frameCount])

    let animationControlButtons = (
        <div className="d-flex flex-row justify-content-center w-100 gap-1">
            <Button variant="light" disabled={!animationReader.hasPreviousFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.seekBeginning();
                animationReader.getNextFrame().then(reportDataCallback);
            }}>
                <FontAwesomeIcon icon={Icon.faBackward}></FontAwesomeIcon>
            </Button>
            <Button variant="light" disabled={!animationReader.hasPreviousFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.getPreviousFrame().then(reportDataCallback)
            }}>
                <FontAwesomeIcon icon={Icon.faBackwardStep}></FontAwesomeIcon>
            </Button>
            <Button variant="light" disabled={!animationReader.hasNextFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.beginPresentation('forward', presentationIntervalMs, reportDataCallback)
            }}>
                <FontAwesomeIcon icon={Icon.faPlay}></FontAwesomeIcon>
            </Button>
            <Button variant="light" disabled={!animationReader.hasNextFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.getNextFrame().then(reportDataCallback)
            }}>
                <FontAwesomeIcon icon={Icon.faForwardStep}></FontAwesomeIcon>
            </Button>
            <Button variant="light" disabled={!animationReader.hasNextFrame()} onClick={() => {
                animationReader.cancelPresentations();
                animationReader.seekEnd();
                animationReader.getNextFrame().then(reportDataCallback);
            }}>
                <FontAwesomeIcon icon={Icon.faForward}></FontAwesomeIcon>
            </Button>
        </div>
    )

    

    return (
        <>
            {
                currentFrame && (
                    <>
                        {props.children(currentFrame?.data)}
                        {animationReader.getFrameCount() > 1 && animationReader.hasAnimationControls && animationControlButtons}
                    </>
                )
            }
        </>
    )
}

export type SimulationStartConfig = {
    reportGroupName: string,
    items: SchemaLayout[]
}

export class SimulationStartLayout extends Layout<SimulationStartConfig, {}> {
    childLayouts: Layout[];

    constructor(config: SimulationStartConfig) {
        super(config);

        this.childLayouts = (config.items || []).map(LAYOUTS.getLayoutForSchema);
    }

    getFormDependencies = () => {
        return (this.childLayouts || []).flatMap(v => v.getFormDependencies());
    }

    component = (props: LayoutProps<{}>) => {
        let { reportGroupName } = this.config;

        let reportEventManager = useContext(CReportEventManager);
        let appName = useContext(CAppName);
        let routeHelper = useContext(CRouteHelper);
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let modelsWrapper = useContext(CModelsWrapper);
        let schema = useContext(CSchema);
        let modelNames = Object.keys(schema.models);

        let store = useStore();


        let [lastSimState, updateSimState] = useState<ResponseHasState>(undefined);
        let stopwatch = useStopwatch();

        let simulationPollingVersionRef = useRef(uuidv4())

        let listenForReportData = () => {
            reportEventManager.addListener(simulationPollingVersionRef.current, reportGroupName, {
                onStart: () => {
                    updateSimState(undefined);
                    stopwatch.reset();
                    stopwatch.start();
                },
                onReportData: (simulationData: ResponseHasState) => {
                    updateSimState(simulationData);
                },
                onComplete: () => {
                    stopwatch.stop();
                }
            })
        }

        useEffect(() => {
            // recover from previous runs on server
            simulationInfoPromise.then(({simulationId}) => {
                let models = getModelValues(modelNames, modelsWrapper, store.getState());
                reportEventManager.getRunStatusOnce({
                    appName,
                    models,
                    simulationId,
                    report: reportGroupName
                }).then(simulationData => {
                    // catch running reports after page refresh
                    updateSimState(simulationData);
                    if (simulationData.state === 'running') {
                        listenForReportData();
                        reportEventManager.pollRunStatus({
                            appName,
                            models,
                            simulationId,
                            report: reportGroupName
                        })
                    }
                    if (simulationData.elapsedTime) {
                        stopwatch.setElapsedSeconds(simulationData.elapsedTime);
                    }
                })
            })

            return () => reportEventManager.clearListenersForKey(simulationPollingVersionRef.current);
        }, []);


        let startSimulation = () => {
            listenForReportData();

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
            updateSimState(undefined);
            stopwatch.reset();
            simulationPollingVersionRef.current = uuidv4();

            simulationInfoPromise.then(({simulationId}) => {
                cancelReport(routeHelper, {
                    appName,
                    models: getModelValues(modelNames, modelsWrapper, store.getState()),
                    simulationId,
                    report: reportGroupName
                })
            })
        }

        let endSimulationButton = <Button variant="primary" onClick={endSimulation}>End Simulation</Button>;
        let startSimulationButton = <Button variant="primary" onClick={startSimulation}>Start Simulation</Button>

        let children = this.childLayouts.map(l => {
            let Component = l.component;
            return <Component></Component>
        });

        if(lastSimState) {
            let getStateBasedElement = (simState: ResponseHasState) => {
                switch(simState.state) {
                    case 'pending':
                        return (
                            <Stack gap={2}>
                                <span><FontAwesomeIcon fixedWidth icon={Icon.faHourglass}/>{` Pending...`}</span>
                                <ProgressBar animated now={100}/>
                                {endSimulationButton}
                            </Stack>
                        )
                    case 'running':
                        return (
                            <Stack gap={2}>
                                <span>{`Running`}</span>
                                <span>{stopwatch.formatElapsedTime()}</span>
                                <ProgressBar animated now={Math.max((simState.percentComplete !== undefined && simState.percentComplete > 0) ? simState.percentComplete : 100, 5)}/>
                                {endSimulationButton}
                            </Stack>
                        )
                    case 'completed':
                        return (
                            <Stack gap={2}>
                                <span>{'Simulation Completed'}</span>
                                <span>{stopwatch.formatElapsedTime()}</span>
                                <div>{children}</div>
                                {startSimulationButton}
                            </Stack>
                        )
                    case 'canceled':
                        return (
                            <Stack gap={2}>
                                <span>{'Simulation Canceled'}</span>
                                <div>{children}</div>
                                {startSimulationButton}
                            </Stack>
                        )
                    case 'error':
                    case 'srException':
                        return (
                            <Stack gap={2}>
                                <span>{'Simulation Error'}</span>
                                <span>{stopwatch.formatElapsedTime()}</span>
                                <div>{children}</div>
                                {startSimulationButton}
                            </Stack>
                        )
                    case 'missing':
                        return <>{startSimulationButton}</>
                }
                throw new Error(`state was not handled for run-status: ${simState.state}`);
            }

            return (
                <>{getStateBasedElement(lastSimState)}</>
            )
        }
        return (<>
            <div>{children}</div>
            {startSimulationButton}
        </>)
    }
}
