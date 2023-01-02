import React from "react";
import usePortal from "react-useportal";

export type PortalProps = {
    targetId: string,
    className?: string
} & {[key: string]: any}

export function Portal(props: PortalProps) {
    let { targetId, className } = props;

    let { Portal, portalRef } = usePortal({
        bindTo: document && document.getElementById(targetId)
    })

    if(portalRef && portalRef.current) {
        (className || "").split(" ").filter(c => c && c.length > 0).forEach(c => portalRef.current.classList.add(c));
    }

    return (
        <Portal>
            {props.children}
        </Portal>
    )
}
