import React from "react";

export const ContextPanelController = React.createContext<PanelController>(undefined);

export class PanelController {
    buttonPortalId: string;
    onChangeShown: (shown: boolean) => void;

    constructor({
        buttonPortalId,
        onChangeShown
    }) {
        this.buttonPortalId = buttonPortalId;
        this.onChangeShown = onChangeShown;
    }

    setShown = (shown: boolean) => {
        this.onChangeShown(shown);
    }
}
