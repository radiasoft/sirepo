import { BooleanInputLayout } from "./boolean";
import { ComputeResultEnumInputLayout, EnumInputLayout, SimulationListEnumInputLayout } from "./enum";
import { FileInputLayout } from "./file";
import { InputLayoutType } from "./input";
import { FloatInputLayout, IntegerInputLayout } from "./number";
import { StringInputLayout } from "./string";

export const TYPE_BASES: {[baseName: string]: InputLayoutType} = {
    'Boolean': BooleanInputLayout,
    'String': StringInputLayout,
    'Float': FloatInputLayout,
    'Integer': IntegerInputLayout,
    'File': FileInputLayout,
    'Enum': EnumInputLayout,
    'ComputeEnum': ComputeResultEnumInputLayout,
    'SimListEnum': SimulationListEnumInputLayout,
    // for omega, replace with real implementation eventually
    'SimArray': StringInputLayout,
}
