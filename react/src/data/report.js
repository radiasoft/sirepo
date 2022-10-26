import { getSimulationFrame, pollRunReport } from "../utility/compute";
import { v4 as uuidv4 } from 'uuid';

export class ReportEventManager {
    constructor() {
        this.reportEventListeners = {};
    }

    onReportData = (report, callback) => {
        let reportListeners = this.reportEventListeners[report] || [];
        reportListeners.push(callback);
        this.reportEventListeners[report] = reportListeners;
    }

    startReport = ({
        appName,
        models,
        simulationId,
        report
    }) => {
        pollRunReport({
            appName,
            models,
            simulationId,
            report,
            pollInterval: 500,
            forceRun: true,
            callback: (simulationData) => {
                let reportListeners = this.reportEventListeners[report] || [];
                for(let reportListener of reportListeners) {
                    reportListener(simulationData);
                }
            }
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
    hookedDependencies
}) {
    let frameIdElements = [
        frameIndex,
        reportName,
        simulationId,
        appName,
        computeJobHash,
        computeJobSerial,
        ...((hookedDependencies || []).map(v => v.value))
    ]

    return frameIdElements.join('*');
}

// Note this accepts hookedFrameIdFields but provides no mechanism for updating them.
// This iterates all future frames assuming this data does not need to change/be current
export class AnimationReader {
    constructor({
        reportName,
        simulationId,
        appName,
        computeJobHash,
        computeJobSerial,
        hookedFrameIdFields,
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
            hookedDependencies: hookedFrameIdFields
        })

        this.presentationVersionNum = uuidv4();
    }

    cancelPresentations = () => {
        this.presentationVersionNum = uuidv4();
    }

    getFrame = (frameIndex) => {
        if(frameIndex < 0 || frameIndex >= this.frameCount) {
            throw new Error(`frame index out of bounds: ${frameIndex}, frame count was ${this.frameCount}`)
        }

        return getSimulationFrame(this.getFrameId(frameIndex));
    }

    getNextFrame = () => {
        return this.getFrame(this.nextFrameIndex++);
    }

    hasNextFrame = () => {
        return this.nextFrameIndex < this.frameCount;
    }

    hasPreviousFrame = () => {
        return this.nextFrameIndex - 2 >= 0;
    }

    getPreviousFrame = () => {
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

        if(direction == 'forward') {
            dir = 1;
        } else if(direction == 'backward') {
            dir = -1;
        } else {
            throw new Error(`invalid direction for presentation: ${direction}`);
        }

        let handlePresentationFrame = (simulationData) => {
            if(activePresentationVersion == this.presentationVersionNum) {
                callback(simulationData);
            }
        }

        let itFuncs = {
            hasNext: dir == 1 ? this.hasNextFrame : this.hasPreviousFrame,
            next: dir == 1 ? this.getNextFrame : this.getPreviousFrame
        }

        let presentationInterval = setInterval(() => {
            if(activePresentationVersion != this.presentationVersionNum) {
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
