import React from "react";
import { Dependency } from "../data/dependency";
import { LayoutProps, LayoutType, View } from "./layout";

export function LayoutWithSpacing<C, P>(Child: LayoutType<C, P>): LayoutType<C, P> {
    return class extends View<C, P> {
        child: View<C, P>;
        constructor(layoutsWrapper) {
            super(layoutsWrapper);
            this.child = new Child(layoutsWrapper);
        }


        getFormDependencies(config: C): Dependency[] {
            return this.child.getFormDependencies(config);
        }

        component = (props: LayoutProps<C, P>) => {
            let ChildComponent = this.child.component;
            return (
                <div className="sr-form-layout">
                    <ChildComponent {...props} />
                </div>
            )
        }
    }
}
