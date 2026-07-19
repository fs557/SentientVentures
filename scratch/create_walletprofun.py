import os
import shutil
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "companies"

src_dir = FIXTURES_DIR / "aether-robotics"
dst_dir = FIXTURES_DIR / "walletprofun"

# Replaces in file content
def replace_in_file(file_path, replacements):
    text = file_path.read_text(encoding="utf-8")
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    file_path.write_text(text, encoding="utf-8")

def main():
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    
    # Copy directory structure
    shutil.copytree(src_dir, dst_dir)
    
    # Rename evaluation files
    eval_dir = dst_dir / "evaluation"
    for item in eval_dir.glob("aether-robotics_*.md"):
        new_name = item.name.replace("aether-robotics_", "walletprofun_")
        item.rename(eval_dir / new_name)
        
    replacements = {
        "aether-robotics": "walletprofun",
        "Aether Robotics": "WalletProFun",
        "Maya Chen and Lukas Weber": "Akshat Tandon and Binhui Shao",
        "Maya Chen": "Akshat Tandon",
        "Lukas Weber": "Binhui Shao",
        "11111111-1111-4111-8111-111111111111": "22222222-2222-4222-8222-222222222222",
        "fictional@example.invalid": "akshat.tandon@example.invalid",
        "Fictional Founder": "Akshat Tandon"
    }
    
    # Apply replacements in all files of dst_dir recursively
    for path in dst_dir.rglob("*"):
        if path.is_file():
            replace_in_file(path, replacements)
            
    # Calculate sha256 of all files
    manifest_entries = {}
    for path in sorted(dst_dir.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(FIXTURES_DIR).as_posix()
            hasher = hashlib.sha256()
            hasher.update(path.read_bytes())
            digest = hasher.hexdigest()
            manifest_entries[rel_path] = digest
            print(f"Calculated hash for {rel_path}: {digest}")
            
    # Load manifest
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    # Update manifest
    for rel_path, digest in manifest_entries.items():
        manifest["files"][rel_path] = digest
        
    # Save manifest
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Successfully updated manifest.json")

if __name__ == "__main__":
    main()
