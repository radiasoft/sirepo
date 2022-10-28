export class PanelController {
    constructor({
        buttonPortalId,
        onChangeShown
    }) {
        this.buttonPortalId = buttonPortalId;
        this.onChangeShown = onChangeShown;
    }

    setShown = (shown) => {
        this.onChangeShown(shown);
    }
}
