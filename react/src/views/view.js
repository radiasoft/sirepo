import { useRenderCount } from "../hooks";

export class View {

    constructor() {
        this.name = this.constructor.name;

        /*
         * This process allows the extension of functionality
         * without requiring a name difference between definition
         * and caller. Component is both the overridden method
         * and called method but can be extended backwards by
         * the parent class.
         * 
         * In the future this can be used for baking in error
         * recovery points and other debugging as a standard
         * part of views.
         */
        let originalComponentDef = this.component;
        this.component = (props) => {
            this._componentBaseInit(props);
            originalComponentDef(props);
        }
    }

    _componentBaseInit(props) {
        let renderCountFn = useRenderCount;
        renderCountFn(this.name);
    }

    /**
     * Gets declared dependencies for this view so that
     * parent elements can make required hooks
     * @param {*} config 
     */
    getFormDependencies = (config) => {
        throw new Error("getFormDependencies() not implemented")
    }

    /**
     * Creates a new component for this view
     * @param {{ config: * }} props 
     */
    component = (props) => {
        throw new Error("component() not implemented")
    }
}
