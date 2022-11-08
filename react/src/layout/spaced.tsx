import React from "react";
import { Dependency } from "../data/dependency";
import { LayoutType, View } from "./layout";

export function LayoutWithSpacing<P>(Child: LayoutType<P>): LayoutType<P> {
    return class extends View<P> {
        child: View<P>;
        constructor(layoutsWrapper) {
            super(layoutsWrapper);
            this.child = new Child(layoutsWrapper);
        }


        getFormDependencies(config: P): Dependency[] {
            return this.child.getFormDependencies(config);
        }

        component = (props) => {
            let ChildComponent = this.child.component;
            return (
                <div className="sr-form-layout">
                    <ChildComponent {...props} />
                </div>
            )
        }
    }
}
