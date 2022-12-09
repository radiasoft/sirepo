import { getSimulationFrame, pollRunReport, ResponseHasState, getRunStatusOnce } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';
import React from "react";
import { ModelStates } from "../store/models";
import { mapProperties } from "../utility/object";

export const CReportEventManager = React.createContext<ReportEventManager>(undefined);

export type ReportEventSubscriber = {
    /**
     * Called once for every simulationData received (including during completion)
     */
    onReportData?: (simulationData: ResponseHasState) => void;
    /**
     * Called once when reports are starting to be generated
     */
    onStart?: () => void;
    /**
     * Called once when reports are finished being generated
     */
    onComplete?: () => void;
}

type RunStatusParams = {
    appName: string,
    models: ModelStates,
    simulationId: string,
    report: string
}

export class ReportEventManager {
    reportEventListeners: {[reportName: string]: {[key: string]: ReportEventSubscriber}} = {}

    addListener = (key: string, reportName: string, listener: ReportEventSubscriber): void => {
        let reportListeners = this.reportEventListeners[reportName] || {};
        //reportListeners.push(callback);
        reportListeners[key] = listener;
        this.reportEventListeners[reportName] = reportListeners;
    }

    clearListenersForKey = (key: string) => {
        this.reportEventListeners = mapProperties(this.reportEventListeners, (_, listeners) => Object.fromEntries(Object.entries(listeners).filter(([k,]) => k !== key)));
    }

    getListenersForReport: (report: string) => ReportEventSubscriber[] = (report: string) => {
        return Object.entries(this.reportEventListeners[report] || {}).map(([, listener]) => listener);
    }

    handleSimulationData: (report: string, simulationData: ResponseHasState) => void = (report: string, simulationData: ResponseHasState) => {
        this.getListenersForReport(report).forEach(l => l.onReportData && l.onReportData(simulationData));
        if(simulationData.state === 'completed') {
            this.getListenersForReport(report).forEach(l => l.onComplete && l.onComplete());
        }
    }

    getRunStatusOnce: (params: RunStatusParams) => Promise<ResponseHasState> = ({
        appName,
        models,
        simulationId,
        report
    }) => {
        return getRunStatusOnce({
            appName,
            models,
            simulationId,
            report,
            forceRun: false
        }).then(d => {
            this.handleSimulationData(report, d)
            return d;
        })
    }

    pollRunStatus = ({
        appName,
        models,
        simulationId,
        report
    }: {
        appName: string,
        models: ModelStates,
        simulationId: string,
        report: string
    }) => {
        pollRunReport({
            appName,
            models,
            simulationId,
            report,
            forceRun: true,
            callback: (simulationData) => {
                this.handleSimulationData(report, simulationData);
            }
        })
    }

    startReport = ({
        appName,
        models,
        simulationId,
        report
    }: {
        appName: string,
        models: ModelStates,
        simulationId: string,
        report: string
    }) => {
        this.getListenersForReport(report).forEach(l => l.onStart && l.onStart());
        this.pollRunStatus({
            appName,
            models,
            simulationId,
            report
        })
    }
}

function getFrameId({
    frameIndex,
    reportName,
    simulationId,
    appName,
    computeJobHash,
    computeJobSerial,
    extraValues
}) {
    let frameIdElements = [
        frameIndex,
        reportName,
        simulationId,
        appName,
        computeJobHash,
        computeJobSerial,
        ...(extraValues || [])
    ]

    return frameIdElements.join('*');
}

export type SimulationFrame<T = unknown> = {
    index: number,
    data: T
}

// Note this accepts hookedFrameIdFields but provides no mechanism for updating them.
// This iterates all future frames assuming this data does not need to change/be current
export class AnimationReader {
    frameCount: number;
    nextFrameIndex: number;
    getFrameId: (frameIndex: number) => string;
    presentationVersionNum: string;

    constructor({
        reportName,
        simulationId,
        appName,
        computeJobHash,
        computeJobSerial,
        frameIdValues,
        frameCount
    }) {
        this.frameCount = frameCount;
        this.nextFrameIndex = 0;
        this.getFrameId = (frameIndex) => getFrameId({
            frameIndex,
            reportName,
            simulationId,
            appName,
            computeJobHash,
            computeJobSerial,
            extraValues: frameIdValues
        })

        this.presentationVersionNum = uuidv4();
    }

    cancelPresentations = () => {
        this.presentationVersionNum = uuidv4();
    }

    getFrame = (frameIndex): Promise<SimulationFrame> => {
        if(frameIndex < 0 || frameIndex >= this.frameCount) {
            throw new Error(`frame index out of bounds: ${frameIndex}, frame count was ${this.frameCount}`)
        }

        return getSimulationFrame(this.getFrameId(frameIndex)).then(data => {
            return {
                index: frameIndex,
                data
            }
        });
    }

    getNextFrame = (): Promise<SimulationFrame> => {
        return this.getFrame(this.nextFrameIndex++);
    }

    hasNextFrame = () => {
        return this.nextFrameIndex < this.frameCount;
    }

    hasPreviousFrame = () => {
        return this.nextFrameIndex - 2 >= 0;
    }

    getPreviousFrame = (): Promise<SimulationFrame> => {
        return this.getFrame((--this.nextFrameIndex) - 1);
    }

    getFrameCount = () => {
        return this.frameCount;
    }

    seekFrame = (frameIndex) => {
        this.nextFrameIndex = frameIndex;
    }

    seekBeginning = () => {
        this.seekFrame(0);
    }

    seekEnd = () => {
        this.seekFrame(this.frameCount - 1);
    }

    beginPresentation = (direction, interval, callback) => {
        let dir = undefined;

        let activePresentationVersion = this.presentationVersionNum;

        if(direction === 'forward') {
            dir = 1;
        } else if(direction === 'backward') {
            dir = -1;
        } else {
            throw new Error(`invalid direction for presentation: ${direction}`);
        }

        let handlePresentationFrame = (simulationData) => {
            if(activePresentationVersion === this.presentationVersionNum) {
                callback(simulationData);
            }
        }

        let itFuncs = {
            hasNext: dir === 1 ? this.hasNextFrame : this.hasPreviousFrame,
            next: dir === 1 ? this.getNextFrame : this.getPreviousFrame
        }

        let presentationInterval = setInterval(() => {
            if(activePresentationVersion !== this.presentationVersionNum) {
                clearInterval(presentationInterval);
                return;
            }

            if(itFuncs.hasNext()) {
                itFuncs.next().then(simulationData => handlePresentationFrame(simulationData));
            } else {
                clearInterval(presentationInterval);
            }
        }, interval)
    }
}
