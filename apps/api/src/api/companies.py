"""Read-only company APIs backed by verified deterministic fixture artifacts."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from ..core.markdown import document_to_contract_dict, parse_evaluation_document
from ..core.registry import CATEGORIES, Category
from ..core.scoring import category_scores, overall_score
from ..core.storage import CompanyRef, StorageError

router = APIRouter(prefix="/api/v1", tags=["companies"])

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CATEGORIES = frozenset(CATEGORIES)


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValidationIssueModel(_ContractModel):
    code: str
    path: str
    message: str
    severity: Literal["warning", "error"]


class EvidenceReferenceModel(_ContractModel):
    kind: Literal["fact", "inference"]
    documentId: str
    text: str
    page: int | None = None
    section: str | None = None


class EvaluationItemModel(_ContractModel):
    id: str
    category: Category
    title: str
    score: int | None
    confidence: int | None
    assessment: str
    positiveArguments: list[str]
    negativeArguments: list[str]
    evidence: list[EvidenceReferenceModel]
    missingInformation: list[str]
    sourceReferences: list[EvidenceReferenceModel]
    validationErrors: list[ValidationIssueModel]


class EvaluationDocumentModel(_ContractModel):
    schemaVersion: Literal[1]
    registryVersion: Literal[1]
    company: str
    slug: str
    category: Category
    generatedAt: str
    sourceDocuments: list[str]
    items: list[EvaluationItemModel]
    validationErrors: list[ValidationIssueModel]


class CategoryScoresModel(_ContractModel):
    home: int | None
    idea: int | None
    market: int | None
    financial: int | None
    management: int | None


class InvestmentTermsModel(_ContractModel):
    amount: float | None
    currency: str | None
    equityPercentage: float | None
    preMoneyValuation: float | None
    postMoneyValuation: float | None
    impliedValuation: float | None
    useOfFunds: list[str]


class CompanySummaryModel(_ContractModel):
    slug: str
    company: str
    stage: str | None
    submissionDate: str
    overallScore: int | None
    categoryScores: CategoryScoresModel


class CompaniesListModel(_ContractModel):
    companies: list[CompanySummaryModel]
    registryVersion: Literal[1]


class CompanyEvaluationModel(_ContractModel):
    companyId: str
    company: str
    slug: str
    stage: str | None
    submissionDate: str
    investment: InvestmentTermsModel
    categories: dict[Category, EvaluationDocumentModel]
    categoryScores: CategoryScoresModel
    overallScore: int | None
    validationErrors: list[ValidationIssueModel]


class FixtureIndexError(RuntimeError):
    """The local immutable fixture/index artifacts cannot be trusted."""


class CompanyNotFoundError(RuntimeError):
    """A validated ready company is not present in the fixture index."""


class InvalidPathParameterError(ValueError):
    """A request path parameter is syntactically invalid."""


@dataclass(frozen=True, slots=True)
class CompanyRecord:
    company_id: str
    company: str
    slug: str
    stage: str | None
    submission_date: str
    categories: dict[Category, dict[str, object]]
    category_scores: dict[Category, int | None]
    overall_score: int | None
    validation_errors: list[dict[str, str]]
    investment: dict[str, object]

    def summary(self) -> dict[str, object]:
        return {
            "slug": self.slug,
            "company": self.company,
            "stage": self.stage,
            "submissionDate": self.submission_date,
            "overallScore": self.overall_score,
            "categoryScores": self.category_scores,
        }

    def aggregate(self) -> dict[str, object]:
        return {
            "companyId": self.company_id,
            "company": self.company,
            "slug": self.slug,
            "stage": self.stage,
            "submissionDate": self.submission_date,
            "investment": self.investment,
            "categories": self.categories,
            "categoryScores": self.category_scores,
            "overallScore": self.overall_score,
            "validationErrors": self.validation_errors,
        }


class FixtureRepository:
    """Validates and reads fixture artifacts without exposing filesystem paths."""

    def __init__(self, root: Path, manifest_path: Path | None = None) -> None:
        self._root = root.resolve()
        self._manifest_path = (manifest_path or self._root / "manifest.json").resolve()

    def load_index(self) -> dict[str, CompanyRecord]:
        manifest = self._read_manifest()
        self._validate_hashes(manifest)
        records: dict[str, CompanyRecord] = {}
        company_slugs = sorted({Path(relative).parts[0] for relative in manifest})
        for slug in company_slugs:
            record = self._load_company(slug)
            if slug in records:
                raise FixtureIndexError("Fixture index contains duplicate slugs")
            records[slug] = record
        return records

    def reserved_slugs(self) -> frozenset[str]:
        """Return fixture namespace entries without trusting their contents.

        Submission storage reserves these names before creating a live record;
        full fixture integrity validation remains the read-path authority.
        """
        try:
            return frozenset(candidate.name for candidate in self._root.iterdir()
                             if candidate.is_dir() and _SLUG.fullmatch(candidate.name))
        except OSError as exc:
            raise FixtureIndexError("Fixture namespace is unavailable") from exc

    def list_companies(self, limit: int) -> list[dict[str, object]]:
        return [record.summary() for record in self.load_index().values()][:limit]

    def get_company(self, slug: str) -> CompanyRecord:
        self._validate_slug(slug)
        record = self.load_index().get(slug)
        if record is None:
            raise CompanyNotFoundError
        return record

    def _read_manifest(self) -> Mapping[str, str]:
        try:
            raw = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            files = raw["files"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise FixtureIndexError("Fixture index is unavailable") from exc
        if raw.get("generator") != "v1" or not isinstance(files, dict) or not files:
            raise FixtureIndexError("Fixture index is malformed")
        validated: dict[str, str] = {}
        for relative, digest in files.items():
            if not isinstance(relative, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise FixtureIndexError("Fixture index has an invalid entry")
            path = self._safe_fixture_path(relative)
            if path == self._manifest_path or not path.is_file():
                raise FixtureIndexError("Fixture index refers to an unavailable artifact")
            validated[relative] = digest
        return validated

    def _validate_hashes(self, manifest: Mapping[str, str]) -> None:
        for relative, expected in manifest.items():
            actual = sha256(self._safe_fixture_path(relative).read_bytes()).hexdigest()
            if actual != expected:
                raise FixtureIndexError("Fixture artifact integrity validation failed")

    def _load_company(self, slug: str) -> CompanyRecord:
        self._validate_slug(slug)
        try:
            reference = CompanyRef.from_root(self._root, slug)
            metadata = json.loads(reference.path("metadata.json").read_text(encoding="utf-8"))
        except (StorageError, OSError, ValueError) as exc:
            raise FixtureIndexError("Fixture company metadata is unavailable") from exc
        if not isinstance(metadata, dict):
            raise FixtureIndexError("Fixture company metadata is malformed")
        company_id = self._metadata_uuid(metadata, "company_id")
        company = self._metadata_text(metadata, "display_name")
        created_at = self._metadata_timestamp(metadata, "created_at")
        if metadata.get("slug") != slug or metadata.get("state") != "ready":
            raise FixtureIndexError("Fixture company is not a ready isolated record")
        if metadata.get("schema_version") != 1 or metadata.get("registry_version") != 1:
            raise FixtureIndexError("Fixture company has unsupported contract versions")
        stage = metadata.get("stage")
        if stage is not None and (not isinstance(stage, str) or len(stage) > 80):
            raise FixtureIndexError("Fixture company stage is invalid")
        raw_errors = metadata.get("validation_errors", [])
        if not isinstance(raw_errors, list) or any(not isinstance(item, dict) for item in raw_errors):
            raise FixtureIndexError("Fixture company validation errors are malformed")
        documents: dict[Category, dict[str, object]] = {}
        parsed_documents: dict[Category, Any] = {}
        for category in CATEGORIES:
            try:
                text = reference.path("evaluation", f"{slug}_{category}.md").read_text(encoding="utf-8")
            except OSError as exc:
                raise FixtureIndexError("Fixture evaluation is unavailable") from exc
            result = parse_evaluation_document(text, slug, category)
            if not result.is_valid or result.document is None:
                raise FixtureIndexError("Fixture evaluation failed contract validation")
            if result.document.company != company:
                raise FixtureIndexError("Fixture evaluation company does not match metadata")
            parsed_documents[category] = result.document
            documents[category] = document_to_contract_dict(result.document)
        computed_category_scores = category_scores(
            {category: document.items for category, document in parsed_documents.items()}
        )
        computed_overall_score = overall_score(computed_category_scores)
        self._validate_metadata_scores(metadata, computed_category_scores, computed_overall_score)
        return CompanyRecord(
            company_id=company_id,
            company=company,
            slug=slug,
            stage=stage,
            submission_date=created_at,
            categories=documents,
            category_scores=computed_category_scores,
            overall_score=computed_overall_score,
            validation_errors=[self._validation_error(item) for item in raw_errors],
            investment=self._investment_terms(metadata),
        )

    def _safe_fixture_path(self, relative: str) -> Path:
        candidate = (self._root / relative).resolve()
        if candidate == self._root or self._root not in candidate.parents:
            raise FixtureIndexError("Fixture index path escapes its root")
        return candidate

    @staticmethod
    def _validate_slug(slug: str) -> None:
        if not _SLUG.fullmatch(slug):
            raise InvalidPathParameterError("slug must use lowercase hyphenated ASCII")

    @staticmethod
    def _metadata_text(metadata: Mapping[str, object], key: str) -> str:
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise FixtureIndexError(f"Fixture metadata field {key} is invalid")
        return value

    @staticmethod
    def _metadata_uuid(metadata: Mapping[str, object], key: str) -> str:
        value = metadata.get(key)
        if not isinstance(value, str):
            raise FixtureIndexError(f"Fixture metadata field {key} is invalid")
        try:
            UUID(value)
        except ValueError as exc:
            raise FixtureIndexError(f"Fixture metadata field {key} is invalid") from exc
        return value

    @staticmethod
    def _metadata_timestamp(metadata: Mapping[str, object], key: str) -> str:
        value = metadata.get(key)
        if not isinstance(value, str):
            raise FixtureIndexError(f"Fixture metadata field {key} is invalid")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise FixtureIndexError(f"Fixture metadata field {key} is invalid") from exc
        if parsed.tzinfo is None:
            raise FixtureIndexError(f"Fixture metadata field {key} is invalid")
        return value

    @staticmethod
    def _validation_error(value: Mapping[str, object]) -> dict[str, str]:
        required = ("code", "path", "message", "severity")
        if any(not isinstance(value.get(key), str) or not value[key] for key in required) or value["severity"] not in {"warning", "error"}:
            raise FixtureIndexError("Fixture validation issue is invalid")
        return {key: value[key] for key in required}  # type: ignore[return-value]

    @staticmethod
    def _investment_terms(metadata: Mapping[str, object]) -> dict[str, object]:
        """Load public investment terms while treating absent legacy metadata as unknown.

        A present investment object is untrusted fixture/live metadata, so it must be
        complete and contract-shaped before it can reach the public response.
        """
        empty: dict[str, object] = {
            "amount": None,
            "currency": None,
            "equityPercentage": None,
            "preMoneyValuation": None,
            "postMoneyValuation": None,
            "impliedValuation": None,
            "useOfFunds": [],
        }
        if "investment" not in metadata:
            return empty
        raw = metadata["investment"]
        if not isinstance(raw, dict):
            raise FixtureIndexError("Fixture investment terms are malformed")
        expected = set(empty)
        if set(raw) != expected:
            raise FixtureIndexError("Fixture investment terms are malformed")

        def monetary(key: str) -> float | None:
            value = raw[key]
            if value is None:
                return None
            if (not isinstance(value, (int, float)) or isinstance(value, bool)
                    or not math.isfinite(value) or value < 0):
                raise FixtureIndexError("Fixture investment terms are malformed")
            return float(value)

        amount = monetary("amount")
        pre_money = monetary("preMoneyValuation")
        post_money = monetary("postMoneyValuation")
        implied = monetary("impliedValuation")
        equity = raw["equityPercentage"]
        if equity is not None and (not isinstance(equity, (int, float)) or isinstance(equity, bool)
                                   or not math.isfinite(equity) or not 0 <= equity <= 100):
            raise FixtureIndexError("Fixture investment terms are malformed")
        currency = raw["currency"]
        if currency is not None and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
            raise FixtureIndexError("Fixture investment terms are malformed")
        use_of_funds = raw["useOfFunds"]
        if (not isinstance(use_of_funds, list)
                or any(not isinstance(item, str) or not item.strip() for item in use_of_funds)):
            raise FixtureIndexError("Fixture investment terms are malformed")
        if (amount is not None and pre_money is not None and post_money is not None
                and not math.isclose(post_money, pre_money + amount, rel_tol=1e-9, abs_tol=1e-6)):
            raise FixtureIndexError("Fixture investment terms are inconsistent")
        if (implied is not None and post_money is not None
                and not math.isclose(implied, post_money, rel_tol=1e-9, abs_tol=1e-6)):
            raise FixtureIndexError("Fixture investment terms are inconsistent")
        if amount is not None and post_money is not None and equity is not None:
            if post_money <= 0 or not math.isclose(
                float(equity), amount / post_money * 100, rel_tol=1e-9, abs_tol=1e-6,
            ):
                raise FixtureIndexError("Fixture investment terms are inconsistent")
        return {
            "amount": amount,
            "currency": currency,
            "equityPercentage": None if equity is None else float(equity),
            "preMoneyValuation": pre_money,
            "postMoneyValuation": post_money,
            "impliedValuation": implied,
            "useOfFunds": use_of_funds,
        }

    @staticmethod
    def _validate_metadata_scores(
        metadata: Mapping[str, object],
        expected_category_scores: Mapping[Category, int | None],
        expected_overall_score: int | None,
    ) -> None:
        supplied = metadata.get("category_scores")
        if not isinstance(supplied, dict) or set(supplied) != set(CATEGORIES):
            raise FixtureIndexError("Fixture category scores are malformed")
        if any(supplied[category] != expected_category_scores[category] for category in CATEGORIES):
            raise FixtureIndexError("Fixture category scores do not match evaluations")
        if metadata.get("overall_score") != expected_overall_score:
            raise FixtureIndexError("Fixture overall score does not match evaluations")


class LiveCompanyRepository(FixtureRepository):
    """Read only ready, fully validated live records; source files stay private."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._manifest_path = self._root / ".not-used"

    def load_index(self) -> dict[str, CompanyRecord]:
        records: dict[str, CompanyRecord] = {}
        if not self._root.exists():
            return records
        for candidate in self._root.iterdir():
            if not candidate.is_dir() or not _SLUG.fullmatch(candidate.name):
                continue
            try:
                record = self._load_company(candidate.name)
            except FixtureIndexError:
                # Queued/failed/corrupt records are intentionally undiscoverable.
                continue
            records[record.slug] = record
        return records


