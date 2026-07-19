# SentientVentures – Greenfield Architecture and Implementation Planning

## Role

You are the lead system architect and planner for a completely new software project called **SentientVentures**. This is a Proof-of-Concept for a Hackathon.

At the moment, there is:

* no working frontend
* no working backend
* no finished Markdown parser
* no implemented LLM Council
* no implemented scoring pipeline
* no working application on port 8080
* no working application on port 8081

Do not assume that any application, component, route, API, parser, database, or AI workflow already exists.

The repository may contain:

* requirements
* design specifications
* assets
* logo files
* agent definitions
* example prompts
* partial experiments
* generated mockups

Treat these only as source material.

Your task is to produce a precise implementation plan for the complete system.

Do not implement production code yet. This will be done by the agents.

If possible, be token-efficent and use existing tools.

This is a proof-of-concept, if you see the possibilty of skipping a step that would be necesssary in production but can be skipped in a demo. You can cheat! But please document these shortcuts.

---

# Project Name

```text
SentientVentures
```

SentientVentures is an AI-assisted venture-capital evaluation platform.

It consists of two separate desktop web applications:

```text
localhost:8080
```

Founder Submission Portal

```text
localhost:8081
```

VC Evaluation Dashboard

Both applications should share:

* one visual design language
* one logo and brand identity
* reusable UI components
* compatible data models
* a common company-evaluation pipeline

---

# Primary Product Workflow

The complete product workflow should be:

```text
Founder submits documents
        ↓
Documents are stored and indexed
        ↓
Text and structured information are extracted
        ↓
Three-model LLM Council evaluates the company
        ↓
Five normalized Markdown evaluation files are generated
        ↓
The company becomes available in the VC Dashboard
        ↓
The dashboard parses all Markdown files
        ↓
Every question, answer, argument and score is displayed
```

The planner must design this workflow end to end.

---

# Core Product Principle

The Markdown files are the central interface between:

* document extraction
* AI evaluation
* scoring
* backend
* VC dashboard

The format must therefore be:

* deterministic
* complete
* human-readable
* machine-readable
* versioned
* testable
* resilient to missing information
* consistent across all companies

Every required evaluation question must appear in the generated data.

No relevant information from the Markdown files may be silently ignored by the dashboard.

---

# Planning-Only Constraint

For this task:

* inspect all available specifications and assets
* identify missing decisions
* make reasonable architecture decisions
* create or update `PLAN.md`
* propose the complete file and directory structure
* define interfaces and contracts
* define implementation phases
* define agent responsibilities
* define acceptance criteria
* define testing requirements
* define risks and fallbacks

Do not implement the applications.

Do not create large production source files. The creation is made my the agents.

Small architecture examples, schemas, interfaces and pseudocode are allowed where they make the plan unambiguous.

---

# Application 1 – Founder Submission Portal

The Founder Submission Portal must run on:

```text
localhost:8080
```

## Purpose

The application allows a founder to submit all information required for a venture-capital evaluation.

## Target platform

Desktop only.

Target resolutions:

```text
1920 × 1080
2560 × 1440
```

Minimum supported width:

```text
approximately 1400px
```

No mobile or tablet optimization is required.

---

# Submission Portal Layout

The page should use a centered desktop layout with a maximum content width of approximately:

```text
1500px
```

Main structure:

```text
------------------------------------------------------------

Shared Navbar

------------------------------------------------------------

|                 Company     |          Personal          |
|                             |                            |
|                             |                            |
|                             |                            |

------------------------------------------------------------

                    Submit Application

------------------------------------------------------------
```

The two main cards should have equal width.

---

# Shared Navbar

Both applications use the same visual navbar.

The left side contains:

* SentientVentures logo
* SentientVentures product name

Use the existing logo asset in /assets/logo/

The logo must remain visible on every page.

---

# Company Submission Card

The left card is titled:

```text
Company
```

It contains the following upload areas.

## Pitch Deck

Required.

Requirements:

* PDF only
* drag and drop
* click to upload
* file validation
* upload progress
* visible filename
* success state
* error state
* replacement option
* removal option

