import { ContextLayouts, ContextRelativeFormState } from "../context";

export class PanelLayout extends View {
    getFormDependencies = (config) => {
        // TODO
        return [];
    }

    component = (props) => {
        let schema = useContext(ContextSchema);

        let { config } = props;

        
        let formState = useContext(ContextRelativeFormState);
        let models = useContext(ContextRelativeModels);
        let title = useInterpolatedString(models, config.title);

        let layouts = useContext(ContextLayouts);

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);

        let store = useStore();

        let getModels = () => {
            return models.getModels(store.getState());
        }

        let saveToServer = (models) => {
            simulationInfoPromise.then((simulationInfo) => {
                simulationInfo.models = models;
                fetch("/save-simulation", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(simulationInfo)
                }).then(resp => {
                    // TODO: error handling
                    console.log("resp", resp);
                })
            })
        }

        if(!config) {
            throw new Error("view missing config: " + config.name);
        }

        let basic = config.basic || [];
        let advanced = config.advanced || [];

        let dependencies = [...basic, ...advanced].map(layoutConfig => {
            let layout = layouts.getLayoutForConfig(layoutConfig);
            return layout.getFormDependencies(layoutConfig);
        }).flat().map(dependencyString => new Dependency(dependencyString));

        let hookedDependencyGroup = new HookedDependencyGroup({ schemaModels: schema.models, models, dependencies });

        let hookedDependencies = dependencies.map(hookedDependencyGroup.getHookedDependency);

        let formController = new FormController({ formState, hookedDependencies });

        let submit = () => {
            let models = getModels();
            formController.submitChanges();
            saveToServer(models);
        }

        let mapLayoutToElement = (layoutConfig, idx) => {
            let layout = layouts.getLayoutForConfig(layoutConfig);
            let LayoutComponent = layout.component;
            return <LayoutComponent key={idx} config={layoutConfig}></LayoutComponent>;
        }

        let mainChildren = (!!basic) ? basic.map(mapLayoutToElement) : undefined;
        let modalChildren = (!!advanced) ? advanced.map(mapLayoutToElement) : undefined;

        let formProps = {
            submit: submit,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren,
            modalChildren,
            title: title || config.name,
            id: config.name
        }

        return (
            <ContextRelativeFormDependencies.Provider value={hookedDependencies}>
                <ContextRelativeHookedDependencyGroup.Provider value={hookedDependencyGroup}>
                    <ContextRelativeFormController.Provider value={formController}>
                        <EditorPanel {...formProps}>
                        </EditorPanel>
                    </ContextRelativeFormController.Provider>
                </ContextRelativeHookedDependencyGroup.Provider>
            </ContextRelativeFormDependencies.Provider>
        )
    }
}
