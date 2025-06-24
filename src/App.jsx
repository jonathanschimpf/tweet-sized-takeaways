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

// EVER-PRESENT NAV ROUTING
import { Link, useLocation } from "react-router-dom";

function App() {
  const [htmlInput, setHtmlInput] = useState("");
  const [summary, setSummary] = useState("");
  const [ogImage, setOgImage] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const location = useLocation();

  const handleSummarize = async () => {
    setLoading(true);
    setSummary("");
    setOgImage("");
    try {
      const response = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: htmlInput }),
      });

      const data = await response.json();
      setSummary(data.summary || "⚠️ No summary returned.");
      if (data.og_image) {
        setOgImage(data.og_image);
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
          {/* APP TITLE */}
          <h1 className="title">Tweet-Sized Takeaways</h1>

          {/* INPUT */}
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
                onClick={handleSummarize}
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

          {/* OG IMAGE */}
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

          {/* SUMMARY CARD */}
          {summary && (
            <Card className="mt-4 summary-card">
              <Card.Body className="position-relative">
                <Card.Title>📝 280-Character (or less) Takeaway</Card.Title>
                <Card.Text className="position-relative" style={{ zIndex: 1 }}>
                  {summary}
                </Card.Text>
                <button
                  className={`icon-copy-btn${copied ? " copied" : ""}`}
                  onClick={handleCopy}
                >
                  <FontAwesomeIcon icon={copied ? faTwitter : faCopy} />
                </button>
                <img
                  src="/images/twitter-died-jetblack.png"
                  alt="Dead Twitter bird"
                  className="summary-background"
                />
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>
    </Container>
  );
}

export default App;
