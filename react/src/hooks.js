import React, { useState, useEffect, useRef } from 'react';

/**
 * Implements useEffect with the ability to block until the returned callback is called. Will run the
 * callback the first time it is encountered
 * @param {() => void} callback a callback to run if this hook is not blocked
 * @param {[*]} reqs list of reqs to pass to internal useEffect
 * @returns {() => void} a callback function that causes the component to re-render and run the callback
 */
 export function useBlockingEffect(callback, reqs) {
    const [lock, updateLock] = useState(false);
    useEffect(() => {
        if(!lock) {
            updateLock(true);
            callback();
        }
    }, [lock, ...(reqs || [])])
    return () => updateLock(false);
}

export function useSetup(shouldRun, callback) {
    const [hasSetup, updateHasSetup] = useState(false);
    const [callbackStarted] = useState({value: false});
    const finish = () => {
        updateHasSetup(true);
    }
    useEffect(() => {
        if(shouldRun && !hasSetup && !callbackStarted.value) {
            callbackStarted.value = true;
            callback(finish);
        }
    });
    return hasSetup;
}

export function useRenderCount(name) {
    const renderCount = useRef(0);
    const domRenderCount = useRef(0);
    ++renderCount.current;
    useEffect(() => {
        ++domRenderCount.current;
        console.log(`DOM render ${name} ${domRenderCount.current} (${renderCount.current})`);
    })
    console.log(`Render ${name} ${(++renderCount.current)}`);
}
