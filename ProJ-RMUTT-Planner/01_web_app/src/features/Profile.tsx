import { copy as uiCopy } from "@/i18n/th";
import { useRef, useState, type ChangeEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Download,
  FileCode2,
  GraduationCap,
  LoaderCircle,
  Upload,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { api, isMock } from "@/api/client";
import { useApiQuery } from "@/api/queries";
import type { ImportResult, StudentProfile, TranscriptResponse } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Empty, ErrorBox, Loading } from "@/components/Common";
import { useApp } from "@/state";
export default function Profile() {
  const profile = useApiQuery<StudentProfile>(
      ["profile"],
      "/students/me/profile",
    ),
    // /students/me/transcript คืน {courses, credits_by_category} ตรงๆ ไม่ได้ห่อแบบ cursor pagination
    transcript = useApiQuery<TranscriptResponse>(
      ["transcript"],
      "/students/me/transcript",
    ),
    cache = useQueryClient(),
    { notify, user } = useApp(),
    file = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null),
    [result, setResult] = useState<ImportResult | null>(null);
  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    e.target.value = "";
    if (!selected) return;
    setResult(null);
    setError(null);
    if (!selected.name.toLowerCase().endsWith(".html")) {
      setError(new Error(uiCopy.profile001));
      return;
    }
    if (selected.size > 2 * 1024 * 1024) {
      setError(new Error(uiCopy.profile002));
      return;
    }
    const form = new FormData();
    form.append("file", selected);
    setPending(true);
    try {
      setResult(await api.post<ImportResult>("/students/me/import", form));
      await cache.invalidateQueries({ queryKey: ["transcript"] });
      await cache.invalidateQueries({ queryKey: ["profile"] });
      notify(uiCopy.profile003);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  if (profile.isLoading) return <Loading />;
  const stats = profile.data;
  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">{uiCopy.profile004}</span>
          <h2>{uiCopy.profile005}</h2>
          <p>{uiCopy.profile006}</p>
        </div>
        <span className="large-feature-icon">
          <GraduationCap size={29} />
        </span>
      </div>
      <ErrorBox error={profile.error} />
      {stats && (
        <>
          <div className="student-card">
            <span className="student-avatar">{uiCopy.app023}</span>
            <div>
              <h3>{user?.username}</h3>
              <p>
                {stats.student_id} • {stats.program_name}
              </p>
              <small>
                {uiCopy.profile007}
                {stats.year_level}
                {uiCopy.profile008}
              </small>
            </div>
            <span className="student-badge">{uiCopy.profile009}</span>
          </div>
          <div className="stat-grid">
            <div>
              <span>{uiCopy.profile010}</span>
              <strong>
                {stats.gpax.toFixed(2)}
                <small>GPAX</small>
              </strong>
            </div>
            <div>
              <span>{uiCopy.profile011}</span>
              <strong>
                {stats.credits_earned}
                <small>{uiCopy.courses028}</small>
              </strong>
            </div>
            <div>
              <span>{uiCopy.profile012}</span>
              <strong>
                {uiCopy.profile013}
                {stats.year_level}
                <small>{stats.program_name}</small>
              </strong>
            </div>
          </div>
        </>
      )}
      <div className="import-card">
        <span className="import-icon">
          <FileCode2 size={29} />
        </span>
        <div>
          <h3>{uiCopy.profile014}</h3>
          <p>{isMock ? uiCopy.profile015 : uiCopy.profile016}</p>
          <small>{uiCopy.profile017}</small>
        </div>
        <div className="button-row">
          {isMock && (
            <Button variant="outline" asChild>
              <a href="/sample-transcript.html" download>
                <Download />
                {uiCopy.profile018}
              </a>
            </Button>
          )}
          <Button disabled={pending} onClick={() => file.current?.click()}>
            {pending ? <LoaderCircle className="animate-spin" /> : <Upload />}
            {uiCopy.profile019}
          </Button>
        </div>
        <input
          ref={file}
          className="sr-only"
          type="file"
          accept=".html"
          onChange={upload}
          aria-label={uiCopy.profile020}
        />
      </div>
      <ErrorBox error={error} />
      {result && (
        <div className="validation-panel valid" role="status">
          <div className="validation-title">
            <CheckCircle2 size={20} />
            <strong>
              {uiCopy.profile021}
              {result.imported_courses}
              {uiCopy.profile022}
            </strong>
          </div>
          <p>
            {uiCopy.profile023}
            {(result.retake_required ?? []).join(", ") || uiCopy.profile024}
          </p>
          {(result.warnings ?? []).map((w) => (
            <small key={w}>{w}</small>
          ))}
        </div>
      )}
      <div className="results-heading">
        <span>{uiCopy.profile025}</span>
        <small>
          {transcript.data?.courses.length || 0}
          {uiCopy.profile026}
        </small>
      </div>
      <ErrorBox error={transcript.error} />
      {transcript.isLoading ? (
        <Loading />
      ) : transcript.data?.courses.length ? (
        <div className="table-scroll">
          <table className="transcript-table">
            <thead>
              <tr>
                <th>{uiCopy.profile027}</th>
                <th>{uiCopy.profile028}</th>
                <th>{uiCopy.courses025}</th>
                <th>{uiCopy.courses028}</th>
                <th>{uiCopy.profile029}</th>
              </tr>
            </thead>
            <tbody>
              {transcript.data.courses.map((r) => (
                <tr key={r.course_code}>
                  <td>{r.course_code}</td>
                  <td>{r.course_name_th}</td>
                  <td>{r.term}</td>
                  <td>{r.credits}</td>
                  <td>
                    <span
                      className={r.grade === "F" ? "grade failed" : "grade"}
                    >
                      {r.grade}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty icon={<FileText size={38} />} title={uiCopy.profile030}>
          <p>{uiCopy.profile031}</p>
        </Empty>
      )}
    </section>
  );
}
