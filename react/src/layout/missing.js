import { View } from "./layout";

export class MissingLayout extends View {
    getFormDependencies = () => {
        return [];
    }

    component = (props) => {
        return <>Missing layout!</>;
    }
}
