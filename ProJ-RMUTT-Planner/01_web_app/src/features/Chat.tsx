import { copy as uiCopy } from "@/i18n/th";
import { RichText } from "@/components/RichText";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowUp,
  ArrowUpRight,
  Check,
  Copy,
  Info,
  Link2,
  LoaderCircle,
  MessageSquare,
  RotateCcw,
  ShieldCheck,
  Square,
  CalendarDays,
} from "lucide-react";
import { useApiPage } from "@/api/queries";
import { errorText, isMock } from "@/api/client";
import { streamChat } from "@/api/chat-stream";
import type { ChatMessage } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ErrorBox, Feedback, Loading, SourceCards } from "@/components/Common";
import { Mascot } from "@/components/Mascot";
import { useApp } from "@/state";
import { th } from "@/i18n/th";

function MessageCard({
  message,
  copy,
}: {
  message: ChatMessage;
  copy: (text: string) => void;
}) {
  if (message.role === "user")
    return (
      <div className="user-message">
        <div className="user-bubble">{message.content}</div>
        <time>
          {new Date(message.created_at).toLocaleTimeString("th-TH", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </time>
      </div>
    );
  return (
    <article className="assistant-message">
      <Mascot avatar className="answer-avatar" />
      <div className="answer-column">
        <div className="assistant-label">
          CampusMate <span>{uiCopy.chat001}</span>
        </div>
        <div className="answer-card">
          <div className="answer-copy">
            <RichText text={message.content} />
            {message.status !== "complete" && message.id > 0 && (
              <span className="partial-status">
                {th.status[message.status]}
              </span>
            )}
          </div>
          {(message.sources?.length ?? 0) > 0 && (
            <div className="answer-sources">
              <h3>
                <Link2 size={16} />
                {uiCopy.chat002}
                <span>{message.sources?.length}</span>
              </h3>
              <SourceCards sources={message.sources ?? []} />
            </div>
          )}
          {message.id > 0 && (
            <div className="answer-actions">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copy(message.content)}
                aria-label={uiCopy.chat003}
              >
                <Copy />
                {uiCopy.chat004}
              </Button>
              <span className="action-divider" />
              {message.status === "complete" && (
                <Feedback target="chat_message" id={String(message.id)} />
              )}
              <span className="response-meta">
                {isMock ? uiCopy.chat005 : ""}
              </span>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
export default function Chat() {
  const { sessionId } = useParams(),
    navigate = useNavigate(),
    cache = useQueryClient(),
    { draft, notify } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]),
    [text, setText] = useState(""),
    [running, setRunning] = useState(false),
    [tool, setTool] = useState(""),
    [error, setError] = useState<unknown>(null),
    [lastText, setLastText] = useState("");
  const controller = useRef<AbortController | null>(null),
    runningRef = useRef(false),
    ownSession = useRef<number | null>(null),
    generation = useRef(0),
    bottom = useRef<HTMLDivElement>(null),
    input = useRef<HTMLTextAreaElement>(null);
  const history = useApiPage<ChatMessage>(
    ["chat-messages", sessionId],
    `/chat/sessions/${sessionId}/messages`,
    !!sessionId && !running,
  );
  useEffect(() => {
    if (runningRef.current && String(ownSession.current) !== sessionId) {
      generation.current++;
      controller.current?.abort();
      runningRef.current = false;
      setRunning(false);
    }
    if (!runningRef.current) {
      setMessages([]);
      setError(null);
      setText("");
    }
  }, [sessionId]);
  useEffect(() => {
    if (history.data && !running) setMessages(history.data.items);
  }, [history.data, running]);
  useEffect(
    () => () => {
      generation.current++;
      controller.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (running || messages.length > 2)
      bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, running]);
  async function send(value = text) {
    const content = value.trim();
    if (!content || runningRef.current) return;
    runningRef.current = true;
    const run = ++generation.current;
    setRunning(true);
    setText("");
    setError(null);
    setLastText(content);
    setTool(uiCopy.chat006);
    controller.current = new AbortController();
    ownSession.current = sessionId ? Number(sessionId) : null;
    const time = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      {
        id: -1,
        role: "user",
        content,
        created_at: time,
        sources: [],
        status: "complete",
      },
      {
        id: -2,
        role: "assistant",
        content: "",
        created_at: time,
        sources: [],
        status: "interrupted",
      },
    ]);
    const update = (change: Partial<ChatMessage>) => {
      if (generation.current === run)
        setMessages((prev) =>
          prev.map((m) => (m.id === -2 ? { ...m, ...change } : m)),
        );
    };
    try {
      const outcome = await streamChat(
        {
          session_id: ownSession.current,
          message: content,
          plan_draft: draft.length
            ? { term: "1/2569", section_ids: draft.map((s) => s.section_id) }
            : null,
        },
        (event) => {
          if (generation.current !== run) return;
          if (event.type === "session") {
            ownSession.current = event.session_id;
            if (!sessionId)
              navigate(`/chat/${event.session_id}`, { replace: true });
          }
          if (event.type === "tool_start")
            setTool(th.tools[event.tool] || uiCopy.chat007);
          if (event.type === "tool_end") setTool(uiCopy.chat008);
          if (event.type === "token") {
            setTool("");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === -2 ? { ...m, content: m.content + event.text } : m,
              ),
            );
          }
          if (event.type === "sources") update({ sources: event.items });
          if (event.type === "done")
            update({ id: event.message_id, status: "complete" });
          if (event.type === "error") {
            update({ id: Date.now(), status: "interrupted" });
            setError(new Error(event.message));
          }
        },
        controller.current.signal,
      );
      if (outcome === "interrupted" && generation.current === run) {
        update({ id: Date.now(), status: "interrupted" });
        setError(new Error(uiCopy.chat009));
      }
    } catch (e) {
      if (generation.current === run) {
        if (e instanceof DOMException && e.name === "AbortError") {
          update({ id: Date.now(), status: "cancelled" });
          notify(uiCopy.chat010);
        } else {
          update({ id: Date.now(), status: "interrupted" });
          setError(e);
        }
      }
    } finally {
      if (generation.current === run) {
        runningRef.current = false;
        setRunning(false);
        setTool("");
        void cache.invalidateQueries({ queryKey: ["chat-sessions"] });
        if (ownSession.current)
          void cache.invalidateQueries({
            queryKey: ["chat-messages", String(ownSession.current)],
          });
        input.current?.focus();
      }
    }
  }
  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      notify(uiCopy.chat011);
    } catch {
      notify(uiCopy.chat012);
    }
  }
  return (
    <>
      <section className="chat-scroll">
        <div className="chat-inner">
          {isMock && (
            <div className="demo-banner">
              <Info size={17} />
              <span>{th.demoHint}</span>
              <span className="demo-label">{uiCopy.chat013}</span>
            </div>
          )}
          <ErrorBox error={history.error} />
          {history.isLoading ? (
            <Loading />
          ) : messages.length ? (
            <div
              className="message-list"
              aria-live="polite"
              aria-relevant="additions"
            >
              {messages
                .filter(
                  (m) =>
                    m.content ||
                    (m.role === "assistant" &&
                      m.id > 0 &&
                      m.status !== "complete"),
                )
                .map((m) => (
                  <MessageCard key={m.id} message={m} copy={copy} />
                ))}
              {running && tool && (
                <div className="thinking" role="status">
                  <Mascot avatar />
                  <span>
                    <i />
                    <i />
                    <i />
                  </span>
                  <small>{tool}</small>
                </div>
              )}
              {!running && !error && (
                <div className="follow-ups">
                  <span>{uiCopy.chat014}</span>
                  {[uiCopy.chat015, uiCopy.chat016].map((t) => (
                    <button key={t} onClick={() => send(t)}>
                      {t}
                      <ArrowUpRight size={14} />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="welcome">
              <Mascot />
              <span className="eyebrow">{uiCopy.app002}</span>
              <h2>{th.greeting}</h2>
              <p>{th.emptyChat}</p>
              <div className="welcome-suggestions">
                {[uiCopy.chat017, uiCopy.chat018, uiCopy.chat019].map((t) => (
                  <button key={t} onClick={() => send(t)}>
                    <MessageSquare size={18} />
                    <span>{t}</span>
                    <ArrowUpRight size={17} />
                  </button>
                ))}
              </div>
            </div>
          )}
          <div ref={bottom} />
        </div>
      </section>
      <footer className="composer-area">
        <div className="composer-inner">
          <ErrorBox error={error} />
          {!!error && !running && (
            <Button variant="ghost" size="sm" onClick={() => send(lastText)}>
              <RotateCcw />
              {uiCopy.chat020}
            </Button>
          )}
          {draft.length > 0 && (
            <div className="attachment-chip">
              <CalendarDays size={15} />
              {uiCopy.chat021}
              {draft.length}
              {uiCopy.chat022}
            </div>
          )}
          <form
            className="composer"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              void send();
            }}
          >
            <span className="composer-spark">
              <MessageSquare size={21} />
            </span>
            <Textarea
              ref={input}
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={4000}
              rows={1}
              disabled={running}
              placeholder={th.placeholder}
              aria-label={uiCopy.chat023}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            {running ? (
              <Button
                type="button"
                className="send-button"
                onClick={() => controller.current?.abort()}
                aria-label={uiCopy.chat024}
              >
                <Square size={18} />
              </Button>
            ) : (
              <Button
                type="submit"
                className="send-button"
                disabled={!text.trim()}
                aria-label={uiCopy.chat025}
              >
                <ArrowUp size={23} />
              </Button>
            )}
          </form>
          <div className="composer-hints">
            <span>{uiCopy.chat026}</span>
            <span>
              <kbd>Enter</kbd>
              {uiCopy.chat027}
              <span className="hint-sep">/</span> <kbd>Shift + Enter</kbd>
              {uiCopy.chat028}
            </span>
          </div>
          <p className="disclaimer">
            <ShieldCheck size={12} />
            {th.disclaimer}
          </p>
        </div>
      </footer>
    </>
  );
}
