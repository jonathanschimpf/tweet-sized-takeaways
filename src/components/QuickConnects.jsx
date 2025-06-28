// src/components/QuickConnects.jsx
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faDev,
  faLinkedin,
  faGithub,
  faInstagram,
  faThreads,
} from "@fortawesome/free-brands-svg-icons";
import { faCameraRetro } from "@fortawesome/free-solid-svg-icons";
import "./QuickConnects.css";

export default function QuickConnects() {
  const icons = [
    {
      icon: faCameraRetro,
      label: ".COM",
      url: "https://jonathanschimpf.com/",
    },
    {
      icon: faDev,
      label: ".DEV",
      url: "https://jonathanschimpf.dev/",
    },
    {
      icon: faLinkedin,
      label: "LinkedIn",
      url: "https://www.linkedin.com/in/jonathan-schimpf/",
    },
    {
      icon: faGithub,
      label: "GitHub",
      url: "https://github.com/jonathanschimpf",
    },
    {
      icon: faInstagram,
      label: "Instagram",
      url: "https://www.instagram.com/schimpfstagram/",
    },
    {
      icon: faThreads,
      label: "Threads",
      url: "https://www.threads.net/@schimpfstagram",
    },
  ];

  return (
    <div className="quick-connects">
      {icons.map(({ icon, label, url }) => (
        <a
          key={label}
          href={url}
          target="_blank"
          rel="noreferrer"
          aria-label={label}
          className="quick-icon"
        >
          <FontAwesomeIcon icon={icon} size="2x" />
          <span className="tooltip">{label}</span>
        </a>
      ))}
    </div>
  );
}
