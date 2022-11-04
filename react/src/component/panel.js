import {
    Card,
    Col,
    Button,
    Modal
} from "react-bootstrap";
import { useState, Fragment } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import { EditorForm } from "./form";
import { v4 as uuidv4 } from 'uuid';
import { ContextPanelController } from "../context";
import { PanelController } from "../data/panel";

export function Panel(props) {
    let { title, buttons, panelBodyShown, ...otherProps } = props;

    let [panelButtonsId] = useState(() => uuidv4());

    let [shown, updateShown] = useState(true);

    let panelController = new PanelController({
        buttonPortalId: panelButtonsId,
        // upward communication is poor practice, this should be avoided or done another way
        onChangeShown: (shown) => {
            updateShown(shown)
        }
    })

    return (
        <ContextPanelController.Provider value={panelController}>
            <Card style={{ display: shown ? undefined: 'none' }}>
                <Card.Header className="lead bg-info bg-opacity-25">
                    {title}
                    <div className="float-end">
                        <div id={panelButtonsId} className="d-inline"></div>
                        {buttons}
                    </div>
                </Card.Header>
                {panelBodyShown &&
                    <Card.Body>
                        {props.children}
                    </Card.Body>
                }
            </Card>
        </ContextPanelController.Provider>
    );
}

export function ViewPanelActionButtons(props) {
    let { canSave, onSave, onCancel, ...otherProps } = props;
    return (
        <Col className="text-center sr-form-action-buttons" sm={12}>
            <Button onClick={onSave} disabled={!canSave} variant="primary">Save Changes</Button>
            <Button onClick={onCancel} variant="light" className="ms-1">Cancel</Button>
        </Col>
    )
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

    let hasModalChildren = !!modalChildren && modalChildren !== [];

    let headerButtons = (
        <Fragment>
            {hasModalChildren && <a className="ms-2" onClick={() => updateAdvancedModalShown(true)}><FontAwesomeIcon icon={Icon.faPencil} fixedWidth /></a>}
            <a className="ms-2" onClick={() => updatePanelBodyShown(!panelBodyShown)}><FontAwesomeIcon icon={panelBodyShown ? Icon.faChevronUp : Icon.faChevronDown} fixedWidth /></a>
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

            {hasModalChildren && <Modal show={advancedModalShown} onHide={() => _cancel()} size="lg">
                <Modal.Header className="lead bg-info bg-opacity-25">
                    {title}
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
            </Modal>}
            {showButtons && actionButtons}
        </Panel>
    )
}
