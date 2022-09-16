export function FormField(props) {
    let { label, tooltip } = props;
    return (
        <Form.Group size="sm" as={Row} className="justify-content-center">
            <Form.Label column className="text-start">
                {label}
                {tooltip &&
                    <LabelTooltip text={tooltip} />
                }
            </Form.Label>
            <Col>
                {props.children}
            </Col>
        </Form.Group>
    )
}

export function EditorForm(props) {
    return (
        <Form>
            {props.children}
        </Form>
    );
}

export function FormStateInitializer(props) {
    let [hasInit, updateHasInit] = useState(undefined);

    let schema = useContext(ContextSchema);

    let models = useContext(ContextModels);
    let formState = new FormState({
        formActions: {
            updateFormFieldState,
            updateFormState
        },
        formSelectors: {
            selectFormState
        }
    })

    useEffect(() => {
        Object.entries(models.getModels()).forEach(([modelName, model]) => {
            if (modelName in schema.models) { // TODO non-model data should not be stored with models in store
                formState.updateModel(modelName, formStateFromModel(model, schema.models[modelName]))
            }
        })
        updateHasInit(true);
    }, [])
    
    return hasInit && (
        <ContextRelativeFormState.Provider value={formState}>
            {props.children}
        </ContextRelativeFormState.Provider>
    );
}
