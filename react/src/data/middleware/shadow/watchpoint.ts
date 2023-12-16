import { ArrayFieldState } from "../../../store/common";
import { ModelState, modelSelectors, modelActions } from "../../../store/models";
import { Schema } from "../../../utility/schema";
import { newModelFromSchema } from "../../data";
import { ConfigurableMiddleware } from "../middleware";
import { Dependency } from "../../dependency";

export type WatchpointReportsMiddlewareConfig = {
    beamlineDependency: string,
    watchpointReportsDependency: string,
    watchpointModelName: string,
    watchpointReportModelName: string
}

export const shadowBeamlineWatchpointReportsMiddleware: ConfigurableMiddleware<WatchpointReportsMiddlewareConfig> = (config: WatchpointReportsMiddlewareConfig, schema: Schema) => {
    let beamDep = new Dependency(config.beamlineDependency);
    let watchRepDep = new Dependency(config.watchpointReportsDependency);
    
    return store => next => action => {
        if(action.type === "models/updateModel") {
            let { name, value } = action.payload;
            if(name === beamDep.modelName) {
                let watchpointReportsModel: ModelState = modelSelectors.selectModel(watchRepDep.modelName)(store.getState());
                if(watchpointReportsModel) {
                    let watchpointReports = watchpointReportsModel[watchRepDep.fieldName] as ArrayFieldState<ModelState>;
                    let bv: ArrayFieldState<ModelState> = value[beamDep.fieldName];
                    let findWatchpointReportById = (id) => watchpointReports.find(e => e.item.id === id);
                    let reportsValue = bv.filter(e => e.model == config.watchpointModelName).map(e => {
                        let id = e.item.id;
                        let watchpointReport = findWatchpointReportById(id); // TODO: these ids need to be made more unique or errors will occur
                        if(!watchpointReport) {
                            watchpointReport = {
                                item: newModelFromSchema(schema.models[config.watchpointReportModelName], { id }),
                                model: config.watchpointReportModelName
                            };
                        }
            
                        return {
                            report: watchpointReport,
                            position: e.item.position as number
                        }
                    }).sort((e1, e2) => e1.position - e2.position).map(e => e.report);
    
                    store.dispatch(modelActions.updateModel({ name: watchRepDep.modelName, value: {
                        [watchRepDep.fieldName]: reportsValue
                    }}));
                }
            }
        }
        return next(action);
    }
} 
