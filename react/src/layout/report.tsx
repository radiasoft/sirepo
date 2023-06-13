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
import React from "react";
import { CPanelController } from "../data/panel";
import { LAYOUTS } from "./layouts";
import { CAppName, CSchema } from "../data/appwrapper";
import { SchemaLayout } from "../utility/schema";
import { CRouteHelper } from "../utility/route";
import { ModelState } from "../store/models";
import { useShown } from "../hook/shown";
import { CHandleFactory, DependencyReader } from "../data/handle";
import { StoreTypes, ValueSelectors } from "../data/data";
import { interpolate, InterpolationBase } from "../utility/string";
import { useSimulationInfo } from "../hook/simulationInfo";


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

    component = (props: LayoutProps<{}>) => {
        let { dependencies } = this.config;

        let appName = useContext(CAppName);
        let schema = useContext(CSchema);
        let store = useStore();
        let handleFactory = useContext(CHandleFactory);
        let simulationInfo = useSimulationInfo(handleFactory);
        let routeHelper = useContext(CRouteHelper);
        let report = interpolate(this.config.report).withDependencies(handleFactory, StoreTypes.Models).raw();

        let reportDependencies = dependencies.map(dependencyString => new Dependency(dependencyString));
        let dependentValues = new DependencyReader(reportDependencies, StoreTypes.Models, schema).hook();
        let [simulationData, updateSimulationData] = useState(undefined);

        let simulationPollingVersionRef = useRef(uuidv4())
        //let model = useModelValue(report, StoreTypes.Models);
        let model = handleFactory.createModelHandle(report, StoreTypes.Models).hook().value;

        useEffect(() => {
            updateSimulationData(undefined);
            let { simulationId } = simulationInfo;
            pollRunReport(routeHelper, {
                appName,
                models: store.getState()[StoreTypes.Models.name],
                simulationId,
                report: report,
                forceRun: false,
                callback: (simulationData) => {
                    updateSimulationData(simulationData);
                }
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

export function useAnimationReader(reportName: string, reportGroupName: string, frameIdFields: string[]) {
    let panelController = useContext(CPanelController);
    let [animationReader, updateAnimationReader] = useState<AnimationReader>(undefined);
    useEffect(() => {
        let s = animationReader && animationReader.frameCount > 0;
        if (panelController) {
            panelController.setShown(s);
        }
    }, [animationReader?.frameCount])
    let handleFactory = useContext(CHandleFactory);
    let simulationInfo = useSimulationInfo(handleFactory);
    let reportEventManager = useContext(CReportEventManager);
    let appName = useContext(CAppName);
    let routeHelper = useContext(CRouteHelper);
    let reportEventsVersionRef = useRef(uuidv4())
    let frameIdHandles = frameIdFields.map(f => new Dependency(f)).map(d => handleFactory.createHandle(d, StoreTypes.Models).hook());

    function reportStatus(reportName: string, simulationData: ResponseHasState) {
        if (simulationData.reports) {
            for (const r of simulationData.reports) {
                if (r.modelName === reportName) {
                    return {
                        frameCount: r.frameCount !== undefined ? r.frameCount : (r.lastUpdateTime || 0),
                        hasAnimationControls: ! r.lastUpdateTime,
                    };
                }
            }
        } else if(simulationData.outputInfo) {
            let frameCount = (simulationData.outputInfo as any[]).find(o => o.modelKey === reportName).pageCount
            return {
                frameCount,
                hasAnimationControls: frameCount > 1
            }
        }
        return {
            frameCount: 0,
            hasAnimationControls: false,
        };
    }

    useEffect(() => {
        reportEventManager.addListener(reportEventsVersionRef.current, reportGroupName, {
            onStart: () => {
                updateAnimationReader(undefined);
            },
            onReportData: (simulationData: ResponseHasState) => {
                console.log("onData");
                let { simulationId } = simulationInfo
                let { computeJobHash, computeJobSerial } = simulationData;
                const s = reportStatus(reportName, simulationData);
                if (!animationReader || s.frameCount !== animationReader?.frameCount) {
                    console.log("frameCount", s.frameCount);
                    if (s.frameCount > 0) {
                        let newAnimationReader = new AnimationReader(routeHelper, {
                            reportName,
                            simulationId,
                            appName,
                            computeJobSerial,
                            computeJobHash,
                            frameIdValues: frameIdHandles.map(h => ValueSelectors.Models(h.value)),
                            frameCount: s.frameCount,
                            hasAnimationControls: s.hasAnimationControls,
                        });
                        updateAnimationReader(newAnimationReader);
                    } else {
                        updateAnimationReader(undefined);
                    }
                }
            }
        })
        return () => {
            reportEventManager.clearListenersForKey(reportEventsVersionRef.current)
        };
    })
    return animationReader;
}

export type ManualRunReportConfig = {
    reportLayout: SchemaLayout,
    reportName: string,
    reportGroupName: string,
    frameIdFields: string[],
    shown: string
}

export class ManualRunReportLayout extends Layout<ManualRunReportConfig, {}> {
    reportLayout: ReportVisual;

    constructor(config: ManualRunReportConfig) {
        super(config);

        this.reportLayout = LAYOUTS.getLayoutForSchema(config.reportLayout) as ReportVisual;
    }

    component = (props: LayoutProps<{}>) => {
        let { reportGroupName, frameIdFields } = this.config;
        let handleFactory = useContext(CHandleFactory);
        let reportName = interpolate(this.config.reportName).withDependencies(handleFactory, StoreTypes.Models).raw();
        let showAnimationController = 'showAnimationController' in this.config
                                    ? !!this.config.showAnimationController
                                    : true;
        let shown = useShown(this.config.shown, true, StoreTypes.Models);
        //let reportModel = useModelValue(reportName, StoreTypes.Models);
        let reportModel = handleFactory.createModelHandle(reportName, StoreTypes.Models).hook().value;
        let animationReader = useAnimationReader(reportName, reportGroupName, frameIdFields);
        console.log("shown", shown);
        console.log("reportLayout", this.reportLayout);
        console.log("animationReader", animationReader);
        return (
            <>
                {shown && this.reportLayout &&
                animationReader &&
                <ReportAnimationController animationReader={animationReader} showAnimationController={showAnimationController} currentFrameIndex={props.currentFrameIndex}>
                    {
                        (currentFrame: SimulationFrame) => {
                            let LayoutComponent = this.reportLayout.component;
                            let canShowReport = this.reportLayout.canShow(currentFrame?.data);
                            let reportLayoutConfig = this.reportLayout.getConfigFromApiResponse(currentFrame?.data);
                            return (
                                <>
                                {
                                    canShowReport && <LayoutComponent data={reportLayoutConfig} model={reportModel}/>
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

function AnimationControlButtons(props: { animationReader: AnimationReader, reportDataCallback: (data: SimulationFrame) => void }) {
    const { animationReader, reportDataCallback } = props;
    const presentationIntervalMs = 1000;
    return (
        <div className="d-flex flex-row justify-content-center w-100 gap-1 mt-3">
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
    );
}

export function ReportAnimationController(props: { animationReader: AnimationReader, children: (data: SimulationFrame) => ReactElement, showAnimationController: boolean, currentFrameIndex: number }) {
    let { animationReader, showAnimationController, currentFrameIndex } = props;

    let [currentFrame, updateCurrentFrame] = useState<SimulationFrame>(undefined);
    let reportDataCallback = (simulationData) => updateCurrentFrame(simulationData);
    useEffect(() => {
        animationReader.seekEnd();
        animationReader.getNextFrame().then(reportDataCallback);
    }, [animationReader?.frameCount])
    useEffect(() => {
        if (currentFrameIndex !== undefined) {
            animationReader.cancelPresentations();
            animationReader.getFrame(currentFrameIndex).then(reportDataCallback);
        }
    }, [currentFrameIndex]);
    return (
        <>
        {
            currentFrame && (
                <>
                {props.children(currentFrame)}
                {
                    showAnimationController
                    && animationReader.getFrameCount() > 1
                    && animationReader.hasAnimationControls
                    && <AnimationControlButtons
                        animationReader={animationReader}
                        reportDataCallback={reportDataCallback}
                    />
                }
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
    
    component = (props: LayoutProps<{}>) => {
        let { reportGroupName } = this.config;

        let reportEventManager = useContext(CReportEventManager);
        let appName = useContext(CAppName);
        let routeHelper = useContext(CRouteHelper);
        let schema = useContext(CSchema);
        let handleFactory = useContext(CHandleFactory);
        let simulationInfo = useSimulationInfo(handleFactory);

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
            let { simulationId } = simulationInfo;
            reportEventManager.getRunStatusOnce({
                appName,
                models: store.getState()[StoreTypes.Models.name],
                simulationId,
                report: reportGroupName
            }).then(simulationData => {
                // catch running reports after page refresh
                updateSimState(simulationData);
                if (simulationData.state === 'running') {
                    listenForReportData();
                    reportEventManager.pollRunStatus({
                        appName,
                        models: store.getState()[StoreTypes.Models.name],
                        simulationId,
                        report: reportGroupName
                    })
                }
                if (simulationData.elapsedTime) {
                    stopwatch.setElapsedSeconds(simulationData.elapsedTime);
                }
            })

            return () => reportEventManager.clearListenersForKey(simulationPollingVersionRef.current);
        }, []);


        let startSimulation = () => {
            listenForReportData();

            let { simulationId } = simulationInfo; 
            reportEventManager.startReport({
                appName,
                models: store.getState()[StoreTypes.Models.name],
                simulationId,
                report: reportGroupName
            })
        }

        let endSimulation = () => {
            updateSimState(undefined);
            stopwatch.reset();
            simulationPollingVersionRef.current = uuidv4();

            let { simulationId } = simulationInfo;
            cancelReport(routeHelper, {
                appName,
                models: store.getState()[StoreTypes.Models.name],
                simulationId,
                report: reportGroupName
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
                                { simState.alert && <div className="card card-body bg-light">
                                    <pre>{simState.alert}</pre>
                                  </div>
                                }
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
                                <div className="card card-body bg-light">
                                    <pre>{simState.alert || simState.error}</pre>
                                </div>
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
