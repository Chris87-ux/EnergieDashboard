export type SeriesKind="measurement"|"power"|"soc"|"charge"|"discharge"|"status"|"cycles";
export interface ChartSeries {kind:SeriesKind;reference_id:string;label:string;color:string;unit:string;}
export interface ChartConfig {id:string;name:string;series:ChartSeries[];sort_order:number;}
export interface ChartSource {kind:SeriesKind;reference_id:string;name:string;unit:string;enabled:boolean;record?:boolean;}
export interface ChartData {id:string;name:string;start:string;end:string;step_s:number;series:(ChartSeries&{name:string;digital:boolean;points:[string,number|null][]})[];errors:string[];}
