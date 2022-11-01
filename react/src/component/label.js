import { Tooltip, OverlayTrigger } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";

export function LabelTooltip(props) {
    let renderTooltip = (childProps) => (
        <Tooltip id="label-tooltip" {...childProps}>
            {props.text}
        </Tooltip>
    );
    return (
        <OverlayTrigger
            placement="bottom"
            delay={{ show: 250, hide: 400 }}
            overlay={renderTooltip}
        >
            <span> <FontAwesomeIcon icon={Icon.faInfoCircle} fixedWidth /></span>
        </OverlayTrigger>
    );
}
