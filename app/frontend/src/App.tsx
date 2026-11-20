import { Routes, Route } from "react-router-dom";
import AppShell from "@/components/AppShell";
import Config from "@/pages/Config";
import Dashboard from "@/pages/Dashboard";
import Energy from "@/pages/Energy";
import System from "@/pages/System";

import Acquisition from "@/pages/Acquisition";
import Appearance from "@/pages/Appearance";
import Theme from "@/components/Theme";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <><Theme /><Routes>
      <Route path="/flow" element={<main className="embed-view min-h-screen space-y-5 bg-background p-4 text-foreground"><Dashboard embedded /></main>} />
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/energie" element={<Energy />} />
        <Route path="/konfiguration" element={<Config />} />
        <Route path="/datenerfassung" element={<Acquisition />} />
        <Route path="/darstellung" element={<Appearance />} />
        <Route path="/system" element={<System />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes></>
  );
}
