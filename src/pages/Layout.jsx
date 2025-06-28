import { NavLink, Outlet } from "react-router-dom";
import "../App.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTwitter } from "@fortawesome/free-brands-svg-icons";
import { useTheme } from "../ThemeContext"; // ✅ IMPORT CONTEXT
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faTwitter);

export default function Layout() {
  const { darkMode, setDarkMode } = useTheme();

  const toggleTheme = () => setDarkMode(!darkMode);

  return (
    <div className="container">
      {/* ✅ TOGGLE IN TOP LEFT */}
      <div
        style={{
          position: "absolute",
          top: "1rem",
          left: "1rem",
          zIndex: 1000,
        }}
      >
        <button className="theme-toggle-icon-btn" onClick={toggleTheme}>
          {darkMode ? "🌞" : "🌙"}
        </button>
      </div>

      <nav className="nav-links">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `nav-link-item ${isActive ? "active" : "inactive"}`
          }
        >
          <FontAwesomeIcon icon={faTwitter} />
        </NavLink>
        <span className="nav-separator">•</span>
        <NavLink
          to="/about"
          className={({ isActive }) =>
            `nav-link-item ${isActive ? "active" : "inactive"}`
          }
        >
          About
        </NavLink>
      </nav>

      <Outlet />
    </div>
  );
}
