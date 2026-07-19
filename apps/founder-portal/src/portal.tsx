import { type ChangeEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { JobStatus } from "@sv/contracts/generated";
import { StatusNotice } from "@sv/ui";
import logo from "../../../assets/logo/sv_logo_128.png";
import { ApiError, createSubmission, getJob, retryJob, searchPeople, type DirectoryPerson } from "./lib/api";

type FieldName = "company_name" | "founder_name" | "founder_email" | "linkedin_url" | "github_url" | "website_url" | "pitch_deck" | "cv";
type Fields = Record<Exclude<FieldName, "pitch_deck" | "cv">, string>;
type Errors = Partial<Record<FieldName | "supporting_documents", string>>;
const maxSupporting = 4;

const emptyFields: Fields = { company_name: "", founder_name: "", founder_email: "", linkedin_url: "", github_url: "", website_url: "" };
const uuid = () => typeof crypto?.randomUUID === "function" ? crypto.randomUUID() : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => { const value = Math.random() * 16 | 0; return (c === "x" ? value : value & 3 | 8).toString(16); });
const isHttpsUrl = (value: string) => { try { return new URL(value).protocol === "https:"; } catch { return false; } };
const fileError = (file: File | null) => !file ? "Choose a PDF file." : (!file.name.toLowerCase().endsWith(".pdf") || (file.type !== "application/pdf" && file.type !== "")) ? "Choose a PDF file." : undefined;

function validate(fields: Fields, pitch: File | null, cv: File | null, supporting: File[]): Errors {
  const errors: Errors = {};
  if (fields.company_name.trim().length < 2 || fields.company_name.trim().length > 120) errors.company_name = "Enter a company name between 2 and 120 characters.";
  if (fields.founder_name.trim().length < 2 || fields.founder_name.trim().length > 120) errors.founder_name = "Enter your name between 2 and 120 characters.";
  if (!/^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,63}$/.test(fields.founder_email)) errors.founder_email = "Enter a valid email address.";
  if (fields.linkedin_url && !isHttpsUrl(fields.linkedin_url)) errors.linkedin_url = "Use a valid HTTPS URL.";
  if (fields.github_url && !isHttpsUrl(fields.github_url)) errors.github_url = "Use a valid HTTPS URL.";
  if (fields.website_url && !isHttpsUrl(fields.website_url)) errors.website_url = "Use a valid HTTPS URL.";
  const pitchProblem = fileError(pitch); if (pitchProblem) errors.pitch_deck = pitchProblem;
  if (cv && fileError(cv)) errors.cv = "Choose a PDF file.";
  if (Boolean(cv) === Boolean(fields.linkedin_url.trim())) errors.cv = "Provide exactly one: a CV PDF or a LinkedIn HTTPS URL.";
  if (supporting.length > maxSupporting || supporting.some((file) => fileError(file))) errors.supporting_documents = "Add up to four PDF files.";
  return errors;
}

function FileRow({ file, onRemove, onReplace, replaceLabel = "Replace" }: { file: File; onRemove: () => void; onReplace: (event: ChangeEvent<HTMLInputElement>) => void; replaceLabel?: string }) {
  return <li className="file-row"><span><strong>{file.name}</strong><small>{Math.ceil(file.size / 1024)} KB · PDF</small></span><label className="text-button">{replaceLabel}<input type="file" accept="application/pdf,.pdf" onChange={onReplace} /></label><button type="button" className="text-button danger" onClick={onRemove}>Remove</button></li>;
}

function UploadField({ id, label, description, file, onChange, onRemove, error, required }: { id: string; label: string; description: string; file: File | null; onChange: (event: ChangeEvent<HTMLInputElement>) => void; onRemove: () => void; error?: string; required?: boolean }) {
  return <div className="field"><div className="field-label"><label htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</label><p>{description}</p></div>{file ? <ul className="file-list"><FileRow file={file} onRemove={onRemove} onReplace={onChange} /></ul> : <input id={id} type="file" accept="application/pdf,.pdf" onChange={onChange} aria-describedby={error ? `${id}-error` : undefined} />}{error && <p id={`${id}-error`} className="error-text" role="alert">{error}</p>}</div>;
}

