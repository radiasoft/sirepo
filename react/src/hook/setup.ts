import { useState, useEffect, useRef } from "react";

export function useSetup<T>(shouldRun: boolean, promise: () => Promise<T>): [boolean, T] {
    const [status, updateStatus] = useState({ completed: false, value: undefined });
    const promiseHasSubscribed = useRef(false);

    useEffect(() => {
        if(shouldRun && !status.completed && !promiseHasSubscribed.current) {
            promiseHasSubscribed.current = true;
            promise().then((v: T) => {
                updateStatus({
                    value: v,
                    completed: true
                })
            })
        }
    }, []);
    return [status.completed, status.value];
}
