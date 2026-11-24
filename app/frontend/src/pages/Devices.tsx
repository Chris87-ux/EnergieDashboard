import CycleOverview from "@/components/CycleOverview";
import {t} from "@/lib/i18n";
export default function Devices(){return <><h1 className="text-2xl font-bold">{t("Gerätestatus")}</h1><CycleOverview full/></>;}
