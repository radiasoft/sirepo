import { formSelectors, formActions } from "../../../store/formState";
import { ModelState, modelActions } from "../../../store/models";
import { getValueSelector, StoreTypes } from "../../data";
import { ConfigurableMiddleware } from "../middleware";
import { Dependency } from "../../dependency";

export type BeamlineSortingMiddlewareConfig = {
    beamlineDependency: string,
}

export const shadowBeamlineSortingMiddleware: ConfigurableMiddleware<BeamlineSortingMiddlewareConfig> = (config, schema) => {
    let beamDep = new Dependency(config.beamlineDependency);

    return store => next => action => {
        let sortValues = (v, vs) => v.sort((a, b) => {
            return parseFloat(vs(a.item.position)) - parseFloat(vs(b.item.position))
        });

        if(action.type === "models/updateModel") {
            let { name, value } = action.payload;
            if(name === beamDep.modelName) {
                let vs = getValueSelector(StoreTypes.Models)
                let v = vs(value.elements);
                let nv = sortValues(v, vs);

                let formBeamlineModel: ModelState = formSelectors.selectModel(beamDep.modelName)(store.getState());
                if(formBeamlineModel !== undefined) {
                    let fvs = getValueSelector(StoreTypes.FormState);
                    store.dispatch(formActions.updateModel({
                        name,
                        value: {
                            ...formBeamlineModel,
                            [beamDep.fieldName]: {
                                ...(formBeamlineModel[beamDep.fieldName] as any),
                                value: sortValues([...fvs(formBeamlineModel[beamDep.fieldName] as any)], fvs)
                            }
                        }
                    }))
                }
                

                return next(modelActions.updateModel({
                    name,
                    value: {
                        ...value,
                        [beamDep.fieldName]: nv
                    }
                }));
            }
        }

        return next(action);
    }
}
