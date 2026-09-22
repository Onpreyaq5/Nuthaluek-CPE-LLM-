import { copy as uiCopy } from "@/i18n/th";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FolderHeart,
  LoaderCircle,
  MessageSquare,
  Plus,
  Save,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { api, requestPage } from "@/api/client";
import { useApiQuery, useApiPage } from "@/api/queries";
import type {
  AutoPlanResponse,
  Day,
  GeneratedPlan,
  PlanCreateResponse,
  PlanDetail as PlanDetailType,
  PlanSummary,
  Section,
  SourceItem,
  Validation,
} from "@/api/types";
import { sectionNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  ErrorBox,
  Feedback,
  Loading,
  SourceCards,
} from "@/components/Common";
import { Timetable, days } from "@/components/Timetable";
import { SectionsList } from "./Courses";
import { useApp } from "@/state";
import { th } from "@/i18n/th";

function useValidation(sections: Section[]) {
  const ids = sections
      .map((s) => s.section_id)
      .sort()
      .join(","),
    [settled, setSettled] = useState(ids);
  useEffect(() => {
    const t = setTimeout(() => setSettled(ids), 400);
    return () => clearTimeout(t);
  }, [ids]);
  const query = useQuery({
    queryKey: ["validation", settled],
    queryFn: ({ signal }) =>
      api.post<Validation>(
        "/plans/validate",
        {
          term: "1/2569",
          section_ids: settled ? settled.split(",") : [],
        },
        signal,
      ),
    retry: false,
  });
  return { ...query, waiting: ids !== settled || query.isFetching };
}
function ValidationPanel({
  value,
  busy,
}: {
  value?: Validation;
  busy?: boolean;
}) {
  if (busy)
    return (
      <div className="validation-panel">
        <LoaderCircle className="animate-spin" size={18} />
        {uiCopy.plans001}
      </div>
    );
  if (!value) return null;
  return (
    <div
      className={`validation-panel ${value.summary.is_valid ? "valid" : "invalid"}`}
    >
      <div className="validation-title">
        {value.summary.is_valid ? (
          <CheckCircle2 size={21} />
        ) : (
          <AlertTriangle size={21} />
        )}
        <strong>
          {value.summary.is_valid ? uiCopy.plans002 : uiCopy.plans003}
        </strong>
        <span>
          {value.summary.total_credits}
          {uiCopy.plans004}
          {value.summary.section_count}
          {uiCopy.chat022}
        </span>
      </div>
      {(value.conflicts ?? []).map((c, i) => (
        <p key={i}>{c.message}</p>
      ))}
      {(value.warnings ?? []).map((w, i) => (
        <p key={i}>{w.message}</p>
      ))}
      <small>{uiCopy.plans005}</small>
    </div>
  );
}
export function SavePlan({
  sections,
  disabled = false,
  onSaved,
}: {
  sections: Section[];
  disabled?: boolean;
  onSaved?: (planId: number) => void;
}) {
  const [open, setOpen] = useState(false),
    [name, setName] = useState(""),
    [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null),
    cache = useQueryClient(),
    { notify } = useApp();
  async function save() {
    setPending(true);
    setError(null);
    try {
      const res = await api.post<PlanCreateResponse>("/plans", {
        name,
        term: "1/2569",
        section_ids: sections.map((s) => s.section_id),
      });
      await cache.invalidateQueries({ queryKey: ["plans"] });
      setOpen(false);
      setName("");
      notify(uiCopy.plans006);
      onSaved?.(res.plan_id);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <Button
        disabled={disabled || !sections.length}
        onClick={() => {
          setError(null);
          setOpen(true);
        }}
      >
        <Save />
        {uiCopy.plans007}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <span className="dialog-symbol">
              <Save />
            </span>
            <DialogTitle>{uiCopy.plans008}</DialogTitle>
            <DialogDescription>{uiCopy.plans009}</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
            className="stack-form"
          >
            <label htmlFor="plan-name">{uiCopy.plans010}</label>
            <input
              id="plan-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={uiCopy.plans011}
              required
              maxLength={80}
            />
            <ErrorBox error={error} />
            <Button disabled={pending || !name.trim()}>
              {pending ? <LoaderCircle className="animate-spin" /> : <Save />}
              {uiCopy.plans012}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
export function Planner() {
  const { draft, setDraft } = useApp(),
    navigate = useNavigate(),
    [selected, setSelected] = useState<Section | null>(null),
    validation = useValidation(draft);
  return (
    <section className="page-content planner-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">{uiCopy.plans013}</span>
          <h2>{uiCopy.plans014}</h2>
          <p>{uiCopy.plans015}</p>
        </div>
        <div className="button-row">
          <Button variant="outline" asChild>
            <Link to="/courses">
              <Plus />
              {uiCopy.plans016}
            </Link>
          </Button>
          <SavePlan
            sections={draft}
            disabled={validation.waiting || !validation.data?.summary.is_valid}
          />
        </div>
      </div>
      <div className="planner-toolbar">
        <span>
          <CalendarDays size={18} />
          {th.term}
        </span>
        <div className="button-row">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/plans/auto">
              <Sparkles />
              {uiCopy.plans017}
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!draft.length}
            onClick={() => navigate("/chat")}
          >
            <MessageSquare />
            {uiCopy.plans018}
          </Button>
        </div>
      </div>
      <ErrorBox error={validation.error} />
      {draft.length ? (
        <>
          <ValidationPanel value={validation.data} busy={validation.waiting} />
          <Timetable
            sections={draft}
            validation={validation.data}
            onSelect={setSelected}
          />
          <div className="selected-heading">
            <h3>
              {uiCopy.plans019}
              <span>{draft.length}</span>
            </h3>
            <small>{uiCopy.plans020}</small>
          </div>
          <div className="selected-list">
            {draft.map((s, i) => (
              <div className="selected-course" key={s.section_id}>
                <span className={`course-dot color-${i % 5}`} />
                <div>
                  <strong>
                    {s.course_code} • {s.course_name_th}
                  </strong>
                  <small>
                    Section {sectionNumber(s.section_id)} • {s.teacher}
                  </small>
                </div>
                <span>
                  {s.credits}
                  {uiCopy.plans021}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={uiCopy.plans022 + s.course_code + uiCopy.plans023}
                  onClick={() =>
                    setDraft(draft.filter((d) => d.section_id !== s.section_id))
                  }
                >
                  <X size={17} />
                </Button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <Empty icon={<CalendarDays size={44} />} title={uiCopy.plans024}>
          <p>{uiCopy.plans025}</p>
          <Button asChild>
            <Link to="/courses">
              <Plus />
              {uiCopy.plans026}
            </Link>
          </Button>
        </Empty>
      )}
      <Dialog
        open={!!selected}
        onOpenChange={(open) => !open && setSelected(null)}
      >
        <DialogContent className="wide-dialog">
          <DialogHeader>
            <DialogTitle>
              {uiCopy.plans027}
              {selected?.course_code}
            </DialogTitle>
            <DialogDescription>{selected?.course_name_th}</DialogDescription>
          </DialogHeader>
          {selected && (
            <>
              {validation.data?.conflicts
                ?.filter((c) => c.section_ids?.includes(selected.section_id))
                .map((c, i) => (
                  <div className="error-box" key={i}>
                    <AlertTriangle size={18} />
                    {c.message}
                  </div>
                ))}
              <SectionsList
                code={selected.course_code}
                selectedIds={draft.map((s) => s.section_id)}
                onSelect={(s) => {
                  setDraft(
                    draft.map((d) => (d.course_code === s.course_code ? s : d)),
                  );
                  setSelected(null);
                }}
              />
            </>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
export function Plans() {
  const query = useApiPage<PlanSummary>(["plans"], "/plans"),
    cache = useQueryClient(),
    { notify } = useApp(),
    [deleting, setDeleting] = useState<PlanSummary | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  async function remove() {
    if (!deleting) return;
    setBusy(true);
    setError(null);
    try {
      await api.delete(`/plans/${deleting.id}`);
      await cache.invalidateQueries({ queryKey: ["plans"] });
      setDeleting(null);
      notify(uiCopy.plans028);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">{uiCopy.plans029}</span>
          <h2>{uiCopy.plans030}</h2>
          <p>{uiCopy.plans031}</p>
        </div>
        <Button asChild>
          <Link to="/planner">
            <Plus />
            {uiCopy.plans032}
          </Link>
        </Button>
      </div>
      <ErrorBox error={query.error} />
      {query.isLoading ? (
        <Loading />
      ) : query.data?.items.length ? (
        <div className="plans-grid">
          {query.data.items.map((plan) => (
            <article className="saved-plan" key={plan.id}>
              <div className="saved-plan-top">
                <span className="plan-symbol">
                  <CalendarDays size={24} />
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={uiCopy.plans033 + plan.name + ""}
                  onClick={() => {
                    setError(null);
                    setDeleting(plan);
                  }}
                >
                  <Trash2 size={17} />
                </Button>
              </div>
              <Link to={`/plans/${plan.id}`}>
                <h3>{plan.name}</h3>
                <p>
                  {uiCopy.plans034}
                  {plan.term}
                </p>
                <div className="plan-card-footer">
                  <span>
                    {plan.total_credits}
                    {uiCopy.plans021}
                  </span>
                  <span>
                    {uiCopy.plans035}
                    <ArrowRight size={16} />
                  </span>
                </div>
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <Empty icon={<FolderHeart size={40} />} title={uiCopy.plans036}>
          <p>{uiCopy.plans037}</p>
          <Button asChild>
            <Link to="/planner">
              {uiCopy.plans038}
              <ArrowRight />
            </Link>
          </Button>
        </Empty>
      )}
      <Dialog
        open={!!deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{uiCopy.plans039}</DialogTitle>
            <DialogDescription>
              {uiCopy.plans040}
              {deleting?.name}
              {uiCopy.plans041}
            </DialogDescription>
          </DialogHeader>
          <ErrorBox error={error} />
          <div className="button-row">
            <Button variant="outline" onClick={() => setDeleting(null)}>
              {uiCopy.plans042}
            </Button>
            <Button variant="destructive" disabled={busy} onClick={remove}>
              {busy ? <LoaderCircle className="animate-spin" /> : <Trash2 />}
              {uiCopy.plans043}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}
export function PlanDetail() {
  const { id } = useParams(),
    query = useApiQuery<PlanDetailType>(["plan", id], `/plans/${id}`),
    explain = useApiQuery<{ explanation: string; sources: SourceItem[] }>(
      ["plan-explain", id],
      `/plans/${id}/explain`,
      !!query.data,
    ),
    { setDraft } = useApp(),
    navigate = useNavigate();
  if (query.isLoading) return <Loading />;
  if (query.error)
    return (
      <section className="page-content">
        <ErrorBox error={query.error} />
        <Button asChild variant="outline">
          <Link to="/plans">{uiCopy.plans044}</Link>
        </Button>
      </section>
    );
  const plan = query.data;
  if (!plan) return null;
  return (
    <section className="page-content">
      <Link className="back-link" to="/plans">
        {uiCopy.plans045}
        <ChevronRight size={14} />
        {plan.name}
      </Link>
      <div className="page-heading">
        <div>
          <h2>{plan.name}</h2>
          <p>
            {uiCopy.plans034}
            {plan.term} • {plan.sections.length}
            {uiCopy.chat022}
          </p>
        </div>
        <Button
          onClick={() => {
            setDraft(plan.sections);
            navigate("/planner");
          }}
        >
          {uiCopy.plans046}
          <ArrowRight />
        </Button>
      </div>
      <Timetable sections={plan.sections} />
      <div className="explanation">
        <h3>
          <Sparkles size={20} />
          {uiCopy.plans047}
        </h3>
        <ErrorBox error={explain.error} />
        {explain.isLoading ? (
          <Loading />
        ) : (
          <>
            <p>{explain.data?.explanation}</p>
            <SourceCards sources={explain.data?.sources || []} />
          </>
        )}
        <div className="answer-actions">
          <span>{uiCopy.plans048}</span>
          <Feedback target="plan" id={String(plan.id)} />
        </div>
      </div>
    </section>
  );
}
/** GeneratedPlan.sections จาก 02 เป็น section_id string ล้วนๆ (ดู COMPAT_FIX_REPORT.md P1-J) — ต้อง
 * hydrate เป็น Section เต็มก้อนเองก่อนส่งต่อให้ <Timetable>/<SavePlan> โดยเดา course_code จาก
 * ส่วนหน้าของ section_id (เช่น "CPE301-01" -> "CPE301") แล้วค่อยดึงรายละเอียดจาก /courses/{code}/sections */
async function hydrateSections(sectionIds: string[]): Promise<Section[]> {
  const courseCodes = [
    ...new Set(sectionIds.map((id) => id.slice(0, id.lastIndexOf("-")))),
  ];
  const byId = new Map<string, Section>();
  await Promise.all(
    courseCodes.map(async (code) => {
      const page = await requestPage<Section>(
        `/courses/${encodeURIComponent(code)}/sections?term=1%2F2569`,
      );
      for (const s of page.items) byId.set(s.section_id, s);
    }),
  );
  return sectionIds
    .map((id) => byId.get(id))
    .filter((s): s is Section => !!s);
}
type HydratedPlan = GeneratedPlan & { hydratedSections: Section[] };
export function AutoPlans() {
  const [freeDays, setFreeDays] = useState<Day[]>([]),
    [max, setMax] = useState(21),
    [early, setEarly] = useState(false),
    [keep, setKeep] = useState(false),
    [pending, setPending] = useState(false),
    [results, setResults] = useState<HydratedPlan[] | null>(null),
    [error, setError] = useState<unknown>(null),
    { draft, setDraft } = useApp(),
    navigate = useNavigate();
  async function generate() {
    setPending(true);
    setResults(null);
    setError(null);
    try {
      const res = await api.post<AutoPlanResponse>("/plans/auto", {
        term: "1/2569",
        preferences: {
          free_days: freeDays,
          no_early_class: early,
          max_credits: max,
        },
        must_include: keep ? draft.map((s) => s.section_id) : [],
      });
      setResults(
        await Promise.all(
          res.plans.map(async (p) => ({
            ...p,
            hydratedSections: await hydrateSections(p.sections),
          })),
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">{uiCopy.plans049}</span>
          <h2>{uiCopy.plans050}</h2>
          <p>{uiCopy.plans051}</p>
        </div>
        <span className="large-feature-icon">
          <Sparkles size={28} />
        </span>
      </div>
      <form
        className="preferences-card"
        onSubmit={(e) => {
          e.preventDefault();
          void generate();
        }}
      >
        <div>
          <label>{uiCopy.plans052}</label>
          <div className="day-options">
            {days.map((d) => (
              <label key={d} className={freeDays.includes(d) ? "checked" : ""}>
                <input
                  type="checkbox"
                  checked={freeDays.includes(d)}
                  onChange={(e) =>
                    setFreeDays(
                      e.target.checked
                        ? [...freeDays, d]
                        : freeDays.filter((x) => x !== d),
                    )
                  }
                />
                {th.days[d]}
              </label>
            ))}
          </div>
        </div>
        <div className="preference-row">
          <label>
            {uiCopy.plans053}
            <input
              type="number"
              min={3}
              max={30}
              value={max}
              onChange={(e) => setMax(Number(e.target.value))}
              required
            />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={early}
              onChange={(e) => setEarly(e.target.checked)}
            />
            {uiCopy.plans054}
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={keep}
              onChange={(e) => setKeep(e.target.checked)}
              disabled={!draft.length}
            />
            {uiCopy.plans055}
            {draft.length})
          </label>
          <Button disabled={pending}>
            {pending ? <LoaderCircle className="animate-spin" /> : <Sparkles />}
            {pending ? uiCopy.plans056 : uiCopy.plans057}
          </Button>
        </div>
      </form>
      <ErrorBox error={error} />
      {results && (
        <>
          <div className="results-heading">
            <span>{uiCopy.plans058}</span>
            <small>
              {results.length}
              {uiCopy.plans059}
            </small>
          </div>
          {results.length ? (
            <div className="auto-results">
              {results.map((p, i) => (
                <article className="auto-card" key={i}>
                  <div className="auto-heading">
                    <span>0{i + 1}</span>
                    <div>
                      <h3>
                        {uiCopy.plans058} {i + 1}
                      </h3>
                      <p>
                        {p.total_credits}
                        {uiCopy.plans004}
                        {p.sections.length}
                        {uiCopy.chat022}
                      </p>
                    </div>
                    <CheckCircle2 size={20} />
                  </div>
                  <Timetable sections={p.hydratedSections} compact />
                  {p.explanation && <p className="auto-reason">{p.explanation}</p>}
                  {(p.relaxed_constraints ?? []).map((t) => (
                    <p key={t} className="warning-copy">
                      {t}
                    </p>
                  ))}
                  <div className="button-row">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setDraft(p.hydratedSections);
                        navigate("/planner");
                      }}
                    >
                      {uiCopy.plans060}
                      <ArrowRight />
                    </Button>
                    <SavePlan sections={p.hydratedSections} />
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <Empty icon={<CalendarDays size={36} />} title={uiCopy.plans061}>
              <p>{uiCopy.plans062}</p>
            </Empty>
          )}
        </>
      )}
    </section>
  );
}
