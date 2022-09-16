export class MissingLayout extends View {
    getFormDependencies = () => {
        return [];
    }

    component = (props) => {
        return <>Missing layout!</>;
    }
}