class CompanyRepository:
    """Combine immutable demo fixtures and independently validated live records."""

    def __init__(self, fixtures: FixtureRepository, live: LiveCompanyRepository) -> None:
        self.fixtures, self.live = fixtures, live

    def list_companies(self, limit: int) -> list[dict[str, object]]:
        records = self._records()
        return [records[slug].summary() for slug in sorted(records)][:limit]

    def get_company(self, slug: str) -> CompanyRecord:
        FixtureRepository._validate_slug(slug)
        record = self._records().get(slug)
        if record is None:
            raise CompanyNotFoundError
        return record

    def _records(self) -> dict[str, CompanyRecord]:
        records = self.fixtures.load_index()
        live_records = self.live.load_index()
        # Fixture and live namespaces must never silently shadow each other.
        # A collision indicates compromised/corrupt local state, so fail closed.
        if records.keys() & live_records.keys():
            raise FixtureIndexError("Live and fixture company slugs collide")
        records.update(live_records)
        return records


def repository_from_request(request: Request) -> CompanyRepository:
    repository = getattr(request.app.state, "company_repository", None)
    if not isinstance(repository, CompanyRepository):
        raise FixtureIndexError("Company repository is unavailable")
    return repository


@router.get("/companies", response_model=CompaniesListModel, response_model_exclude_unset=True)
def list_companies(request: Request, limit: int = 50) -> dict[str, object]:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    try:
        companies = repository_from_request(request).list_companies(limit)
    except FixtureIndexError as exc:
        raise HTTPException(status_code=500, detail="Fixture index is invalid") from exc
    return {"companies": companies, "registryVersion": 1}


@router.get("/companies/{slug}", response_model=CompanyEvaluationModel, response_model_exclude_unset=True)
def get_company(slug: str, request: Request) -> dict[str, object]:
    try:
        return repository_from_request(request).get_company(slug).aggregate()
    except InvalidPathParameterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Company not found") from exc
    except FixtureIndexError as exc:
        raise HTTPException(status_code=500, detail="Fixture index is invalid") from exc


@router.get(
    "/companies/{slug}/categories/{category}",
    response_model=EvaluationDocumentModel,
    response_model_exclude_unset=True,
)
def get_category(slug: str, category: str, request: Request) -> dict[str, object]:
    if category not in _CATEGORIES:
        raise HTTPException(status_code=422, detail="Unsupported evaluation category")
    try:
        record = repository_from_request(request).get_company(slug)
    except InvalidPathParameterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Company not found") from exc
    except FixtureIndexError as exc:
        raise HTTPException(status_code=500, detail="Fixture index is invalid") from exc
    return record.categories[cast(Category, category)]
