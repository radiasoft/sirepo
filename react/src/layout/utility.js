export function SpacedLayout(subView) {
    return new class extends subView {
        component = (props) => {
            let ChildComponent = super.component;
            return (
                <div className="sr-form-layout">
                    <ChildComponent {...props} />
                </div>
            )
        }
    }
}
