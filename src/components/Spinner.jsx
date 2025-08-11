// SPINNER SPINNING
import "./Spinner.css";
export default function Spinner({ size = 16, className = "", label = "Loading" }) {
    return (
        <svg
            className={`tst-spinner ${className}`}
            width={size}
            height={size}
            viewBox="0 0 24 24"
            role="status"
            aria-label={label}
        >
            <circle
                className="tst-spinner-track"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4" fill="none"
            />
            <path
                className="tst-spinner-arc"
                fill="currentColor"
                d="M4 12a8 8 0 0 0 8 8v-4a4 4 0 0 1-4-4H4z"
            />
        </svg>
    );
}
