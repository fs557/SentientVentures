import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FounderPortal } from "./portal";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function addRequiredFields() {
  fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: "Aster Labs" } });
  fireEvent.change(screen.getByLabelText(/founder name/i), { target: { value: "Aster Founder" } });
  fireEvent.change(screen.getByLabelText(/founder email/i), { target: { value: "founder@example.test" } });
  fireEvent.change(screen.getByLabelText(/linkedin url/i), { target: { value: "https://linkedin.example.test/founder" } });
  fireEvent.change(screen.getByLabelText(/^pitch deck/i), { target: { files: [new File(["%PDF- test"], "deck.pdf", { type: "application/pdf" })] } });
}

describe("FounderPortal", () => {
  beforeEach(() => { fetchMock.mockReset(); });

  it("shows client validation before submission", () => {
    render(<FounderPortal />);
    fireEvent.click(screen.getByRole("button", { name: /submit for evaluation/i }));
    expect(screen.getByText(/enter a company name/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects invalid supporting files immediately", () => {
    render(<FounderPortal />);
    fireEvent.change(screen.getByLabelText(/supporting documents/i), { target: { files: [new File(["notes"], "notes.txt", { type: "text/plain" })] } });
    expect(screen.getByText("Supporting documents must be PDF files.")).toBeInTheDocument();
  });

  it("submits the accepted multipart field names with a UUID key", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ company: { id: "a", slug: "aster-labs", name: "Aster Labs" }, job: { id: "j", state: "queued", statusUrl: "/api/v1/jobs/aster-labs" }, acceptedAt: "2026-07-19T12:00:00Z" }), { status: 202 }));
    render(<FounderPortal />); addRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /submit for evaluation/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/submissions");
    expect((options.headers as Record<string, string>)["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/i);
    expect(Array.from((options.body as FormData).keys())).toEqual(expect.arrayContaining(["company_name", "founder_name", "founder_email", "linkedin_url", "pitch_deck"]));
    expect(await screen.findByRole("heading", { name: /being evaluated/i })).toBeInTheDocument();
  });

  it("does not announce completion until the job is ready", async () => {
    vi.useFakeTimers();
    let statusCallCount = 0;
    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/people/search")) {
        return Promise.resolve(new Response(JSON.stringify({ people: [] }), { status: 200 }));
      }
      if (url.includes("/submissions")) {
        return Promise.resolve(new Response(JSON.stringify({ company: { id: "a", slug: "aster-labs", name: "Aster Labs" }, job: { id: "j", state: "queued", statusUrl: "/api/v1/jobs/aster-labs" }, acceptedAt: "2026-07-19T12:00:00Z" }), { status: 202 }));
      }
      if (url.includes("/jobs/aster-labs")) {
        statusCallCount++;
        if (statusCallCount === 1) {
          return Promise.resolve(new Response(JSON.stringify({ id: "j", companySlug: "aster-labs", state: "extracting", stage: "Reading deck", progress: 20, attempt: 1, repairCount: 0, updatedAt: "2026-07-19T12:00:02Z", error: null, retryAllowed: false }), { status: 200 }));
        }
        return Promise.resolve(new Response(JSON.stringify({ id: "j", companySlug: "aster-labs", state: "ready", stage: "Ready", progress: 100, attempt: 1, repairCount: 0, updatedAt: "2026-07-19T12:00:04Z", error: null, retryAllowed: false }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    render(<FounderPortal />); addRequiredFields(); fireEvent.click(screen.getByRole("button", { name: /submit for evaluation/i }));
    await act(async () => {});
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.queryByRole("heading", { name: /evaluation ready/i })).not.toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.getByRole("heading", { name: /evaluation ready/i })).toBeInTheDocument();
    vi.useRealTimers();
  });
});
