export class FieldGridLayout extends View {
    getFormDependencies = (config) => {
        let fields = [];
        for(let row of config.rows) {
            fields.push(...(row.fields));
        }
        return fields;
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
            <Row key={"header"}>
                {(someRowHasLabel ? <Col key={"label_dummy"}></Col> : undefined)}
                {columns.map(colName => <Col key={colName}><Form.Label size={"sm"}>{colName}</Form.Label></Col>)}
            </Row>
        )

        for(let idx = 0; idx < rows.length; idx++) {
            let row = rows[idx];
            let fields = row.fields;
            let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
            let rowElement = (
                <Row key={idx}>
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
        return config.fields;
    }

    component = (props) => {
        let { config } = props;

        let contextFn = useContext;

        let formController = contextFn(ContextRelativeFormController);

        let fields = config.fields;

        return <Container>
            {fields.map((field, idx) => (
                <LabeledFieldInput key={idx} field={formController.getHookedField(new Dependency(field))}></LabeledFieldInput>
            ))} 
        </Container>
    }
}
