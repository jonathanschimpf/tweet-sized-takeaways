import { useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import {
  Container,
  Form,
  Button,
  Card,
  Row,
  Col,
  Spinner,
} from "react-bootstrap";
import "./App.css";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { faTwitter } from "@fortawesome/free-brands-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faCopy, faTwitter);

import { useLocation } from "react-router-dom";

function App() {
  const [htmlInput, setHtmlInput] = useState("");
  const [summary, setSummary] = useState("");
  const [ogImage, setOgImage] = useState("");
  const [scrapedText, setScrapedText] = useState(""); // 🧠 TRACK TEXT
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [usedHuggingFace, setUsedHuggingFace] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const location = useLocation();

  const handleSummarize = async (forceHF = false) => {
    setLoading(true);
    setSummary("");
    setOgImage("");
    setUsedHuggingFace(false);

    try {
      const isDev = window.location.hostname === "localhost";
      const endpoint = `${isDev ? "http://localhost:8000" : "https://tweet-sized-takeaways.onrender.com"}/summarize${forceHF ? "/hf" : ""}`;

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

      // ✅ STORE SCRAPED TEXT ON NON-HF RUN
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

  return (
    <Container className="container">
      <Row className="justify-content-center">
        <Col xs={12} className="text-center px-3">
          <h1 className="title">Tweet-Sized Takeaways</h1>

          <Form onKeyDown={handleKeyPress}>
            <Form.Group className="d-flex justify-content-center mb-3">
              <Form.Control
                type="text"
                placeholder="Paste a link you want a summary for..."
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
                {loading ? (
                  <Spinner
                    animation="border"
                    size="sm"
                    style={{ color: "#1da1f2", borderWidth: "0.15em" }}
                  />
                ) : (
                  "Summarize"
                )}
              </Button>
            </div>
          </Form>

          <div className="result-wrapper">
            {ogImage && (
              <img
                src={ogImage}
                alt="Preview"
                className="og-image"
                loading="lazy"
              />
            )}

            {summary && (
              <>
                <Card className="mt-4 summary-card">
                  <Card.Body className="summary-body">
                    <div className="summary-header">
                      <span className="summary-label">
                        📝 280-Character (or less) Takeaway
                      </span>
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
                          className={`black-deadtwitterbird${usedHuggingFace ? " dimmed" : ""}`}
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
                        <div
                          className={`icon-tooltip${showTooltip ? " visible" : ""}`}
                        >
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
              </>
            )}
          </div>
        </Col>
      </Row>
    </Container>
  );
}

export default App;
