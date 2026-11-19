import { Routes, Route } from "react-router-dom";
import AppShell from "@/components/AppShell";
import Config from "@/pages/Config";
import Dashboard from "@/pages/Dashboard";
import Energy from "@/pages/Energy";
import System from "@/pages/System";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/energie" element={<Energy />} />
        <Route path="/konfiguration" element={<Config />} />
        <Route path="/system" element={<System />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