## Financial and Other Documents

Optional.

Requirements:

* one or multiple PDF files
* drag and drop
* click to upload
* visible filenames
* upload progress
* success and error states
* removal option

The planner must decide whether multiple files are supported in the first version and document that decision.

---

# Personal Submission Card

The right card is titled:

```text
Personal
```

## CV

Required through exactly one of the following options:

### Option A – CV Upload

* PDF
* drag and drop
* click to upload

### Option B – LinkedIn Profile

* URL input
* validation
* clear error message

Show a clear visual separator:

```text
OR
```

The application must require at least one of the two options.

## Optional Founder Fields

* GitHub profile URL
* personal website URL

The planner should also consider whether founder name and email are required for reliable submission tracking.

If added, this must be explicitly documented in the plan.

---

# Submission Button

Primary button text:

```text
Submit Application
```

On submission, the UI must show:

* validation state
* loading state
* upload progress
* processing state
* success state
* failure state
* retry option
* generated submission or company identifier

The portal must not imply that the complete AI analysis is finished immediately if processing is asynchronous.

The planner must determine whether the initial implementation uses:

* synchronous processing
* background processing with polling
* background processing with server-sent events
* background processing with WebSockets

Prefer the simplest reliable architecture suitable for a hackathon demonstration.

---

# Document Processing Pipeline

After submission, the system must process all provided information.

The planner must define separate stages for:

1. file validation
2. safe file storage
3. PDF text extraction
4. document classification
5. structured fact extraction
6. missing-information detection
7. LLM Council preparation
8. LLM Council evaluation
9. Markdown generation
10. Markdown validation
11. score calculation
12. company indexing
13. dashboard availability

Each stage must have:

* input
* output
* validation
* error handling
* retry behavior
* logging behavior

Do not treat the complete process as one unstructured AI prompt.

---

# LLM Council

The first version should use a three-agent LLM Council.

The intended cost-efficient default model is currently described as:

```text
gpt-5.4-nano
```

The exact model identifier must be configurable.

The implementation team must verify model availability before implementation.

Do not hard-code the model identifier throughout the codebase.

Use a central configuration value.

---

# Council Roles

## Council Agent 1 – Pro Analyst

The Pro Analyst should identify:

* strengths
* opportunities
* positive evidence
* competitive advantages
* founder advantages
* market opportunities
* plausible upside scenarios

The Pro Analyst must remain evidence-based and must not invent facts.

## Council Agent 2 – Contra Analyst

The Contra Analyst should identify:

* weaknesses
* risks
* contradictions
* missing information
* competitive threats
* financial concerns
* management concerns
* execution risks
* unrealistic assumptions

The Contra Analyst must remain evidence-based and must not reject a company merely to create artificial disagreement.

## Council Agent 3 – Investment Judge

The Investment Judge receives:

* extracted document facts
* Pro analysis
* Contra analysis
* required evaluation questions
* scoring rubric

The Judge must:

* reconcile the two analyses
* answer every required question
* distinguish facts from inference
* identify missing information
* provide evidence
* provide positive arguments
* provide risks
* assign one score from `1` to `100` for every evaluative question
* generate the five final Markdown files

The Judge must not omit a question.

---

# Council Discussion Structure

The planner must propose a bounded council workflow.

Avoid unbounded discussions or repeated loops.

Recommended structure:

```text
Structured document facts
        ↓
Pro analysis
        ↓
Contra analysis
        ↓
Judge synthesis
        ↓
Validation
        ↓
Optional single repair pass
```

There should be at most one automatic repair pass when:

* a required question is missing
* a score is invalid
* a required section is empty
* the output does not match the schema

Do not allow an unlimited discussion loop. If possible consider the possiblity of a hardcoded function that checks the schema for valid input without the use of tokens/LLMs.

---

# Company Directory Structure

Use one directory per company.

Preferred structure:

```text
data/
└── companies/
    ├── company-slug-one/
    │   ├── source/
    │   │   ├── pitch-deck.pdf
    │   │   ├── financial-report.pdf
    │   │   └── cv.pdf
    │   │
    │   ├── extracted/
    │   │   ├── company-facts.json
    │   │   ├── founder-facts.json
    │   │   └── document-index.json
    │   │
    │   ├── evaluation/
    │   │   ├── company-slug-one_home.md
    │   │   ├── company-slug-one_idea.md
    │   │   ├── company-slug-one_market.md
    │   │   ├── company-slug-one_financial.md
    │   │   └── company-slug-one_management.md
    │   │
    │   └── metadata.json
    │
    └── company-slug-two/
        └── ...
```

The planner may adjust this structure when there is a strong reason.

Any change must preserve:

* clear separation between source documents and generated evaluations
* stable company identifiers
* simple company discovery
* easy testing
* human-readable output

---

# Company Slugs

Company directories and files must use URL-safe slugs.

Example:

```text
Sentient Ventures
```

becomes:

```text
sentient-ventures
```

File examples:

```text
sentient-ventures_home.md
sentient-ventures_idea.md
sentient-ventures_market.md
sentient-ventures_financial.md
sentient-ventures_management.md
```

---

# Canonical Markdown Format

The planner must define a deterministic Markdown contract.

Each Markdown file should begin with YAML front matter.

Example:

```markdown
---
company: "Aether Robotics"
slug: "aether-robotics"
category: "idea"
generated_at: "2026-07-18T18:00:00Z"
version: 1
source_documents:
  - "pitch-deck.pdf"
  - "financial-report.pdf"
---

# Idea Evaluation
```

Each evaluation item should follow one consistent structure:

```markdown
## How unique is the company idea?

**Score:** 88

**Confidence:** 82

### Assessment

The company combines autonomous inspection drones with an
industry-specific workflow.

### Positive Arguments

- Strong specialization in a regulated industrial niche.
- Clear operational benefit.
- Relevant founder experience.

### Negative Arguments and Risks

- Individual technology components are commercially available.
- Larger competitors could enter the market.

### Evidence

- Pitch deck, slides 12–18.
- Founder CV, professional experience section.
- Pilot report, page 4.

### Missing Information

- No independent customer references were provided.
```

---

# Required Markdown Fields

Each evaluative item must support:

* stable item identifier
* question title
* score
* optional confidence
* assessment
* positive arguments
* negative arguments and risks
* evidence
* missing information
* optional source references

The planner must decide whether the stable item identifier is stored:

* in front matter
* in an HTML comment
* in a dedicated Markdown field
* through a canonical question registry

Prefer a solution that remains human-readable.

---

# Score Rules

Every evaluative question receives a score from:

```text
1 to 100
```

Scores must be integers.

Valid examples:

```text
1
44
78
100
```

Invalid examples:

```text
0
101
87.5
high
unknown
```

Invalid or missing scores must not be silently replaced.

The system should:

* preserve the textual assessment
* mark the score as unavailable
* exclude the invalid score from averages
* record a validation error
* optionally trigger one repair pass
* never fabricate a neutral score such as 50

---

# Evidence Rules

The AI evaluation must distinguish between:

## Fact

Directly supported by submitted material.

## Inference

Reasonable conclusion based on supplied information.

## Missing Information

Information required for a reliable conclusion but not supplied.

The planner should define how this distinction is represented in:

* extracted facts
* council prompts
* Markdown output
* dashboard presentation

The system must not invent:

* revenue
* profit
* market size
* customer numbers
* valuations
* founder experience
* patents
* partnerships
* funding history

When data is unavailable, state:

```text
Not provided
```

or:

```text
Insufficient information
```

---

# Required Home Questions

The Home evaluation file must contain:

1. What is the company name?
2. What is the current valuation?
3. What is the company idea?
4. In which sector does the company operate?
5. What exactly does the company do?
6. What will the requested investment be used for?
7. How much equity is offered?
8. How much investment is requested?
9. What implied valuation follows from the proposed terms?
10. Who are the founders?
11. What are the most important founder facts?
12. What are the most important company facts?
13. What important information is missing?

The Home file primarily contains facts.

Where meaningful, it may also include scores for:

* company clarity
* investment clarity
* founder information completeness
* submission completeness
* overall first impression