export function FounderPortal() {
  const [fields, setFields] = useState<Fields>(emptyFields);
  const [pitch, setPitch] = useState<File | null>(null);
  const [cv, setCv] = useState<File | null>(null);
  const [supporting, setSupporting] = useState<File[]>([]);
  const [errors, setErrors] = useState<Errors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [peopleMatches, setPeopleMatches] = useState<DirectoryPerson[]>([]);
  const heldKey = useRef(uuid());
  const retryKey = useRef(uuid());
  const processing = job && job.state !== "ready" && job.state !== "failed";
  useEffect(() => { if (fields.founder_name.trim().length < 2) { setPeopleMatches([]); return; } const controller = new AbortController(); const timer = window.setTimeout(() => searchPeople(fields.founder_name.trim(), controller.signal).then(setPeopleMatches).catch((error: unknown) => { if ((error as DOMException).name !== "AbortError") setPeopleMatches([]); }), 250); return () => { window.clearTimeout(timer); controller.abort(); }; }, [fields.founder_name]);

  useEffect(() => {
    if (!job || !processing) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const latest = await getJob(job.companySlug);
        if (!stopped) { setJob(latest); setPollError(null); if (latest.state !== "ready" && latest.state !== "failed") timer = setTimeout(poll, 2000); }
      } catch (error) {
        if (!stopped) { setPollError(error instanceof Error ? error.message : "We could not refresh the job status."); timer = setTimeout(poll, 2000); }
      }
    };
    timer = setTimeout(poll, 2000);
    return () => { stopped = true; if (timer) clearTimeout(timer); };
  }, [job?.companySlug, job?.state, processing]);

  const statusTitle = useMemo(() => job?.state === "ready" ? "Evaluation ready" : job?.state === "failed" ? "Evaluation could not be completed" : "Your submission is being evaluated", [job?.state]);
  const update = (name: keyof Fields) => (event: ChangeEvent<HTMLInputElement>) => { setFields((current) => ({ ...current, [name]: event.target.value })); setErrors((current) => ({ ...current, [name]: undefined, ...(name === "linkedin_url" ? { cv: undefined } : {}) })); };
  const chooseSingle = (setter: (file: File | null) => void, name: "pitch_deck" | "cv") => (event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0] ?? null; const problem = file ? fileError(file) : name === "pitch_deck" ? "Choose a PDF file." : undefined; setter(problem ? null : file); setErrors((current) => ({ ...current, [name]: problem })); };
  const addSupporting = (event: ChangeEvent<HTMLInputElement>) => { const files = Array.from(event.target.files ?? []); const invalid = files.some((file) => fileError(file)); const tooMany = supporting.length + files.length > maxSupporting; if (!invalid && !tooMany) setSupporting((current) => [...current, ...files]); setErrors((current) => ({ ...current, supporting_documents: invalid ? "Supporting documents must be PDF files." : tooMany ? "Add up to four PDF files." : undefined })); event.target.value = ""; };
  const replaceSupporting = (index: number) => (event: ChangeEvent<HTMLInputElement>) => { const replacement = event.target.files?.[0]; if (!replacement) return; const problem = fileError(replacement); if (!problem) setSupporting((current) => current.map((file, position) => position === index ? replacement : file)); setErrors((current) => ({ ...current, supporting_documents: problem })); event.target.value = ""; };

  async function submit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validate(fields, pitch, cv, supporting);
    setErrors(nextErrors); setSubmissionError(null);
    if (Object.keys(nextErrors).length) return;
    const form = new FormData();
    Object.entries(fields).forEach(([key, value]) => { if (value.trim()) form.append(key, value.trim()); });
    form.append("pitch_deck", pitch!); if (cv) form.append("cv", cv); supporting.forEach((file) => form.append("supporting_documents", file));
    setSubmitting(true);
    try {
      const accepted = await createSubmission(form, heldKey.current);
      setJob({ id: accepted.job.id, companySlug: accepted.company.slug, state: "queued", stage: "Queued", progress: 0, attempt: 1, repairCount: 0, updatedAt: accepted.acceptedAt, error: null, retryAllowed: false });
    } catch (error) { setSubmissionError(error instanceof Error ? error.message : "Your submission could not be sent. Please try again."); }
    finally { setSubmitting(false); }
  }

  async function retry() {
    if (!job) return;
    setSubmissionError(null); setPollError(null); setSubmitting(true);
    try { const response = await retryJob(job.companySlug, retryKey.current); retryKey.current = uuid(); setJob((current) => current && { ...current, id: response.id, state: "queued", stage: "Queued for retry", attempt: response.attempt as 1 | 2, progress: 0, error: null, retryAllowed: false }); }
    catch (error) { setSubmissionError(error instanceof Error ? error.message : "The evaluation could not be retried."); }
    finally { setSubmitting(false); }
  }

  if (job) return <div className="app-shell sv-app-shell"><Nav /><main className="status-page"><section className="status-card" aria-labelledby="job-title" aria-live="polite"><p className="eyebrow">Submission received</p><h1 id="job-title">{statusTitle}</h1><p className="lede">{job.state === "ready" ? "Your evaluation has completed successfully." : job.state === "failed" ? "No completed evaluation is being shown. You can retry only if the service permits it." : "We will continue processing your materials. This page only confirms completion when the job reaches Ready."}</p><dl className="job-details"><div><dt>Company</dt><dd>{job.companySlug}</dd></div><div><dt>Current stage</dt><dd>{job.stage}</dd></div><div><dt>Progress</dt><dd>{job.progress}%</dd></div><div><dt>Attempt</dt><dd>{job.attempt} of 3</dd></div></dl>{processing && <progress value={job.progress} max="100">{job.progress}%</progress>}{pollError && <StatusNotice tone="warning" title="Status refresh delayed"><p>{pollError} We’ll keep trying.</p></StatusNotice>}{job.error && <StatusNotice tone="error" title="Job error"><p>{typeof job.error.message === "string" ? job.error.message : "The service reported an error while evaluating this submission."}</p></StatusNotice>}{submissionError && <StatusNotice tone="error" title="Request unavailable"><p>{submissionError}</p></StatusNotice>}{job.state === "failed" && job.retryAllowed && <button type="button" onClick={retry} disabled={submitting}>{submitting ? "Retrying…" : "Retry evaluation"}</button>}</section></main></div>;

  return <div className="app-shell"><Nav /><main><section className="intro" aria-labelledby="page-title"><p className="eyebrow">Founder submission</p><h1 id="page-title">Put your company in focus.</h1><p>Share the essentials and the materials behind your next venture. Required details are marked with an asterisk.</p></section><form onSubmit={submit} noValidate><div className="form-grid"><section className="form-card" aria-labelledby="company-title"><header><p className="eyebrow">01 · Company</p><h2 id="company-title">Your company</h2><p>Tell us what we should call this submission.</p></header><TextField id="company_name" label="Company name" value={fields.company_name} onChange={update("company_name")} error={errors.company_name} required /><UploadField id="pitch_deck" label="Pitch deck" description="One PDF, required." file={pitch} onChange={chooseSingle(setPitch, "pitch_deck")} onRemove={() => setPitch(null)} error={errors.pitch_deck} required /><div className="field"><div className="field-label"><label htmlFor="supporting_documents">Supporting documents</label><p>Optional · up to four PDFs.</p></div>{supporting.length > 0 && <ul className="file-list">{supporting.map((file, index) => <FileRow key={`${file.name}-${index}`} file={file} onReplace={replaceSupporting(index)} onRemove={() => setSupporting((current) => current.filter((_, position) => position !== index))} />)}</ul>}{supporting.length < maxSupporting && <input id="supporting_documents" type="file" accept="application/pdf,.pdf" multiple onChange={addSupporting} />}{errors.supporting_documents && <p className="error-text" role="alert">{errors.supporting_documents}</p>}</div></section><section className="form-card" aria-labelledby="personal-title"><header><p className="eyebrow">02 · Personal</p><h2 id="personal-title">Your details</h2><p>We use these details to associate the submission with its founder.</p></header><TextField id="founder_name" label="Founder name" value={fields.founder_name} onChange={update("founder_name")} error={errors.founder_name} required />{peopleMatches.length > 0 && <div className="directory-hint" aria-live="polite"><strong>Existing profile matches</strong>{peopleMatches.slice(0, 3).map((person) => <div key={person.id}><span>{person.name}</span><small>{person.projects.length} linked project{person.projects.length === 1 ? "" : "s"}{person.city ? ` ? ${person.city}` : ""}</small></div>)}</div>}<TextField id="founder_email" label="Founder email" type="email" value={fields.founder_email} onChange={update("founder_email")} error={errors.founder_email} required /><UploadField id="cv" label="CV" description="One PDF, or provide a LinkedIn URL below." file={cv} onChange={chooseSingle(setCv, "cv")} onRemove={() => setCv(null)} error={errors.cv} /><TextField id="linkedin_url" label="LinkedIn URL" type="url" value={fields.linkedin_url} onChange={update("linkedin_url")} error={errors.linkedin_url} description="HTTPS only. Provide this instead of a CV." /><TextField id="github_url" label="GitHub URL" type="url" value={fields.github_url} onChange={update("github_url")} error={errors.github_url} optional /><TextField id="website_url" label="Website URL" type="url" value={fields.website_url} onChange={update("website_url")} error={errors.website_url} optional /></section></div>{submissionError && <StatusNotice tone="error" title="Submission unavailable"><p>{submissionError}</p></StatusNotice>}<div className="submit-row"><p>PDF uploads only. The review starts after your submission is accepted.</p><button type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit for evaluation"}</button></div></form></main></div>;
}

function TextField({ id, label, value, onChange, error, required, optional, type = "text", description }: { id: keyof Fields; label: string; value: string; onChange: (event: ChangeEvent<HTMLInputElement>) => void; error?: string; required?: boolean; optional?: boolean; type?: string; description?: string }) { return <div className="field"><div className="field-label"><label htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}{optional && <span className="optional"> · optional</span>}</label>{description && <p>{description}</p>}</div><input id={id} type={type} value={value} onChange={onChange} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} required={required} />{error && <p id={`${id}-error`} className="error-text" role="alert">{error}</p>}</div>; }
function Nav() { return <header className="navbar sv-navbar"><a href="/" className="brand sv-brand" aria-label="Sentient Ventures submission home"><img src={logo} alt="Sentient Ventures" /><span>Sentient<br />Ventures</span></a><p>Founder submission portal</p></header>; }
