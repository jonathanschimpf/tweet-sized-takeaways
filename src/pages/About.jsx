// src/pages/About.jsx
export default function About() {
  return (
    <div className="container text-center mt-5">
      <h2 className="title">About Tweet-Sized Takeaways</h2>
      <p className="mt-3">
        This project distills the internet into 280-character insights. It
        scrapes, parses, and runs content through Hugging Face to give
        tweet-ready summaries. Built with FastAPI + Vite + React. <br />
        Made by Jonathan Schimpf in 2025.
      </p>
    </div>
  );
}
