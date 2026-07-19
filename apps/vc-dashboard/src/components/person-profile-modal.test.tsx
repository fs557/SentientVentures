import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { PersonProfileModal } from "./person-profile-modal";

const mockPeopleApi = vi.hoisted(() => ({
  fetchPersonProfile: vi.fn(),
  fetchPersonScores: vi.fn(),
  fetchPersonNetwork: vi.fn()
}));

vi.mock("../lib/people", () => ({
  fetchPersonProfile: mockPeopleApi.fetchPersonProfile,
  fetchPersonScores: mockPeopleApi.fetchPersonScores,
  fetchPersonNetwork: mockPeopleApi.fetchPersonNetwork
}));

describe("PersonProfileModal", () => {
  const onCloseMock = vi.fn();
  const mockUserId = "02887d15-7eac-40f7-836d-4a7a23031b5a";

  const mockProfile = {
    id: mockUserId,
    name: "Akshat Tandon",
    firstName: "Akshat",
    lastName: "Tandon",
    avatarUrl: null,
    tagline: "Lead Engineer",
    university: "Harvard University",
    fieldOfStudy: "Computer Science",
    academicDegree: "B.Sc.",
    graduationYear: "2024",
    professionalSituation: "Active",
    country: "USA",
    city: "Boston",
    nationality: "Indian",
    githubUrl: "https://github.com/akshat",
    linkedinUrl: "https://linkedin.com/in/akshat",
    careerOpportunities: "None",
    passionHobby: "Coding",
    activeFounderScore: 75.0,
    projects: [
      { id: "proj-1", title: "OpportunityMap", relationship: "Contributor", completed: true }
    ]
  };

  const mockScores = [
    { timestamp: "2026-01-15T09:00:00Z", score: 20.0 },
    { timestamp: "2026-03-20T12:00:00Z", score: 45.0 },
    { timestamp: "2026-06-15T15:00:00Z", score: 75.0 }
  ];

  const mockNetwork = {
    nodes: [
      { id: mockUserId, label: "Akshat Tandon", type: "founder" },
      { id: "Harvard University", label: "Harvard University", type: "university" }
    ],
    links: [
      { source: mockUserId, target: "Harvard University", relationship: "studied_at" }
    ]
  };

  beforeEach(() => {
    onCloseMock.mockReset();
    mockPeopleApi.fetchPersonProfile.mockReset();
    mockPeopleApi.fetchPersonScores.mockReset();
    mockPeopleApi.fetchPersonNetwork.mockReset();
  });

  it("shows loading indicator initially and renders profile on success", async () => {
    mockPeopleApi.fetchPersonProfile.mockResolvedValueOnce(mockProfile);
    mockPeopleApi.fetchPersonScores.mockResolvedValueOnce(mockScores);
    mockPeopleApi.fetchPersonNetwork.mockResolvedValueOnce(mockNetwork);

    render(<PersonProfileModal userId={mockUserId} onClose={onCloseMock} />);

    expect(screen.getByText(/loading founder profile.../i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Akshat Tandon" })).toBeInTheDocument();
    });

    expect(screen.getByText("Lead Engineer")).toBeInTheDocument();
    expect(screen.getAllByText(/Harvard University/).length).toBeGreaterThan(0);
    expect(screen.getByText("75.0")).toBeInTheDocument();
    expect(screen.getByText("Strong")).toBeInTheDocument();
    expect(screen.getByText("OpportunityMap")).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    mockPeopleApi.fetchPersonProfile.mockResolvedValueOnce(mockProfile);
    mockPeopleApi.fetchPersonScores.mockResolvedValueOnce(mockScores);
    mockPeopleApi.fetchPersonNetwork.mockResolvedValueOnce(mockNetwork);

    render(<PersonProfileModal userId={mockUserId} onClose={onCloseMock} />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Akshat Tandon" })).toBeInTheDocument();
    });

    const closeBtn = screen.getByLabelText(/close profile/i);
    fireEvent.click(closeBtn);
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it("renders error message on fetch failure", async () => {
    mockPeopleApi.fetchPersonProfile.mockRejectedValueOnce(new Error("API Connection Error"));
    mockPeopleApi.fetchPersonScores.mockResolvedValueOnce([]);
    mockPeopleApi.fetchPersonNetwork.mockResolvedValueOnce({ nodes: [], links: [] });

    render(<PersonProfileModal userId={mockUserId} onClose={onCloseMock} />);

    await waitFor(() => {
      expect(screen.getByText("API Connection Error")).toBeInTheDocument();
    });
  });
});
