export class PanelLayout extends View {
    getDependencies = (config) => {
        // TODO
        return [];
    }

    component = (props) => {
        let schema = useContext(ContextSchema);

        let { config } = props;

        let formActions = useContext(ContextReduxFormActions); // TODO: make these generic
        let formSelectors = useContext(ContextReduxFormSelectors);

        let models = useContext(ContextRelativeModels);
        let title = useInterpolatedString(models, config.title);

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
            let ele = elementForLayoutName(layoutConfig.layout);
            return ele.getDependencies(layoutConfig);
        }).flat().map(dependencyString => new Dependency(dependencyString));

        let hookedDependencyGroup = new HookedDependencyGroup({ schemaModels: schema.models, models, dependencies });

        let hookedDependencies = dependencies.map(hookedDependencyGroup.getHookedDependency);

        let formController = new FormController({ formActions, formSelectors, hookedDependencies });

        let submit = () => {
            let models = getModels();
            formController.submitChanges();
            saveToServer(models);
        }

        let mapLayoutToElement = (layoutConfig, idx) => {
            let ele = elementForLayoutName(layoutConfig.layout);
            let LayoutElement = ele.element;
            return <LayoutElement key={idx} config={layoutConfig}></LayoutElement>;
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
