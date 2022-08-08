import { Card, Modal, Col, Button, Form } from "react-bootstrap";
import { useState, Fragment } from 'react';
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export function Panel(props) {
    let {title, buttons, panelBodyShown, ...otherProps} = props;
    return (
        <Card>
            <Card.Header className="lead bg-info bg-opacity-25">
                {title}
                <div className="float-end">
                    {buttons}
                </div>
            </Card.Header>
            {panelBodyShown &&
             <Card.Body>
                 {props.children}
             </Card.Body>
            }
        </Card>
    );
}

function ViewPanelActionButtons(props) {
    let {canSave, onSave, onCancel, ...otherProps} = props;
    return (
        <Col className="text-center" sm={12}>
            <Button onClick={onSave} disabled={! canSave } variant="primary">Save Changes</Button>
            <Button onClick={onCancel} variant="light" className="ms-1">Cancel</Button>
        </Col>
    )
}

function EditorForm(props) {
    return (
        <Form>
            {props.children}
        </Form>
    );
}

export function EditorPanel(props) {
    let {
        submit,
        cancel,
        showButtons,
        mainChildren,
        modalChildren,
        formValid,
        title,
        id
    } = props;

    let [advancedModalShown, updateAdvancedModalShown] = useState(false);
    let [panelBodyShown, updatePanelBodyShown] = useState(true);

    let headerButtons = (
        <Fragment>
            <a className="ms-2" onClick={() => updateAdvancedModalShown(true)}><FontAwesomeIcon icon={Icon.faPencil} fixedWidth /></a>
            <a className="ms-2" onClick={() => updatePanelBodyShown(! panelBodyShown)}><FontAwesomeIcon icon={panelBodyShown ? Icon.faChevronUp : Icon.faChevronDown} fixedWidth /></a>
        </Fragment>
    );

    let _cancel = () => {
        updateAdvancedModalShown(false);
        cancel();
    }

    let _submit = () => {
        updateAdvancedModalShown(false);
        submit();
    }

    let actionButtons = <ViewPanelActionButtons canSave={formValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>

    // TODO: should this cancel changes on modal hide??
    return (
        <Panel title={title} buttons={headerButtons} panelBodyShown={panelBodyShown}>
            <EditorForm key={id}>
                {mainChildren}
            </EditorForm>

            <Modal show={advancedModalShown} onHide={() => _cancel()} size="lg">
                <Modal.Header className="lead bg-info bg-opacity-25">
                    { title }
                </Modal.Header>
                <Modal.Body>
                    <EditorForm key={id}>
                        {modalChildren}
                    </EditorForm>
                    {showButtons &&
                     <Fragment>
                         {actionButtons}
                     </Fragment>
                    }
                </Modal.Body>
            </Modal>
            {showButtons && actionButtons}
        </Panel>
    )
}
