import { View } from "./layout";
import { useContext } from "react";
import { 
    Row,
    Col,
    Form,
    Container
} from "react-bootstrap";
import { 
    ContextRelativeFormController,
    ContextRelativeFormDependencies,
    ContextRelativeFormState,
    ContextSchema,
    ContextModelsWrapper,
    ContextRelativeHookedDependencyGroup
} from "../context";
import { Dependency, HookedDependencyGroup } from "../data/dependency";
import { FieldInput, LabeledFieldInput } from "../component/input";
import { FormController } from "../data/form";
import "./form.scss";

export function LayoutWithFormController(subLayout) {
    return class extends subLayout {
        constructor(layoutsWrapper) {
            super(layoutsWrapper);

            let oldComponent = this.component;

            this.component = (props) => {
                let ChildComponent = oldComponent;
                let FormComponent = this.formComponent;
                return (
                    <FormComponent {...props}>
                        <ChildComponent {...props}/>
                    </FormComponent>
                )
            }
        }

        formComponent = (props) => {
            let { config } = props;

            let contextFn = useContext;
            let formState = contextFn(ContextRelativeFormState);
            let schema = contextFn(ContextSchema);
            let modelsWrapper = contextFn(ContextModelsWrapper);
    
            let dependencies = this.getFormDependencies(config);
    
            let hookedDependencyGroup = new HookedDependencyGroup({ schemaModels: schema.models, modelsWrapper, dependencies });
    
            let hookedDependencies = dependencies.map(hookedDependencyGroup.getHookedDependency);
    
            let formController = new FormController({ formState, hookedDependencies });
    
            return (
                <ContextRelativeFormDependencies.Provider value={hookedDependencies}>
                    <ContextRelativeHookedDependencyGroup.Provider value={hookedDependencyGroup}>
                        <ContextRelativeFormController.Provider value={formController}>
                            { props.children }
                        </ContextRelativeFormController.Provider>
                    </ContextRelativeHookedDependencyGroup.Provider>
                </ContextRelativeFormDependencies.Provider>
            )
        }
    }
}

export class FieldGridLayout extends View {
    getFormDependencies = (config) => {
        let fields = [];
        for(let row of config.rows) {
            fields.push(...(row.fields));
        }
        return fields.map(f => new Dependency(f));
    }

    component = (props) => {
        let { config } = props;

        let contextFn = useContext;

        let formController = contextFn(ContextRelativeFormController);

        let columns = config.columns;
        let rows = config.rows;

        let els = [];

        let someRowHasLabel = rows.reduce((prev, cur) => prev || !!cur.label);
        
        els.push( // header row
            <Row className="sr-form-row" key={"header"}>
                {(someRowHasLabel ? <Col key={"label_dummy"}></Col> : undefined)}
                {columns.map(colName => <Col key={colName}><Form.Label size={"sm"}>{colName}</Form.Label></Col>)}
            </Row>
        )

        for(let idx = 0; idx < rows.length; idx++) {
            let row = rows[idx];
            let fields = row.fields;
            let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
            let rowElement = (
                <Row className="sr-form-row" key={idx}>
                    {labelElement ? <Col>{labelElement}</Col> : undefined}
                    {columns.map((_, index) => {
                        let field = fields[index];
                        let hookedField = formController.getHookedField(new Dependency(field));
                        return <FieldInput key={index} field={hookedField}></FieldInput>
                    })}
                </Row>
            )
            els.push(rowElement);
        }

        return <Container>{els}</Container>
    }
}

export class FieldListLayout extends View {
    getFormDependencies = (config) => {
        return (config.fields || []).map(f => new Dependency(f));
    }

    component = (props) => {
        let { config } = props;

        let formController = useContext(ContextRelativeFormController);

        let fields = config.fields;

        return <Container>
            {fields.map((field, idx) => (
                <LabeledFieldInput key={idx} field={formController.getHookedField(new Dependency(field))}></LabeledFieldInput>
            ))} 
        </Container>
    }
}
