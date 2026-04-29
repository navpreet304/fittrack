import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import {
  LayoutDashboard,
  Dumbbell,
  Utensils,
  Target,
  Ruler,
  Bell,
  Users,
  LogOut,
} from "lucide-react";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workouts", label: "Workouts", icon: Dumbbell },
  { to: "/meals", label: "Meals", icon: Utensils },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/measurements", label: "Measurements", icon: Ruler },
  { to: "/notifications", label: "Notifications", icon: Bell },
];

export default function Sidebar() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside
      style={{ background: "#0D1B2A", borderRight: "1px solid #1e3050" }}
      className="flex flex-col w-56 min-h-screen shrink-0"
    >
      <div className="p-4 text-white font-bold text-lg tracking-wide">
        FitTrack Pro
      </div>
      <nav className="flex-1 flex flex-col gap-1 p-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[#1A8FE3] text-white"
                  : "text-slate-300 hover:bg-[#1e3050] hover:text-white"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
        {auth?.role === "coach" && (
          <NavLink
            to="/coach"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[#1A8FE3] text-white"
                  : "text-slate-300 hover:bg-[#1e3050] hover:text-white"
              }`
            }
          >
            <Users size={18} />
            Coach Dashboard
          </NavLink>
        )}
      </nav>
      <div className="p-2">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-[#1e3050] transition-colors"
          style={{ background: "transparent", borderRadius: "0.5rem" }}
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </aside>
  );
}
