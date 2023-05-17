import { Tooltip, OverlayTrigger } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import React from "react";

export function LabelTooltip(props) {
    let renderTooltip = (childProps) => (
        <Tooltip id="label-tooltip" {...childProps}>
            {props.text}
        </Tooltip>
    );
    return (
        <OverlayTrigger
            //TODO(pjm): bottom placement causes page to flicker when body scrollbar is modified
            placement="top"
            delay={{ show: 250, hide: 400 }}
            overlay={renderTooltip}
        >
            <span> <FontAwesomeIcon icon={Icon.faInfoCircle} fixedWidth /></span>
        </OverlayTrigger>
    );
}
