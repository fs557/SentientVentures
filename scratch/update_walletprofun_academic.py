import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "companies"

mgmt_file = FIXTURES_DIR / "walletprofun" / "evaluation" / "walletprofun_management.md"
meta_file = FIXTURES_DIR / "walletprofun" / "metadata.json"
manifest_path = FIXTURES_DIR / "manifest.json"

def main():
    # 1. Update management MD file
    old_section = """## management.academic_background | How strong is the academic background?

**Score:** 87
**Confidence:** 85

### Assessment
Academic background is engineering and computer-science degrees relevant to robotics.

### Positive Arguments
- The submitted company profile supports this assessment: Academic background is engineering and computer-science degrees relevant to robotics.

### Negative Arguments and Risks
- Credentials do not by themselves prove operating execution.

### Evidence
- fact | doc_22222222-2222-4222-8222-222222222222 | p. 1 | Academic background is engineering and computer-science degrees relevant to robotics."""

    new_section = """## management.academic_background | How strong is the academic background?

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
- fact | doc_22222222-2222-4222-8222-222222222222 | p. 1 | Academic background is exceptional and verified via database integration. Akshat Tandon studied Computer Science at the Technical University of Munich (Master's), and Binhui Shao holds a PhD from Cambridge University."""

    text = mgmt_file.read_text(encoding="utf-8")
    if old_section in text:
        text = text.replace(old_section, new_section)
    else:
        # Fallback simple replacement if formatting was slightly different
        text = text.replace("**Score:** 87\n**Confidence:** 85", "**Score:** 98\n**Confidence:** 95")
    mgmt_file.write_text(text, encoding="utf-8")
    print("Updated walletprofun_management.md")

    # 2. Update metadata.json
    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    metadata["category_scores"]["management"] = 86
    metadata["overall_score"] = 83
    meta_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Updated metadata.json")

    # 3. Recalculate hashes of walletprofun directory
    walletprofun_dir = FIXTURES_DIR / "walletprofun"
    manifest_entries = {}
    for path in sorted(walletprofun_dir.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(FIXTURES_DIR).as_posix()
            hasher = hashlib.sha256()
            hasher.update(path.read_bytes())
            digest = hasher.hexdigest()
            manifest_entries[rel_path] = digest
            print(f"Calculated hash for {rel_path}: {digest}")

    # 4. Load, update, and save manifest.json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel_path, digest in manifest_entries.items():
        manifest["files"][rel_path] = digest
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Successfully updated manifest.json")

if __name__ == "__main__":
    main()
