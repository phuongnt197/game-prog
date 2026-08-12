import { useEffect, useMemo, useState } from "react";
import { get, streamPost } from "../api/client";
import { MarkdownContent } from "../components/MarkdownContent";
import { HighlightedCode } from "../components/SyntaxCode";


const ANIMATION_PLAN_MARKER = "===ANIMATION_PLAN===";
const EXAMPLES = [
  "Show how a for loop moves through a Python list.",
  "Explain recursion using a stack of function calls.",
  "Visualize how binary search removes half of the choices each step.",
];


export function AiEducationPage() {
  const [question, setQuestion] = useState("");
  const [capability, setCapability] = useState();
  const [streamed, setStreamed] = useState("");
  const [status, setStatus] = useState("");
  const [lesson, setLesson] = useState();
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    get("/api/ai-education/capabilities")
      .then(setCapability)
      .catch((nextError) => setError(nextError.message));
  }, []);

  const preview = useMemo(() => parseEducationPreview(streamed), [streamed]);
  const explanation = lesson?.explanation || preview.explanation;
  const source = lesson?.manim_code || preview.animationPlan;
  const sourceLanguage = lesson ? "python" : "json";

  const generate = async (event) => {
    event.preventDefault();
    const nextQuestion = question.trim();
    if (nextQuestion.length < 3 || generating || capability?.renderer_available === false) return;
    setGenerating(true);
    setLesson(undefined);
    setStreamed("");
    setError("");
    setStatus("Connecting to the AI visual tutor…");
    try {
      const finalEvent = await streamPost("/api/ai-education/generate", { question: nextQuestion }, (streamEvent) => {
        if (streamEvent.type === "status") setStatus(streamEvent.message);
        if (streamEvent.type === "reset") setStreamed("");
        if (streamEvent.type === "delta") setStreamed((current) => current + streamEvent.content);
      });
      if (!finalEvent?.video_url) throw new Error("The visual tutor did not return a lesson video.");
      setLesson({
        ...finalEvent,
        video_url: `${finalEvent.video_url}?generated=${Date.now()}`,
      });
      setStreamed("");
      setStatus("Lesson video ready");
    } catch (nextError) {
      setError(nextError.message);
      setStatus("");
    } finally {
      setGenerating(false);
    }
  };

  return <div className="ai-education-page">
    <div className="education-guide-column">
      <section className="surface education-prompt-panel">
        <header>
          <div><span className="eyebrow">Ask · Generate · Visualize</span><h2>AI visual tutor</h2></div>
          <span className={`status ${capability?.renderer_available ? "success" : capability ? "danger" : "info"}`}>
            {capability?.renderer_available ? "✓ Manim ready" : capability ? "× Renderer unavailable" : "Checking renderer…"}
          </span>
        </header>
        <p className="education-intro">Ask about a programming, mathematics, or course concept. The AI will arrange visual objects and movements, then the server will compile the plan into a Manim video.</p>
        <form onSubmit={generate} className="education-question-form">
          <label>What should the video explain?
            <textarea
              rows="5"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="For example: Explain recursion using a stack of function calls."
              disabled={generating}
            />
          </label>
          <button className="primary" disabled={generating || question.trim().length < 3 || capability?.renderer_available === false}>
            {generating ? "Creating lesson…" : "Generate lesson video"}
          </button>
        </form>
        <div className="education-examples"><strong>Try an example</strong>{EXAMPLES.map((example) => <button key={example} onClick={() => setQuestion(example)} disabled={generating}>{example}</button>)}</div>
        {capability?.renderer_available === false && <div className="notice error education-notice">The server needs Manim before it can render videos. Install the backend requirements and restart FastAPI.</div>}
        {status && <div className={`education-generation-status ${generating ? "is-active" : "is-ready"}`}><span aria-hidden="true" />{status}</div>}
        {error && <div className="error-banner">{error}</div>}
      </section>

      <section className="surface education-explanation-panel">
        <header><div><span className="eyebrow">Learning guide</span><h2>What to watch for</h2></div>{generating && explanation && <span className="status info">Streaming…</span>}</header>
        <div className={`education-explanation ${generating ? "is-streaming" : ""}`}>
          {explanation ? <MarkdownContent content={explanation} /> : <div className="empty-state"><strong>Your explanation will appear here</strong><p>The video and its key ideas are generated together.</p></div>}
        </div>
      </section>
    </div>

    <div className="education-output-column">
      <section className="surface education-video-panel">
        <header><div><span className="eyebrow">Rendered lesson</span><h2>Concept video</h2></div>{lesson && <span className="status success">✓ Ready to play</span>}</header>
        <div className="education-video-stage">
          {lesson?.video_url
            ? <video key={lesson.video_url} controls playsInline preload="metadata"><source src={lesson.video_url} type="video/mp4" />Your browser cannot play this MP4 video.</video>
            : <div className={`education-video-placeholder ${generating ? "is-generating" : ""}`}><div className="education-orbit" aria-hidden="true"><span /><span /><span /></div><h3>{generating ? "Building your animation" : "Your concept video will appear here"}</h3><p>{generating ? "The AI is designing objects and movements; Manim will render them next." : "Choose an example or ask your own question to begin."}</p></div>}
        </div>
        <p className="education-disclaimer">AI-generated explanations can be imperfect. Compare important details with your course materials.</p>
      </section>

      <section className="surface education-code-panel">
        <header><div><span className="eyebrow">{lesson ? "Compiled source · Read only" : "AI animation plan · Read only"}</span><h2>{lesson ? "Manim scene" : "Visual animation plan"}</h2></div>{generating && source && <span className="status info">Designing motion…</span>}</header>
        <div className="education-code-view">
          {source ? <HighlightedCode code={source} language={sourceLanguage} ariaLabel={lesson ? "Compiled Manim scene code" : "AI-generated animation plan"} /> : <div className="empty-state">The AI's visual objects and movements will stream here before rendering.</div>}
        </div>
      </section>
    </div>
  </div>;
}


export function parseEducationPreview(raw = "") {
  const markerIndex = raw.indexOf(ANIMATION_PLAN_MARKER);
  const explanation = (markerIndex >= 0 ? raw.slice(0, markerIndex) : raw)
    .replace(/^\s*EXPLANATION\s*:\s*/i, "")
    .trim();
  const rawPlan = markerIndex >= 0 ? raw.slice(markerIndex + ANIMATION_PLAN_MARKER.length) : "";
  const animationPlan = rawPlan
    .replace(/^\s*```(?:json)?\s*/i, "")
    .replace(/\s*```\s*$/i, "")
    .trimStart();
  return { explanation, animationPlan };
}
