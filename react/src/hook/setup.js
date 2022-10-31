import { useState, useEffect } from "react";

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
