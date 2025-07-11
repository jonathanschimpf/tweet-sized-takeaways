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

import { Link, useLocation } from "react-router-dom";

function App() {
  const [htmlInput, setHtmlInput] = useState("");
  const [summary, setSummary] = useState("");
  const [ogImage, setOgImage] = useState("");
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
      const response = await fetch(
        `http://localhost:8000/summarize${forceHF ? "/hf" : ""}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: htmlInput }),
        }
      );

      const data = await response.json();
      setSummary(data.summary || "⚠️ No summary returned.");
      if (data.og_image) setOgImage(data.og_image);
      if (data.used_huggingface) setUsedHuggingFace(true);
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

          {/* ALREADY USED HF MESSAGE */}
          {usedHuggingFace && (
            <p className="small text-muted">
              The Hugging Face summary is on the takeaway card below.
            </p>
          )}

          {ogImage && (
            <div className="og-image-container mb-3">
              <img
                src={ogImage}
                alt="Preview"
                className="og-image"
                loading="lazy"
              />
            </div>
          )}

          {summary && (
            <Card className="mt-4 summary-card">
              <Card.Body className="summary-body">
                <div className="summary-header">
                  <span className="summary-label">
                    📝 280-Character (or less) Takeaway
                  </span>
                </div>

                <Card.Text className="summary-text">{summary}</Card.Text>

                {/* ICON STRIP BELOW SUMMARY */}
                <div className="summary-icons">
                  {/* COPY BUTTON + TOOLTIP */}
                  <div className="tooltip-wrapper">
                    <button
                      className={`icon-copy-btn${copied ? " copied" : ""}`}
                      onClick={handleCopy}
                    >
                      <FontAwesomeIcon icon={copied ? faTwitter : faCopy} />
                    </button>
                    <div className="icon-tooltip">Copy</div>
                  </div>

                  {/* DEAD TWITTER BIRD + TOOLTIP */}
                  <div className="tooltip-wrapper bird-tooltip">
                    <img
                      src="/images/twitter-died-jetblack.png"
                      alt="Dead Twitter bird"
                      className="black-deadtwitterbird"
                    />
                    <div className="icon-tooltip">xTwitter is dead</div>
                  </div>

                  {/* HUGGING FACE BUTTON + TOOLTIP */}
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
          )}
        </Col>
      </Row>
    </Container>
  );
}

export default App;
