import { RefObject, useRef } from 'react';

export type StopwatchData = {
    startTime: number,
    endTime: number
}

class Stopwatch {
    times: StopwatchData;

    constructor(stopwatchDataRef: RefObject<StopwatchData>) {
        this.times = stopwatchDataRef.current;
    }

    getElapsedSeconds() {
        if(this.times.startTime === undefined) {
            throw new Error("cannot get elapsed time from stopwatch that has not been started");
        }
        return ((this.times.endTime || new Date().valueOf()) - this.times.startTime) / 1000;
    }

    start() {
        if(this.times.endTime !== undefined) {
            throw new Error("connect start stopwatch that has already been started, reset it first");
        }

        this.times.startTime = new Date().valueOf();
    }

    stop() {
        if(this.times.startTime === undefined) {
            throw new Error("cannot stop stopwatch before it has been started");
        }

        this.times.endTime = new Date().valueOf();
    }

    reset() {
        this.times.startTime = undefined;
        this.times.endTime = undefined;
    }

    setElapsedSeconds(seconds) {
        this.times.endTime = new Date().valueOf();
        this.times.startTime = new Date(this.times.endTime - 1000 * seconds).valueOf();
    }

    isComplete() {
        return this.times.startTime !== undefined && this.times.endTime !== undefined;
    }

    formatElapsedTime() {
        if (! this.times.startTime) {
            return '';
        }

        function format(val) {
            return leftPadZero(Math.floor(val));
        }

        function formatDays(seconds) {
            const d = Math.floor(seconds / (3600 * 24));
            return d === 0
                ? ''
                : `${d} day${d > 1 ? 's' : ''} `;
        }

        function leftPadZero(num) {
            return num >= 10
                ? num
                : '0' + num;
        }

        const s = Math.floor(this.getElapsedSeconds());
        return 'Elapsed time: ' + formatDays(s)
            + [
                // hh:mm:ss
                format(s % (3600 * 24) / 3600),
                format(s % 3600 / 60),
                format(s % 60),
            ].join(':');
    }
}

export function useStopwatch() {
    let stopwatchData = useRef({
        startTime: undefined,
        endTime: undefined
    })

    return new Stopwatch(stopwatchData);
}
