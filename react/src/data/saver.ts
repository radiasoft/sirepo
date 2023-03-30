import { FormModelState } from "../store/formState";
import { ModelState } from "../store/models";
import { getModelNamesSelector, getModelReadSelector, getModelWriteActionCreator, StoreType } from "./data";

export class FormStateSaver {
    private saveModel: (name: string, value: FormModelState) => void

    constructor() {
        this.saveModel = getModelWriteActionCreator(StoreType.FormState);
    }

    save = (state: any): void => {
        let fmns = getModelNamesSelector(StoreType.FormState)();
        let formModelNames = fmns(state);
        let fmvs = getModelReadSelector<FormModelState>(StoreType.FormState);
        let mvs = getModelReadSelector<ModelState>(StoreType.Models);

        let formModelValues = Object.fromEntries(formModelNames.map(mn => {
            return [
                mn,
                fmvs(mn)(state) 
            ]
        }))

        let modelValues = Object.fromEntries(formModelNames.map(mn => {
            return [
                mn,
                mvs(mn)(state)
            ]
        }))

        let modelUpdated = Object.entries(formModelValues).map(([modelName, formModelValue]) => {
            
        })
    }
}
