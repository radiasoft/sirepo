import { SimulationInfo } from "../component/simulation";
import { StoreTypes } from "../data/data";
import { HandleFactory } from "../data/handle";

export function useSimulationInfo(handleFactory: HandleFactory): SimulationInfo {
    return handleFactory.createModelHandle("simulation", StoreTypes.Models).hook().value as SimulationInfo;
}
