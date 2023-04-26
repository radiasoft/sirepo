import { ArrayInputLayout } from "./array";
import { BooleanInputLayout } from "./boolean";
import { ArrayElementEnumInputLayout, ComputeResultEnumInputLayout, EnumInputLayout, SimulationListEnumInputLayout } from "./enum";
import { FileInputLayout } from "./file";
import { InputLayoutType } from "./input";
import { FloatInputLayout, IntegerInputLayout } from "./number";
import { StringInputLayout } from "./string";
import { ValueListInputLayout } from "./valueList";

export const TYPE_BASES: {[baseName: string]: InputLayoutType} = {
    'Boolean': BooleanInputLayout,
    'String': StringInputLayout,
    'Float': FloatInputLayout,
    'Integer': IntegerInputLayout,
    'File': FileInputLayout,
    'Enum': EnumInputLayout,
    'ComputeEnum': ComputeResultEnumInputLayout,
    'SimListEnum': SimulationListEnumInputLayout,
    // moellep: for omega, replace with real implementation eventually
    'SimArray': StringInputLayout,
    // garsuga: for madx, replace with real implementation eventually
    'RPNValue': FloatInputLayout,
    // garsuga: for madx, replace with real implementation eventually
    'OutputFile': FileInputLayout,
    // garsuga: for madx, needs to be implemented
    'ArrayElementEnum': ArrayElementEnumInputLayout,
    'ValueList': ValueListInputLayout,
    'Array': ArrayInputLayout
}
