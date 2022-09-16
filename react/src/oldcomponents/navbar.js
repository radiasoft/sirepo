import { useContext, useState } from "react";
import { Modal } from "react-bootstrap";
import { useInterpolatedString } from "../dependency/dependency";
import { ContextModels } from "../components/context";
import { elementForLayoutName } from "./panel";

export let NavBarModalButton = ({ schema }) => (view) => {
    let NavBarModalButtonComponent = (props) => {
        let { config } = view;
        let { modal } = config;

        let models = useContext(ContextModels);
        let title = useInterpolatedString(models, config.title);

        let [modalShown, updateModalShown] = useState(false);

        let _cancel = () => {
            updateModalShown(false);
            cancel();
        }

        modal.items.map(layoutConfig => {
            let LayoutElement = elementForLayoutName(layoutConfig.layout).element;
            // TODO unify form functionality
        })

        return (
            <Modal show={modalShown} onHide={() => _cancel()} size="lg">
                <Modal.Header className="lead bg-info bg-opacity-25">
                    {title}
                </Modal.Header>
                <Modal.Body>

                </Modal.Body>
            </Modal>
        )
    }
}
