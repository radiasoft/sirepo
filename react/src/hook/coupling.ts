import { useState } from "react";

export function useCoupledState<V>(dependentValue, stateValOrFn: V | (() => V)): [V, (n: V) => void, boolean] {
    let [dv, updateDv] = useState(dependentValue);
    let [v, updateV] = useState(stateValOrFn);
    
    let updated = false;

    if(dependentValue !== dv) {
        updateDv(dependentValue);
        let nv = typeof stateValOrFn === "function" ? (stateValOrFn as Function)() : stateValOrFn;
        updateV(nv);
        updated = true;
    }

    return [v, updateV, updated];
}
