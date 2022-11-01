import { useRef } from 'react';

class Stopwatch {
    constructor(stopwatchDataRef) {
        this.times = stopwatchDataRef.current;
    }

    getElapsedSeconds() {
        if(this.times.startTime === undefined) {
            throw new Error("cannot get elapsed time from stopwatch that has not been started");
        }

        if(this.times.endTime === undefined) {
            throw new Error("cannot get elapsed time from stopwatch that has not been ended");
        }

        return (this.times.endTime - this.times.startTime) / 1000;
    }

    start() {
        if(this.times.endTime !== undefined) {
            throw new Error("connect start stopwatch that has already been started, reset it first");
        }

        this.times.startTime = new Date();
    }

    stop() {
        if(this.times.startTime === undefined) {
            throw new Error("cannot stop stopwatch before it has been started");
        }

        this.times.endTime = new Date();
    }

    reset() {
        this.times.startTime = undefined;
        this.times.endTime = undefined;
    }

    isComplete() {
        return this.times.startTime !== undefined && this.times.endTime !== undefined;
    }
}

export function useStopwatch() {
    let stopwatchData = useRef({
        startTime: undefined,
        endTime: undefined
    })

    return new Stopwatch(stopwatchData);
}
