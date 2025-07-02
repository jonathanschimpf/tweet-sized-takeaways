// src/pages/About.jsx
import QuickConnects from "../components/QuickConnects";
import "./About.css";

export default function About() {
  return (
    <div className="container text-center mt-5">
      <h2 className="about-title">About Tweet-Sized Takeaways</h2>
      <p className="mt-3">
        This project distills the internet into 280-character insights. It
        scrapes, parses, and summarizes web content down to short overviews. At
        its core, Tweet-Sized Takeaways uses the open-source
        'facebook/bart-large-cnn' summarization model, hosted through Hugging
        Face's Inference API. This approach prioritizes transparency and
        accessibility over closed-source, pay-per-token alternatives — keeping
        things open and remixable. Built with FastAPI on the back-end and Vite +
        React on the front-end, the app supports a responsive dark/light mode
        toggle for a smoother user experience across devices. It's deployed
        seamlessly on Netlify for fast, global access.
      </p>

      <p className="twitterbluesignoff">
        Crafted by Jonathan Schimpf in 2025 — 2 years after Twitter died.
      </p>
      <br />

      <a
        href="https://huggingface.co/"
        target="_blank"
        rel="noopener noreferrer"
        className="huggingface-link quick-icon"
      >
        <span
          role="img"
          aria-label="Hugging Face"
          style={{ fontSize: "1.5rem" }}
        >
          🤗
        </span>
        <span className="tooltip">Hugging Face</span>
      </a>

      <br />
      <br />

      <QuickConnects />
    </div>
  );
}
