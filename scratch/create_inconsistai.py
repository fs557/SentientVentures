import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "companies"

sys.path.insert(0, str(Path(ROOT / "apps/api/src").resolve()))
from core.markdown import parse_evaluation_document
from core.scoring import category_scores, overall_score
from core.registry import CATEGORIES

walletprofun_dir = FIXTURES_DIR / "walletprofun"
inconsistai_dir = FIXTURES_DIR / "inconsistai"

def main():
    # 1. Recreate directory structure
    if inconsistai_dir.exists():
        shutil.rmtree(inconsistai_dir)
    inconsistai_dir.mkdir(parents=True)
    (inconsistai_dir / "evaluation").mkdir()
    (inconsistai_dir / "extracted").mkdir()

    # 2. Copy and modify evaluation files
    for path in walletprofun_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(walletprofun_dir)
            target = inconsistai_dir / rel
            
            if rel.name.endswith(".md") or rel.name.endswith(".json"):
                content = path.read_text(encoding="utf-8")
                # Replace common placeholders
                content = content.replace("walletprofun", "inconsistai")
                content = content.replace("WalletProFun", "InconsistAI")
                content = content.replace("22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333")
                content = content.replace("doc_22222222-2222-4222-8222-222222222222", "doc_33333333-3333-4333-8333-333333333333")
                
                if rel.name == "walletprofun_home.md":
                    # Replace founders assessment
                    old_founders = "The founding team is Akshat Tandon and Binhui Shao."
                    new_founders = "The founding team is Moad Larabi and Elsa Nisa."
                    content = content.replace(old_founders, new_founders)
                
                if rel.name == "walletprofun_management.md":
                    # Replace academic background section with inconsistency
                    old_academic = """## management.academic_background | How strong is the academic background?

**Score:** 98
**Confidence:** 95

### Assessment
Academic background is exceptional and verified via database integration. Akshat Tandon studied Computer Science at the Technical University of Munich (Master's), and Binhui Shao holds a PhD from Cambridge University.

### Positive Arguments
- Verified database records: Akshat Tandon studied at Technical University of Munich; Binhui Shao studied at Cambridge university.
- Founder projects in database: Akshat Tandon did 'OpportunityMap'; Binhui Shao did 'OmniSkill Pathways: From Invisible Skills to Resilient Livelihoods'.
- The academic background is verified by database integration.

### Negative Arguments and Risks
- Credentials do not by themselves prove operating execution.

### Evidence
- fact | doc_33333333-3333-4333-8333-333333333333 | p. 1 | Academic background is exceptional and verified via database integration. Akshat Tandon studied Computer Science at the Technical University of Munich (Master's), and Binhui Shao holds a PhD from Cambridge University."""

                    new_academic = """## management.academic_background | How strong is the academic background?

**Score:** 55
**Confidence:** 90

### Assessment
The academic background is inconsistent. The pitch claims Moad Larabi studied at Oxford University and Elsa Nisa studied at Stanford University, which does not match public database records.

### Positive Arguments
- Pitch highlights top-tier academic ambitions.

### Negative Arguments and Risks
- Database records indicate Moad Larabi studied at INSEAD and Elsa Nisa studied at Harvard University, contradicting the pitch.
- Credentials in the pitch deck do not match database verification.

### Evidence
- fact | doc_33333333-3333-4333-8333-333333333333 | p. 1 | The pitch claims Moad Larabi studied at Oxford University and Elsa Nisa studied at Stanford University."""

                    content = content.replace(old_academic, new_academic)
                
                target_name = rel.name.replace("walletprofun", "inconsistai")
                target = target.parent / target_name
                target.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(path, target)

    # 3. Calculate category scores and overall score
    docs = {}
    for cat in CATEGORIES:
        path = inconsistai_dir / "evaluation" / f"inconsistai_{cat}.md"
        content = path.read_text(encoding="utf-8")
        parsed = parse_evaluation_document(content, "inconsistai", cat)
        docs[cat] = parsed.document.items

    scores = category_scores(docs)
    overall = overall_score(scores)
    print("New category scores:", scores)
    print("New overall score:", overall)

    # 4. Update metadata.json
    meta_path = inconsistai_dir / "metadata.json"
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    metadata["category_scores"] = scores
    metadata["overall_score"] = overall
    metadata["submission"]["founder_name"] = "Moad Larabi"
    metadata["submission"]["founder_email"] = "moad.larabi@example.invalid"
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Created metadata.json")

    # 5. Add all files to manifest.json
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    # Calculate hashes of inconsistai directory
    for path in sorted(inconsistai_dir.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(FIXTURES_DIR).as_posix()
            hasher = hashlib.sha256()
            hasher.update(path.read_bytes())
            digest = hasher.hexdigest()
            manifest["files"][rel_path] = digest
            print(f"Added hash for {rel_path}: {digest}")

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Updated manifest.json successfully!")

if __name__ == "__main__":
    main()
