import { useContext } from "react";
import { StoreType, StoreTypes } from "../data/data";
import { CHandleFactory } from "../data/handle";
import { interpolate } from "../utility/string"

export function useShown<M, F>(shownStr: string, defaultValue: boolean, type: StoreType<M, F>) {
    let dhf = useContext(CHandleFactory);
    if(shownStr) {
        let shown = interpolate(shownStr).withDependencies(dhf, type).evaluated();
        if(typeof(shown) !== 'boolean'){
            throw new Error(`'shown' function did not evaluate to a boolean "${shownStr}" -> ${shown}`)
        }
        return shown;
    }
    return defaultValue;
}
