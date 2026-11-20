import { useEffect } from "react";
import { useSettings } from "@/lib/queries";
import { defaultAppearance } from "@/pages/Appearance";
export default function Theme() {
  const {data}=useSettings();
  useEffect(()=>{const a=data?.appearance??defaultAppearance;const style=document.documentElement.style;
    style.setProperty("--background",a.background);style.setProperty("--card",a.surface);style.setProperty("--popover",a.surface);
    style.setProperty("--muted",`color-mix(in srgb, ${a.surface} 70%, ${a.background})`);
    style.setProperty("--secondary",`color-mix(in srgb, ${a.surface} 80%, ${a.accent} 10%)`);
    style.setProperty("--accent",`color-mix(in srgb, ${a.accent} 18%, ${a.surface})`);
    style.setProperty("--border",`color-mix(in srgb, ${a.surface} 80%, ${a.accent} 20%)`);
    style.setProperty("--primary",a.accent);style.setProperty("--ring",a.accent);document.documentElement.dataset.layout=a.layout;
  },[data?.appearance]);return null;
}
