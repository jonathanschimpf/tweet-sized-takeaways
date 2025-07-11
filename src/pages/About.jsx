// src/pages/About.jsx
import QuickConnects from "../components/QuickConnects";
import "./About.css";

export default function About() {
  return (
    <div className="container text-center mt-5">
      <h2 className="about-title">About Tweet-Sized Takeaways</h2>
      <p className="mt-3">
        <p className="about-body mt-3">
          <a href="https://github.com/jonathanschimpf/tweet-sized-takeaways" target="_blank" rel="noopener noreferrer" className="twitterblue-link">
            Tweet-Sized Takeaways</a>&nbsp; starts by pulling what websites quietly embed in their <span className="twitterbluetxt">&lt;head&gt;</span>&nbsp; — Open Graph <span className="twitterbluetxt">&lt;meta&gt;</span>&nbsp;
          tags like <span className="twitterbluetxt">'og:title'</span>  and <span className="twitterbluetxt">'og:description'</span>. If those tags are informative, you get a clean 280-character (or less) takeaway instantly,
          straight from the source. Alongside that metadata summary, a 🤗 Hugging Face button lives right on the card, offering an alternate perspective,
          generated from the page's visible text using the open-source <a href="https://huggingface.co/facebook/bart-large-cnn" target="_blank" rel="noopener noreferrer" className="twitterblue-link">
            facebook/bart-large-cnn </a>&nbsp;summarization model, served through Hugging Face's Inference API.
          <br />
          <br />
          It's an interesting contrast between what a developer writes into &lt;meta&gt; tags and what an AI model extracts from the full content.
          So whether it's a quick, native insight or a modeled, AI-powered interpretation, you get two takes on the same link.
          One lightweight and author-provided, one heavyweight and distilled by open source. &nbsp;
          <span className="twitterbluesignoff">
            Crafted by Jonathan Schimpf in 2025 — 2 years after Twitter died.
          </span>
        </p>
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
    </div >
  );
}
