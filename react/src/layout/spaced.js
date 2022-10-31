export function LayoutWithSpacing(subView) {
    return class extends subView {
        constructor(layoutsWrapper) {
            super(layoutsWrapper);

            let oldComponent = this.component;

            this.component = (props) => {
                let ChildComponent = oldComponent;
                return (
                    <div className="sr-form-layout">
                        <ChildComponent {...props} />
                    </div>
                )
            }
        }
    }
}
