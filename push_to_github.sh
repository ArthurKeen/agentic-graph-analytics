#!/bin/bash
# Script to push graph-analytics-ai to GitHub as private repository
# 
# Usage:
#   1. Create private repo on GitHub: https://github.com/new
#   2. Replace YOUR_USERNAME below with your GitHub username
#   3. Run: bash push_to_github.sh

# SET YOUR GITHUB USERNAME HERE
GITHUB_USERNAME="YOUR_USERNAME"

# Repository name
REPO_NAME="graph-analytics-ai"

# Check if remote already exists
if git remote get-url origin >/dev/null 2>&1; then
    echo "Warning: Remote 'origin' already exists:"
    git remote -v
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote set-url origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
    else
        echo "Aborted. Update GITHUB_USERNAME in this script and try again."
        exit 1
    fi
else
    # Add remote
    echo "Adding remote repository..."
    git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
fi

# Verify remote
echo "Remote configured:"
git remote -v
echo ""

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "Successfully pushed to GitHub!"
    echo "Repository: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
    echo ""
    echo "Next steps:"
    echo "  1. Create a release tag: git tag -a v1.0.0 -m 'Initial release' && git push origin --tags"
    echo "  2. Set up branch protection in GitHub settings"
    echo "  3. Add repository description and topics"
else
    echo ""
    echo "Push failed. Common issues:"
    echo "  - Repository doesn't exist on GitHub (create it first)"
    echo "  - Authentication required (use GitHub CLI or SSH keys)"
    echo "  - Wrong username (update GITHUB_USERNAME in this script)"
fi

