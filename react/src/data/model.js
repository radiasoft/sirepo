export class Models {
    constructor({ modelActions, modelSelectors }) {
        this.modelActions = modelActions;
        this.modelSelectors = modelSelectors;

        let dispatchFn = useDispatch;
        this.dispatch = dispatchFn();
    }

    getModel = (modelName, state) => {
        return this.modelSelectors.selectModel(modelName)(state);
    }

    getModels = (state) => {
        return this.modelSelectors.selectModels(state);
    }

    getIsLoaded = (state) => {
        return this.modelSelectors.selectIsLoaded(state);
    }

    forModel = (modelName) => {
        return {
            updateModel: (value) => {
                return this.updateModel(modelName, value);
            },
            hookModel: () => {
                return this.hookModel(modelName);
            }
        }
    }

    updateModel = (modelName, value) => {
        console.log("dispatching update to ", modelName, " changing to value ", value);
        dispatch(this.modelActions.updateModel({
            name: modelName,
            value
        }))
    }

    hookModel = (modelName) => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectModel(modelName));
    }

    hookModels = () => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectModels);
    }

    hookIsLoaded = () => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectIsLoaded);
    }
}
