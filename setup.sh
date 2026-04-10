#!/usr/bin/env bash
# setup.sh — Bootstrap a fresh working directory for LoopEval development
#
# Usage:
#   mkdir ~/myworkdir && cd ~/myworkdir
#   curl -fsSL https://raw.githubusercontent.com/loopkitdev/LoopEval/main/setup.sh | bash
#
# Or if you already have LoopEval cloned:
#   bash ~/path/to/LoopEval/setup.sh

set -euo pipefail

echo "=== LoopEval Setup ==="
echo ""

# ── 1. Check requirements ─────────────────────────────────────────────────────

if ! command -v swift &> /dev/null; then
    echo "❌ Swift not found. Install Xcode or Swift toolchain from swift.org"
    exit 1
fi

SWIFT_VERSION=$(swift --version 2>&1 | head -1)
echo "✓ Swift: $SWIFT_VERSION"

if ! command -v git &> /dev/null; then
    echo "❌ git not found."
    exit 1
fi
echo "✓ git: $(git --version)"

# ── 2. Determine working directory ────────────────────────────────────────────

WORKDIR="${1:-$(pwd)}"
echo ""
echo "Working directory: $WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# ── 3. Clone / update LoopAlgorithm ──────────────────────────────────────────
# LoopEval's Package.swift references LoopAlgorithm as a local sibling: path: "../LoopAlgorithm"
# So LoopAlgorithm must live at <workdir>/LoopAlgorithm

echo ""
echo "── LoopAlgorithm ──────────────────────────────────────────────────────────"
if [ -d "LoopAlgorithm/.git" ]; then
    echo "→ Already cloned, pulling latest..."
    git -C LoopAlgorithm pull --ff-only || echo "  (pull failed, using existing)"
else
    echo "→ Cloning LoopAlgorithm..."
    git clone https://github.com/tidepool-org/LoopAlgorithm.git LoopAlgorithm
fi
echo "✓ LoopAlgorithm ready"

# ── 4. Clone / update LoopEval ───────────────────────────────────────────────

echo ""
echo "── LoopEval ────────────────────────────────────────────────────────────────"
if [ -d "LoopEval/.git" ]; then
    echo "→ Already cloned, pulling latest..."
    git -C LoopEval pull --ff-only || echo "  (pull failed, using existing)"
else
    echo "→ Cloning LoopEval..."
    git clone https://github.com/loopkitdev/LoopEval.git LoopEval
fi
echo "✓ LoopEval ready"

# ── 5. Build ──────────────────────────────────────────────────────────────────

echo ""
echo "── Building ────────────────────────────────────────────────────────────────"
cd LoopEval
echo "→ Running swift build (debug)..."
swift build 2>&1
echo "✓ Build complete"

BINARY="$(pwd)/.build/debug/loop-eval"
echo ""
echo "Binary: $BINARY"

# ── 6. Quick smoke test ───────────────────────────────────────────────────────

echo ""
echo "── Smoke test ──────────────────────────────────────────────────────────────"
"$BINARY" --help | head -5
echo "✓ Binary runs"

# ── 7. Run unit tests ─────────────────────────────────────────────────────────

echo ""
echo "── Unit tests ──────────────────────────────────────────────────────────────"
swift test 2>&1 | tail -10
echo "✓ Tests complete"

# ── 8. Summary ────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo " ✅  Setup complete!"
echo ""
echo " Directory layout:"
echo "   $WORKDIR/"
echo "   ├── LoopAlgorithm/   (local dependency)"
echo "   └── LoopEval/        ← work here"
echo ""
echo " Quick start:"
echo "   cd $WORKDIR/LoopEval"
echo "   .build/debug/loop-eval evaluate \\"
echo "     --nightscout-url https://<NS> \\"
echo "     --start 2026-03-01 --end 2026-03-08"
echo ""
echo " Read CLAUDE.md for full project context."
echo "════════════════════════════════════════════════════════════"
