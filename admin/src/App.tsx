import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Login } from "./views/Login";
import { Sidebar } from "./components/Sidebar";

import { SuperDashboard } from "./views/SuperAdmin/Dashboard";
import { SuperSchools } from "./views/SuperAdmin/Schools";
import { SuperSchoolDetail } from "./views/SuperAdmin/SchoolDetail";
import { SuperAdmins } from "./views/SuperAdmin/Admins";

import { SchoolDashboard } from "./views/SchoolAdmin/Dashboard";
import { SchoolOrders } from "./views/SchoolAdmin/Orders";
import { SchoolStudents } from "./views/SchoolAdmin/Students";
import { SchoolSettings } from "./views/SchoolAdmin/Settings";
import { SchoolAnalytics } from "./views/SchoolAdmin/Analytics";

export function App() {
  const { state, me } = useAuth();
  if (state === "checking") return <div className="p-8 text-gray-500">Loading…</div>;
  if (state === "unauthenticated" || !me) return <Login />;

  return (
    <div className="min-h-screen flex">
      <Sidebar role={me.role} />
      <div className="flex-1 ml-56 p-6 max-w-7xl">
        {me.role === "super_admin" ? <SuperRoutes /> : <SchoolRoutes />}
      </div>
    </div>
  );
}

function SuperRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SuperDashboard />} />
      <Route path="/schools" element={<SuperSchools />} />
      <Route path="/schools/:id" element={<SuperSchoolDetail />} />
      <Route path="/admins" element={<SuperAdmins />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function SchoolRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SchoolDashboard />} />
      <Route path="/orders" element={<SchoolOrders />} />
      <Route path="/students" element={<SchoolStudents />} />
      <Route path="/analytics" element={<SchoolAnalytics />} />
      <Route path="/settings" element={<SchoolSettings />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
