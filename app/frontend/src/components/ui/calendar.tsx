import { DayPicker, type DayPickerProps } from "react-day-picker";
import "react-day-picker/style.css";

export function Calendar(props: DayPickerProps) {
  return <DayPicker className="[--rdp-accent-color:#93C5FD] [--rdp-accent-background-color:#1C2E6A] [--rdp-day-height:36px] [--rdp-day-width:36px] [--rdp-day_button-height:34px] [--rdp-day_button-width:34px]" {...props} />;
}