Home should not automatically affect the overall investment score.

---

# Required Idea Questions

The Idea evaluation must include:

1. How unique is the company idea?
2. How easily can the idea be copied?
3. How defensible is the idea?
4. Is the idea patentable or otherwise protectable?
5. How complex is the technical execution?
6. How complex is the operational execution?
7. How much effort is required to achieve the stated goal?
8. How sustainable or environmentally friendly is the idea?
9. What fundamental problems exist with the idea?
10. How clearly does the idea solve a real problem?
11. How strong is the value proposition?
12. How mature is the current product or prototype?

Every question must receive its own assessment and score.

---

# Required Market Questions

The Market evaluation must include:

1. How large is the addressable market?
2. How reliable is the stated market-size estimate?
3. Is the sector trending upward or downward?
4. What market growth can reasonably be expected?
5. How strong is the timing for market entry?
6. How strong is the competition?
7. What barriers to entry exist?
8. How difficult will customer adoption be?
9. What problems exist in the target market?
10. Does the company fit the VC portfolio?
11. Are there synergies with the existing portfolio?
12. Is the target customer clearly defined?
13. Is the go-to-market strategy plausible?
14. How concentrated is the customer base likely to be?
15. Are regulatory barriers relevant?

Every question must receive its own assessment and score.

For portfolio-fit and portfolio-synergy questions, the planner must define how the VC portfolio is represented.

If no portfolio data exists, the result must explicitly state that the evaluation is unavailable or provisional.

---

# Required Financial Questions

The Financial evaluation must include:

1. What is the current revenue?
2. What is the current profit or loss?
3. What future revenue is projected?
4. What future profit is projected?
5. How plausible are the projections?
6. What is the customer acquisition cost?
7. What is the recurring customer rate?
8. What is the customer retention rate?
9. What is the revenue per employee?
10. What is the profit per employee?
11. What is the current burn rate?
12. What is the current runway?
13. How plausible is the funding requirement?
14. How will the requested capital be allocated?
15. What is the proposed exit strategy?
16. What financial inconsistencies exist?
17. What financial risks exist?
18. How complete and reliable are the submitted financial documents?
19. What assumptions have the largest influence on the forecast?

Do not invent financial values.

If the necessary data is absent, clearly state this in the assessment.

---

# Required Management Questions

The Management evaluation must include:

1. How strong is the academic background?
2. How relevant is the professional background?
3. How deep is the domain expertise?
4. How strong is the technical expertise?
5. How strong is the commercial expertise?
6. How strong is the founder-market fit?
7. How large is the founder's professional following or influence?
8. Are there relevant controversies?
9. How creative or innovative is the management team?
10. What are the management team's greatest strengths?
11. What are the management team's greatest weaknesses?
12. Are important roles missing?
13. How strong is the team's ability to execute?
14. How credible and trustworthy does the team appear?
15. Is the team sufficiently balanced?
16. Is there evidence of previous successful execution?

Use the internal category name:

```text
management
```

The visible UI label should be:

```text
MANAGEMENT
```

Do not call this category `PERSONAL` when evaluating the complete team.

---

# Application 2 – VC Evaluation Dashboard

The VC Evaluation Dashboard must run on:

```text
localhost:8081
```

## Purpose

The dashboard allows a professional investor to inspect the complete AI-generated startup evaluation.

All content must come from the selected company’s evaluation files and metadata.

Do not hard-code example answers or scores into UI components.

---

# Dashboard Design Direction

The dashboard should feel like professional software used by a high-quality venture-capital investment team.

Desired qualities:

* trustworthy
* restrained
* analytical
* premium
* information-dense
* readable
* consistent
* desktop-oriented

Avoid:

* playful visual design
* excessive gradients
* excessive glow
* decorative charts without analytical value
* excessive animation
* huge empty areas
* mobile-first layouts
* overly colorful screens

Use the generated dashboard mockups in the project conversation as visual direction only.

Do not assume that they define the final component structure.

---

# Dashboard Navbar

The shared navbar should contain:

## Left

* SentientVentures logo
* SentientVentures name

