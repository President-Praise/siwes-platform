import { NavLink } from "react-router-dom";
import { useAuth } from "../auth";

interface Item { to: string; label: string; }

const superItems: Item[] = [
  { to: "/", label: "Dashboard" },
  { to: "/schools", label: "Schools" },
  { to: "/admins", label: "Admins" },
];
const schoolItems: Item[] = [
  { to: "/", label: "Dashboard" },
  { to: "/orders", label: "Orders" },
  { to: "/students", label: "Students" },
  { to: "/analytics", label: "Analytics" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar({ role }: { role: "super_admin" | "school_admin" }) {
  const { me, logout } = useAuth();
  const items = role === "super_admin" ? superItems : schoolItems;
  return (
    <aside className="w-56 fixed inset-y-0 left-0 bg-navy text-white p-5 flex flex-col">
      <div className="mb-6">
        <div className="font-head text-lg font-bold">SIWES Platform</div>
        <div className="text-xs opacity-75 mt-1">
          {role === "super_admin" ? "Super Admin" : me?.school?.name}
        </div>
      </div>
      <nav className="flex-1 space-y-1">
        {items.map(it => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.to === "/"}
            className={({ isActive }) =>
              "block px-3 py-2 rounded text-sm " +
              (isActive ? "bg-gold text-navy font-semibold" : "hover:bg-navy-dark")
            }
          >
            {it.label}
          </NavLink>
        ))}
      </nav>
      <div className="text-xs opacity-75 border-t border-white/20 pt-4">
        <div className="mb-2">{me?.admin?.display_name || me?.admin?.username || "superadmin"}</div>
        <button onClick={logout} className="text-gold hover:text-white">Log out</button>
      </div>
    </aside>
  );
}
