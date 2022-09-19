export function SpacedLayout(subView) {
    return class extends subView {
        constructor(config) {
            super(config);

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