## Center or primary navigation area

* Home
* Idea
* Market
* Financials
* Management
* Overall Score

## Right

* selected company
* company stage where available
* optional notification or user controls

The actual layout should be planned based on available desktop width.

---

# Dashboard Navigation

Display:

```text
HOME

IDEA 86

MARKET 78

FINANCIALS 72

MANAGEMENT 91

SCORE 82
```

Requirements:

* Home is clickable.
* Every category is clickable.
* Score is not clickable.
* Active category is clearly highlighted.
* Category scores are derived from the loaded Markdown data.
* Overall score is derived from category scores.
* No score is hard-coded.
* Navigation should remain visible while reading long content.

---

# Company Selection

The dashboard must discover all valid companies.

Provide a company selector showing:

* company name
* overall score
* optional stage
* optional submission date

Changing the selected company must update:

* company metadata
* investment information
* Home page
* all category pages
* category scores
* overall score

Data from different companies must never be mixed.

Use the company slug as the stable identifier.

---

# Main Category Layout

The most important visual requirement is the direct relationship between:

* evaluation text
* reasoning
* evidence
* score

For each question, display one dedicated evaluation row or card.

Recommended structure:

```text
-----------------------------------------------------------------------
| Question, answer and argumentation                     | Score       |
|                                                        |             |
| Assessment                                             |    88       |
|                                                        |   / 100     |
| Positive arguments                                     |             |
| Negative arguments and risks                           | Indicator   |
| Evidence                                               |             |
| Missing information                                    | Confidence  |
-----------------------------------------------------------------------
```

The large left area contains:

* question
* assessment
* positive arguments
* negative arguments and risks
* evidence
* missing information

The smaller right area contains:

* numerical score
* `/ 100`
* qualitative label
* progress bar or circular indicator
* optional confidence

Recommended desktop width distribution:

```text
Left content area: 75–82%
Right score area: 18–25%
```

Each score must remain visually attached to its question.

Do not place all textual analysis in one large Markdown block.

Do not place all scores in an unrelated global sidebar.

---

# Evaluation Criterion Component

The planner should specify a reusable component similar to:

```tsx
<EvaluationCriterionCard
  id={item.id}
  title={item.title}
  score={item.score}
  confidence={item.confidence}
  assessment={item.assessment}
  positiveArguments={item.positiveArguments}
  negativeArguments={item.negativeArguments}
  evidence={item.evidence}
  missingInformation={item.missingInformation}
/>
```

Each criterion should remain readable without interaction.

Do not hide core arguments behind hover states.

Expandable sections may be used only for secondary detail.

---

# Score Labels

The planner may use the following initial score labels:

```typescript
function getScoreLabel(score: number): string {
  if (score >= 90) return "Exceptional";
  if (score >= 80) return "Strong";
  if (score >= 70) return "Promising";
  if (score >= 60) return "Mixed";
  if (score >= 40) return "Weak";
  return "Critical";
}
```

The planner may refine these labels but must document the final thresholds centrally.

Color must remain a secondary indicator.

The score and label must remain understandable without color.

---

# Score Calculation

Calculate a category score from all valid evaluative scores in that category.

Initial rule:

```typescript
function calculateCategoryScore(validScores: number[]): number | null {
  if (validScores.length === 0) {
    return null;
  }

  const total = validScores.reduce((sum, score) => sum + score, 0);
  return Math.round(total / validScores.length);
}
```

Calculate the initial overall score from:

* Idea
* Market
* Financials
* Management

Do not include Home by default.

Initial rule:

```typescript
function calculateOverallScore(
  categoryScores: Array<number | null>
): number | null {
  const validScores = categoryScores.filter(
    (score): score is number => score !== null
  );

  if (validScores.length === 0) {
    return null;
  }

  const total = validScores.reduce((sum, score) => sum + score, 0);
  return Math.round(total / validScores.length);
}
```

The planner must decide whether equal weighting is sufficient for the first version.

If weighted scoring is proposed, the plan must define:

* weights
* business justification
* configuration location
* UI disclosure
* test cases

Prefer equal weighting for the first version unless a strong reason exists.

