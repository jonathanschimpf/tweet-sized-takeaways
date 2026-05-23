import { useState } from "react";
import TstSpinner from "./components/Spinner"; // ← custom spinner
import "bootstrap/dist/css/bootstrap.min.css";
import { Container, Form, Button, Card, Row, Col } from "react-bootstrap";
import "./App.css";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { faTwitter } from "@fortawesome/free-brands-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faCopy, faTwitter);

const THREADS_IMAGE_FALLBACKS = [
  "/images/og-fallbacks/threads/1_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/2_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/3_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/4_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/5_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/6_threads-og-image-fallback.png",
  "/images/og-fallbacks/threads/7_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/8_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/9_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/10_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/11_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/12_threads-og-image-fallback.jpeg",
  "/images/og-fallbacks/threads/13_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/14_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/15_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/16_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/17_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/18_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/19_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/20_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/21_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/22_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/23_threads-og-image-fallback.png",
  "/images/og-fallbacks/threads/24_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/25_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/26_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/27_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/28_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/29_threads-og-image-fallback.jpg",
  "/images/og-fallbacks/threads/30_threads-og-image-fallback.jpg",
];

function App() {
  const [htmlInput, setHtmlInput] = useState("");
  const [summary, setSummary] = useState("");
  const [ogImage, setOgImage] = useState("");
  const [scrapedText, setScrapedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [usedHuggingFace, setUsedHuggingFace] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const handleSummarize = async (forceHF = false) => {
    setLoading(true);
    setSummary("");
    setOgImage("");
    setUsedHuggingFace(false);

    try {
      const isDev = window.location.hostname === "localhost";
      const endpoint = `${isDev ? "http://localhost:8000" : "https://tweet-sized-takeaways.onrender.com"
        }/summarize${forceHF ? "/hf" : ""}`;

      const payload = forceHF
        ? { url: htmlInput, text: scrapedText || undefined }
        : { url: htmlInput };

      console.log("📤 Sending request to:", endpoint);
      console.log("📦 Payload:", payload);

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      console.log("📬 Response:", data);

      setSummary(
        data.summary ||
        "🤗 This website doesn't even like Hugging Face — give it a once over and arrive at a summary of your own. 🤷‍♂️"
      );
      if (data.og_image) setOgImage(data.og_image);
      if (data.used_huggingface) setUsedHuggingFace(true);

      if (!forceHF && data.scraped_text) {
        setScrapedText(data.scraped_text);
        console.log("📚 scraped_text saved to state");
      }
    } catch (err) {
      console.error("🔥 Network error:", err);
      setSummary("💥 Backend unreachable or failed. Check console.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (summary) {
      navigator.clipboard.writeText(summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSummarize();
    }
  };

  const hasResult = Boolean(ogImage || summary);
  const isThreadsUrl = htmlInput.toLowerCase().includes("threads.");

  const handlePreviewError = () => {
    if (isThreadsUrl && !THREADS_IMAGE_FALLBACKS.includes(ogImage)) {
      const nextFallback =
        THREADS_IMAGE_FALLBACKS[Math.floor(Math.random() * THREADS_IMAGE_FALLBACKS.length)];
      setOgImage(nextFallback);
    }
  };

  const brandLogo = (
    <div className="brand-logo-wrap">
      <img
        src="/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-master-logo_2048-1a1a1a.png"
        alt="Tweet-Sized Takeaways logo (Twitter bird with X overlay)"
        className="brand-logo"
      />
    </div>
  );

  return (
    <Container className={`container app-shell${hasResult ? " has-result" : ""}`}>
      <Row className="justify-content-center">
        <Col xs={12} className="text-center px-3">
          <h1 className="title">Tweet-Sized Takeaways</h1>

          <Form onKeyDown={handleKeyPress}>
            <Form.Group className="d-flex justify-content-center mb-3">
              <Form.Control
                type="text"
                placeholder="The link you want a summary for..."
                className="custom-input"
                value={htmlInput}
                onChange={(e) => setHtmlInput(e.target.value)}
              />
            </Form.Group>

            <div className="d-flex justify-content-center gap-2 mb-3">
              <Button
                className="twitterblue"
                variant="primary"
                onClick={() => handleSummarize()}
                disabled={loading}
              >
                {loading ? <TstSpinner size={16} /> : "Summarize"}
              </Button>
            </div>
          </Form>

          {!hasResult && brandLogo}

          <div className="result-wrapper">
            {hasResult && (
              <div className="result-layout">
                {ogImage && (
                  <div className="media-preview preview-card">
                    <img
                      src={ogImage}
                      alt="Preview"
                      className="og-image"
                      loading="lazy"
                      onError={handlePreviewError}
                    />
                  </div>
                )}

                {summary && (
                  <div className="takeaway-column">
                    <Card className="summary-card takeaway-card">
                      <Card.Body className="summary-body">
                        <div className="summary-header">
                          <span className="summary-label">📝 280-Character (or less) Takeaway</span>
                        </div>

                        <Card.Text className="summary-text">{summary}</Card.Text>

                        <div className="summary-icons">
                          <div className="tooltip-wrapper">
                            <button
                              className={`icon-copy-btn${copied ? " copied" : ""}`}
                              onClick={handleCopy}
                            >
                              <FontAwesomeIcon icon={copied ? faTwitter : faCopy} />
                            </button>
                            <div className="icon-tooltip">Copy</div>
                          </div>

                          <div className="tooltip-wrapper bird-tooltip">
                            <img
                              src="/images/twitter-died-jetblack.png"
                              alt="Dead Twitter bird"
                              className={`black-deadtwitterbird${usedHuggingFace ? " dimmed" : ""
                                }`}
                            />
                            <div className="icon-tooltip">xTwitter is dead</div>
                          </div>

                          <div className="huggingface-wrapper tooltip-wrapper">
                            <button
                              className="huggingface-btn"
                              onClick={() => {
                                handleSummarize(true);
                                setShowTooltip(true);
                                setTimeout(() => setShowTooltip(false), 1000);
                              }}
                              disabled={loading || usedHuggingFace}
                            >
                              🤗
                            </button>
                            <div className={`icon-tooltip${showTooltip ? " visible" : ""}`}>
                              Hugging Face Takeaway
                            </div>
                          </div>
                        </div>
                      </Card.Body>
                    </Card>

                    {usedHuggingFace && (
                      <p className="hf-note text-muted mt-2 text-center">
                        The Hugging Face summary is up there on the takeaway card. 🤗
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {hasResult && brandLogo}
        </Col>
      </Row>
    </Container>
  );
}

export default App;
