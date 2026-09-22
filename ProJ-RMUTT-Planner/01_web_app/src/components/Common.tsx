import { copy as uiCopy } from "@/i18n/th";
import { useState, type ReactNode } from "react";
import {
  AlertCircle,
  FileText,
  LoaderCircle,
  ThumbsDown,
  ThumbsUp,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, errorText, isMock } from "@/api/client";
import { useApp } from "@/state";
import type { SourceItem } from "@/api/types";
export function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <div className="error-box" role="alert">
      <AlertCircle size={18} />
      <span>{errorText(error)}</span>
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="loading-view" role="status">
      <LoaderCircle className="animate-spin" size={22} />
      {uiCopy.common001}
    </div>
  );
}
export function Empty({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon}
      <h3>{title}</h3>
      {children}
    </div>
  );
}
export function Feedback({ target, id }: { target: string; id: string }) {
  const [vote, setVote] = useState<1 | -1 | null>(null),
    [pending, setPending] = useState(false);
  const { notify } = useApp();
  // 02's `rating` เป็นสเกล 1–5 ดาว ไม่ใช่ signed vote — thumbs-up/down ของ UI นี้ map เป็นปลายสเกล
  // (thumbs-up=5, thumbs-down=1) เพื่อไม่ให้ 422 โดยไม่ต้องออกแบบ UI ใหม่ทั้งหมด (ดู COMPAT_FIX_REPORT.md P1-F)
  async function send(vote: 1 | -1) {
    setPending(true);
    try {
      await api.post("/feedback", {
        target_type: target,
        target_id: id,
        rating: vote === 1 ? 5 : 1,
        reason: "",
      });
      setVote(vote);
      notify(uiCopy.common002);
    } catch (e) {
      notify(errorText(e));
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        disabled={pending}
        aria-label={uiCopy.common003}
        aria-pressed={vote === 1}
        onClick={() => send(1)}
        className={vote === 1 ? "voted" : ""}
      >
        <ThumbsUp />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        disabled={pending}
        aria-label={uiCopy.common004}
        aria-pressed={vote === -1}
        onClick={() => send(-1)}
        className={vote === -1 ? "voted" : ""}
      >
        <ThumbsDown />
      </Button>
    </>
  );
}
export function SourceCards({ sources }: { sources: SourceItem[] }) {
  const [chosen, setChosen] = useState<SourceItem | null>(null);
  return (
    <>
      <div className="source-grid">
        {sources.map((s, i) => (
          <button
            className="source-card"
            key={`${s.document_id}-${i}`}
            onClick={() => setChosen(s)}
          >
            <span className="file-icon">
              <FileText size={23} />
            </span>
            <span>
              <strong>{s.title}</strong>
              <small>
                {[s.section, s.page ? uiCopy.courses033 + s.page + "" : null]
                  .filter(Boolean)
                  .join(" • ")}
              </small>
            </span>
            <span className="source-hint">{uiCopy.common005}</span>
          </button>
        ))}
      </div>
      <Dialog open={!!chosen} onOpenChange={(open) => !open && setChosen(null)}>
        <DialogContent>
          <DialogHeader>
            <span className="dialog-symbol">
              <FileText />
            </span>
            <DialogTitle>{chosen?.title}</DialogTitle>
            <DialogDescription>
              {chosen?.section}{" "}
              {chosen?.page ? uiCopy.common006 + chosen.page + "" : ""}
            </DialogDescription>
          </DialogHeader>
          <p className="muted-copy">
            {isMock ? uiCopy.common007 : uiCopy.common008}
          </p>
          {chosen?.url && /^https?:\/\//i.test(chosen.url) ? (
            <Button asChild>
              <a href={chosen.url} target="_blank" rel="noopener noreferrer">
                {uiCopy.common009}
                <ExternalLink />
              </a>
            </Button>
          ) : (
            <div className="info-box">{uiCopy.common010}</div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