---

# Home Dashboard Page

The Home page should provide a compact investment overview.

Recommended sections:

## Company Overview

* company name
* sector
* stage
* location
* founding year
* company description

## Investment Terms

* investment requested
* equity offered
* pre-money valuation
* post-money valuation
* use of funds

## Founder Overview

* founder names
* academic background
* professional background
* relevant founder facts

## Score Overview

* Idea score
* Market score
* Financial score
* Management score
* Overall score

## Top Investment Arguments

* strongest positive arguments
* most important risks
* most important missing information

All information must come from company data.

When unavailable, show:

```text
Not provided
```

Do not show placeholders such as:

```text
$100,000 for X%
```

when real data is available.

---

# Markdown Parsing

The dashboard must not treat each Markdown file as one opaque string.

The parser must extract:

* YAML front matter
* document metadata
* category
* question headings
* score
* confidence
* assessment
* positive arguments
* negative arguments
* evidence
* missing information
* source references

The plan must specify:

* parser library or custom parser strategy
* validation layer
* canonical question registry
* malformed file behavior
* duplicate question behavior
* unknown section behavior
* missing section behavior
* sanitization
* test fixtures

Rendered Markdown must be sanitized.

Arbitrary HTML and scripts must not execute.

---

# Normalized Data Model

The planner must define one normalized internal model.

A possible starting point is:

```typescript
export type EvaluationCategory =
  | "home"
  | "idea"
  | "market"
  | "financial"
  | "management";

export interface EvidenceReference {
  label: string;
  sourceDocument?: string;
  page?: number;
  section?: string;
}

export interface EvaluationItem {
  id: string;
  category: EvaluationCategory;
  title: string;

  score: number | null;
  confidence?: number | null;

  assessment: string;
  positiveArguments: string[];
  negativeArguments: string[];
  evidence: EvidenceReference[];
  missingInformation: string[];

  validationErrors: string[];
}

export interface EvaluationDocument {
  company: string;
  slug: string;
  category: EvaluationCategory;
  generatedAt?: string;
  version: number;
  sourceDocuments: string[];
  items: EvaluationItem[];
}

export interface InvestmentTerms {
  amount?: number;
  currency?: string;
  equityPercentage?: number;
  preMoneyValuation?: number;
  postMoneyValuation?: number;
  useOfFunds?: string[];
}

export interface CompanyEvaluation {
  company: string;
  slug: string;
  stage?: string;
  submissionDate?: string;

  investment: InvestmentTerms;

  categories: Partial<
    Record<EvaluationCategory, EvaluationDocument>
  >;

  categoryScores: {
    home: number | null;
    idea: number | null;
    market: number | null;
    financial: number | null;
    management: number | null;
  };

  overallScore: number | null;
  validationErrors: string[];
}
```

Adapt this model where necessary.

The final plan must include the selected model and explain major deviations.

---

# Example Companies

Create three complete fictional example companies for:

* visual demonstration
* parser tests
* scoring tests
* company-switching tests
* council-output validation

## Example Company One

A comparatively strong company with:

* convincing founder background
* attractive market trend
* defensible product
* reasonable financial plan
* realistic but manageable risks
* mostly high but not perfect scores

## Example Company Two

A mixed or weaker company with:

* an interesting concept
* weak defensibility
* uncertain market demand
* incomplete financial information
* management gaps
* several medium and low scores

Both examples must include:

* all five Markdown files
* every required question
* assessment for every question
* positive arguments where applicable
* risks where applicable
* evidence or explicit missing information
* integer score from 1 to 100 for every evaluative question

Do not duplicate the same content while only changing company names.

---

# Technical Architecture Decisions

The planner must explicitly decide and justify:

1. frontend framework
2. backend framework
3. whether both applications live in one monorepo
4. shared component strategy
5. shared type strategy
6. local development orchestration
7. port configuration
8. company storage strategy
9. file upload strategy
10. PDF extraction library
11. Markdown parsing approach
12. schema-validation library
13. background-job strategy
14. LLM provider abstraction
15. council orchestration
16. retry policy
17. logging strategy
18. error-reporting strategy
19. test framework
20. fixture strategy
21. configuration and secrets handling
22. deployment path after the hackathon

