# Markdown Contract

This repository uses a strict evaluation Markdown format for each company/category document.

## File shape

Each document is UTF-8 text with LF line endings and a trailing newline. The serializer writes:

- YAML front matter
- a document title
- one section per evaluation criterion

The parser only accepts the repository’s canonical structure. Unknown structural sections or malformed headings are rejected.

## Front matter

The supported keys are:

- `schema_version`
- `registry_version`
- `company`
- `slug`
- `category`
- `generated_at`
- `source_documents`

All keys are required. Unknown keys are rejected.

## Document heading

The top-level heading is:

```md
# <Category> Evaluation
```

The category name comes from the registry category title used by the serializer.

## Criterion blocks

Each criterion block is serialized in this order:

1. `## <stable-id> | <title>`
2. `**Score:** ...`
3. optional `**Confidence:** ...`
4. `### Assessment`
5. `### Positive Arguments`
6. `### Negative Arguments and Risks`
7. `### Evidence`
8. `### Missing Information`
9. `### Source References`

The parser expects every criterion in registry order and rejects duplicates, missing entries, reordered entries, and title mismatches.

## Scores

Scores are integers from `1` through `100`, or `N/A` for unsupported items. Confidence, when present, uses the same numeric range. Invalid scores are rejected during parsing and validation.

## Evidence lines

Evidence is written as bullet lines in the form:

```md
- <kind> | <document id> | p. <page> | <section> | <text>
```

`kind` is either `fact` or `inference`. The parser treats evidence as structured metadata, not free-form prose.

## Validation behavior

The parser returns validation issues rather than silently dropping content. A malformed document is not considered ready for publication.

Observed failure cases include:

- missing or invalid front matter
- missing criterion blocks
- duplicate criterion IDs
- invalid score values
- unsupported category values
- slug mismatches
- raw HTML in the document body

## Normalized output

Parsed documents are converted into the API contract shape used by the dashboard:

- `EvaluationDocument`
- `EvaluationItem`
- `EvidenceReference`
- `ValidationIssue`

The dashboard consumes the normalized JSON response from the API and does not parse Markdown directly.
