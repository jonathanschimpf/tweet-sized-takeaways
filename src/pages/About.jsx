// src/pages/About.jsx
import QuickConnects from "../components/QuickConnects";

export default function About() {
  return (
    <div className="container text-center mt-5">
      <h2 className="about-title">About Tweet-Sized Takeaways</h2>
      <p className="mt-3">
        This project distills the internet into 280-character insights. It
        scrapes, parses, and summarizes web content to generate concise,
        tweet-ready overviews. At its core, Tweet-Sized Takeaways uses the
        open-source 'facebook/bart-large-cnn' summarization model, hosted
        through Hugging Face's Inference API. This approach prioritizes
        transparency and accessibility over closed-source, pay-per-token
        alternatives — keeping things open and remixable. Built with FastAPI on
        the backend and Vite + React on the frontend, the app supports a
        responsive dark/light mode toggle for a smoother user experience across
        devices. It's deployed seamlessly on Netlify for fast, global access.
        <br />
        <br />
        Crafted by Jonathan Schimpf in 2025 — 2 years after Twitter died.
      </p>

      <QuickConnects />
    </div>
  );
}