For a hackathon, prefer:

* simple architecture
* transparent data flow
* minimal infrastructure
* reproducible local setup
* easy live demonstration
* clear upgrade path

Avoid unnecessary:

* microservices
* distributed queues
* Kubernetes
* complex event systems
* multiple databases
* premature cloud dependencies

---

# Suggested Monorepo Direction

The planner should evaluate a structure similar to:

```text
sentient-ventures/
├── apps/
│   ├── founder-portal/
│   ├── vc-dashboard/
│   └── api/
│
├── packages/
│   ├── ui/
│   ├── types/
│   ├── markdown-schema/
│   ├── scoring/
│   └── config/
│
├── data/
│   └── companies/
│
├── prompts/
│   ├── pro-analyst.md
│   ├── contra-analyst.md
│   └── investment-judge.md
│
├── tests/
│   ├── fixtures/
│   ├── integration/
│   └── end-to-end/
│
├── scripts/
│   ├── validate-evaluations
│   ├── generate-example-companies
│   └── reindex-companies
│
├── .codex/
├── .agents/
├── AGENTS.md
├── PLAN.md
└── README.md
```

This is a proposal, not a mandatory structure.

The planner must select the final layout.

---

# Agent Decomposition

The final plan must divide implementation work among the custom agents.

## Explorer

Use only when repository contents, assets or experiments need to be mapped.

## Planner

Owns:

* system architecture
* interfaces
* contracts
* milestones
* acceptance criteria
* implementation order

## Backend Agent

Owns:

* upload endpoints
* file storage
* PDF extraction
* structured fact extraction
* council orchestration
* Markdown generation
* validation
* company indexing
* dashboard data endpoints

## Frontend Agent

Owns:

* shared design system
* Founder Submission Portal
* VC Dashboard
* company selector
* category navigation
* evaluation criterion cards
* score visualization

The frontend agent must use the `ui-ux-pro-max` skill.

## Tester

Owns:

* parser tests
* schema-validation tests
* scoring tests
* upload tests
* API integration tests
* company-isolation tests
* end-to-end tests
* regression checks

## Reviewer

Reviews:

* parser reliability
* data isolation
* score correctness
* security
* file upload handling
* prompt-injection exposure
* invented-data risks
* missing-information behavior
* concurrency and job-state handling

## Documentary

Documents:

* setup
* local development
* architecture
* company directory format
* Markdown contract
* adding a company
* model configuration
* running both applications
* known limitations

---

# Implementation Order

The plan should use staged implementation.

Recommended sequence:

## Phase 1 – Contracts and Fixtures

* canonical question registry
* normalized data model
* Markdown schema
* score rules
* three complete example companies
* parser fixtures

## Phase 2 – Markdown and Scoring Core

* parser
* validation
* score calculation
* company discovery
* automated tests

## Phase 3 – VC Dashboard

* shared design system
* company selector
* Home page
* category pages
* criterion cards
* score panels
* navigation
* example company rendering

## Phase 4 – Founder Submission Portal

* upload UI
* validation
* submission workflow
* processing-status UI

## Phase 5 – Backend Processing

* uploads
* storage
* PDF extraction
* structured fact extraction
* company indexing

## Phase 6 – LLM Council

* Pro prompt
* Contra prompt
* Judge prompt
* output validation
* one repair pass
* Markdown persistence

## Phase 7 – Integration and Demo Hardening

* complete end-to-end flow
* loading and error states
* demo reset
* example submissions
* logging
* documentation
* final review

The planner may adjust the order but must explain why.

---

# Security and Reliability Planning

The plan must address:

* PDF file-type validation
* file-size limits
* safe filenames
* directory traversal prevention
* malicious PDF handling
* Markdown sanitization
* prompt injection inside uploaded documents
* secret management
* LLM request logging
* personally identifiable information
* cross-company data isolation
* partial processing failures
* duplicate submissions
* retry behavior
* timeout behavior
* corrupted Markdown
* missing company files
* invalid scores
* model-output schema violations

