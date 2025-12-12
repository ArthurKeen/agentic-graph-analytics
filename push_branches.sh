#!/bin/bash
# Quick script to push both branches
# Run this manually: bash push_branches.sh

set -e

echo "🚀 Pushing branches to remote..."

# Push planning branch
echo ""
echo "📋 Pushing planning branch..."
git checkout feature/complete-platform-planning
git push -u origin feature/complete-platform-planning

# Push development branch
echo ""
echo "💻 Pushing development branch..."
git checkout feature/ai-foundation-phase1
git push -u origin feature/ai-foundation-phase1

echo ""
echo "✅ Both branches pushed successfully!"
echo ""
echo "Next steps:"
echo "1. Create PR for feature/complete-platform-planning (for team review)"
echo "2. Continue development on feature/ai-foundation-phase1"
echo ""
echo "GitHub PR URLs:"
echo "- Planning: https://github.com/ArthurKeen/graph-analytics-ai/compare/feature/complete-platform-planning"
echo "- Dev: https://github.com/ArthurKeen/graph-analytics-ai/compare/feature/ai-foundation-phase1"
