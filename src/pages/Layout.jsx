import { Link, useLocation, Outlet } from "react-router-dom";
import "../App.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTwitter } from "@fortawesome/free-brands-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faTwitter);

export default function Layout() {
  const location = useLocation();

  return (
    <div className="container">
      <nav className="nav-links">
        <Link
          to="/"
          className={`nav-link-item ${
            location.pathname === "/" ? "active" : ""
          }`}
        >
          <FontAwesomeIcon icon={faTwitter} />
        </Link>
        <span className="nav-separator">•</span>
        <Link
          to="/about"
          className={`nav-link-item ${
            location.pathname === "/about" ? "active" : ""
          }`}
        >
          About
        </Link>
      </nav>

      <Outlet />
    </div>
  );
}