Uploaded documents must be treated as untrusted input.

Instructions contained inside uploaded documents must not override system prompts or council roles.

---

# Required Automated Tests

The plan must include tests for:

## Markdown Parser

* valid complete file
* missing front matter
* missing question
* duplicated question
* missing score
* invalid score
* unknown section
* empty assessment
* multiple evidence entries
* malformed Markdown
* unsupported category

## Score Calculation

* normal category average
* one invalid score
* all scores invalid
* missing category
* overall average
* rounding behavior
* score boundaries 1 and 100

## Company Isolation

* selecting company A never returns company B data
* assistant context contains only selected company data
* file paths cannot escape the company directory

## Submission

* valid pitch deck
* invalid file type
* oversized file
* CV upload
* LinkedIn alternative
* missing required founder information
* duplicate submission
* processing failure

## Dashboard

* all required questions render
* correct score attached to correct question
* category navigation
* company switching
* missing score state
* missing information state
* long-text scrolling
* desktop resolutions
* both example companies

## Council

* every required question is returned
* all scores are integers from 1 to 100
* evidence is present or missing information is explicit
* no unlimited repair loop
* invalid output triggers validation
* one repair pass is enforced

---

# Definition of Done

The complete implementation will only be considered finished when:

## Founder Portal

* [ ] Port 8080 runs.
* [ ] Required uploads work.
* [ ] CV or LinkedIn validation works.
* [ ] Submission state is visible.
* [ ] Processing state is visible.
* [ ] Errors can be retried.

## Processing

* [ ] PDFs are extracted.
* [ ] Structured facts are generated.
* [ ] The three council roles run.
* [ ] Five Markdown files are generated.
* [ ] All required questions are included.
* [ ] All evaluative questions have valid scores.
* [ ] Invalid output is detected.
* [ ] Companies are indexed.

## VC Dashboard

* [ ] Port 8081 runs.
* [ ] Both example companies are selectable.
* [ ] All five files are loaded.
* [ ] All questions render.
* [ ] Text and argumentation appear on the left.
* [ ] The corresponding score appears on the right.
* [ ] Score and text remain in the same card.
* [ ] Category scores are calculated centrally.
* [ ] Overall score is calculated centrally.
* [ ] No UI score is hard-coded.
* [ ] Missing values are clearly identified.
* [ ] No company data is mixed.

## Quality

* [ ] Tests pass.
* [ ] Upload handling is secure.
* [ ] Markdown is sanitized.
* [ ] Council output is validated.
* [ ] Documentation is complete.
* [ ] The reviewer reports no unresolved high-severity issue.
* [ ] Both applications can be demonstrated locally.

---

# Required Planner Deliverable

Create or update:

```text
PLAN.md
```

The final `PLAN.md` must contain:

1. Executive summary
2. Confirmed assumptions
3. Explicit non-goals
4. Chosen technology stack
5. Complete architecture
6. End-to-end data flow
7. Complete directory structure
8. Company storage structure
9. Canonical question registry
10. Canonical Markdown contract
11. Normalized internal data model
12. API contracts
13. Job and processing-state model
14. LLM Council design
15. Prompt responsibilities
16. Validation and repair strategy
17. Scoring rules
18. Frontend component hierarchy
19. Port 8080 page structure
20. Port 8081 page structure
21. Company-selection behavior
24. Security considerations
25. Testing strategy
26. Example-company strategy
27. Implementation phases
28. Agent task decomposition
29. Acceptance criteria
30. Risks and mitigations
31. Demo strategy
32. Deployment path
33. Open questions that genuinely block implementation

For each implementation phase, include:

* objective
* owning agent
* dependencies
* affected files
* expected outputs
* acceptance criteria
* tests
* estimated complexity as small, medium or large

Do not use time estimates.

---

# Final Planner Response

After creating `PLAN.md`, return a concise summary containing:

* selected stack
* selected architecture
* most important data contracts
* final Markdown strategy
* council workflow
* implementation phases
* largest risks
* questions that still require a product decision

Do not begin implementation.

Stop after the planning deliverable is complete.
