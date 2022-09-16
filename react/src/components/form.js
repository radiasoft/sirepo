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

function EditorForm(props) {
    return (
        <Form>
            {props.children}
        </Form>
    );
}
