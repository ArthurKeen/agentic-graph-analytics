# UI Mockups & Visual Guide

**Companion to:** UI_IMPLEMENTATION_PLAN.md  
**Purpose:** Visual reference for UI design  
**Date:** December 2025  

---

## Overview

This document provides ASCII-art mockups and visual descriptions of the Graph Analytics AI web interface. These mockups show the key screens and user flows.

---

## Color Scheme & Design System

### Colors
- **Primary:** Blue (#2563eb) - Actions, links
- **Success:** Green (#22c55e) - Completed states
- **Warning:** Yellow (#eab308) - In-progress, caution
- **Error:** Red (#ef4444) - Failed states, errors
- **Neutral:** Gray scale - Backgrounds, text

### Typography
- **Headings:** Inter, bold
- **Body:** Inter, regular
- **Code/Data:** Fira Mono

### Components
Based on **shadcn/ui** + **Tailwind CSS**

---

## 1. Dashboard (Home)

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔷 Graph Analytics AI                    [🔔]  [👤 John] [⚙️]       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Dashboard                                                           ║
║  ─────────────────────────────────────────────────────────────────  ║
║                                                                      ║
║  Quick Stats                                                         ║
║  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐║
║  │     23       │ │   $12.34     │ │   4.5 hrs    │ │     3      │║
║  │  Analyses    │ │  Total Cost  │ │  Total Time  │ │  Running   │║
║  │  ━━━━━━━━━  │ │  ━━━━━━━━━  │ │  ━━━━━━━━━  │ │  ━━━━━━━  │║
║  │  +5 this wk  │ │  +$2.10 wk   │ │  +2.3h week  │ │  Now       │║
║  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘║
║                                                                      ║
║  Recent Analyses                             [➕ New Analysis]       ║
║  ┌────────────────────────────────────────────────────────────────┐║
║  │ 🟢 Supply Chain Risk              ✓ Complete    $0.46   2h ago │║
║  │    4 analyses • 30K documents • 11m runtime                    │║
║  │    [View Report] [Export] [Share]                              │║
║  ├────────────────────────────────────────────────────────────────┤║
║  │ 🟡 Fraud Detection                ⟳ Running     $0.12   now    │║
║  │    Step 4/7: Generating Templates • 57% complete               │║
║  │    [View Progress] [Cancel]                                    │║
║  ├────────────────────────────────────────────────────────────────┤║
║  │ 🟢 Customer Segmentation          ✓ Complete    $0.28   1d ago │║
║  │    3 analyses • 15K documents • 8m runtime                     │║
║  │    [View Report] [Export] [Share]                              │║
║  └────────────────────────────────────────────────────────────────┘║
║                                                                      ║
║  Cost Trend (Last 30 Days)                    Usage by Algorithm    ║
║  ┌─────────────────────────┐  ┌─────────────────────────────────┐ ║
║  │  $                      │  │  ┌────┐                          │ ║
║  │ 5│     ▄▄               │  │  │ PR │ ████████████ 45%         │ ║
║  │ 4│    ██▄               │  │  └────┘                          │ ║
║  │ 3│   ███▄▄              │  │  ┌────┐                          │ ║
║  │ 2│  ████▄▄█             │  │  │WCC │ ████████ 30%             │ ║
║  │ 1│▄████████▄            │  │  └────┘                          │ ║
║  │  └─┬─┬─┬─┬─┬─           │  │  ┌────┐                          │ ║
║  │   1 5 10 15 20          │  │  │ LP │ █████ 25%                │ ║
║  └─────────────────────────┘  └─────────────────────────────────┘ ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Real-time statistics cards
- Recent analyses with status indicators
- Quick actions (New Analysis, View, Export, Share)
- Cost and usage trends
- Visual feedback with colors (green=done, yellow=running, red=error)

---

## 2. Document Management

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔷 Graph Analytics AI    Documents                [🔔] [👤] [⚙️]    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  [←] Documents                    [🔍 Search...]      [➕ Upload]    ║
║  ─────────────────────────────────────────────────────────────────  ║
║                                                                      ║
║  ┌─Folders─────────┐  ┌─ Documents ────────────────────────────────┐║
║  │                 │  │                                             │║
║  │ ▼ 📁 Requirements│ │  Name                Type      Updated      │║
║  │   • 5 files     │  │  ┌──────────────────────────────────────┐ │║
║  │                 │  │  │ ☑ fraud_requirements.md               │ │║
║  │ ▶ 📁 Context    │  │  │   Requirements • 2.3 KB • 2h ago      │ │║
║  │   • 3 files     │  │  │   [Edit] [Download] [Delete]          │ │║
║  │                 │  │  ├──────────────────────────────────────┤ │║
║  │ ▶ 📁 Business   │  │  │ ☑ supply_chain_goals.md               │ │║
║  │   • 2 files     │  │  │   Requirements • 1.8 KB • 1d ago      │ │║
║  │                 │  │  │   [Edit] [Download] [Delete]          │ │║
║  │ ▶ 📁 Technical  │  │  ├──────────────────────────────────────┤ │║
║  │   • 1 file      │  │  │ □ network_topology.md                 │ │║
║  │                 │  │  │   Requirements • 3.1 KB • 3d ago      │ │║
║  │ ─────────────── │  │  │   [Edit] [Download] [Delete]          │ │║
║  │                 │  │  └──────────────────────────────────────┘ │║
║  │ 📋 Templates    │  │                                             │║
║  │ • Fraud Det.    │  │  ┌──────────────────────────────────────┐ │║
║  │ • Supply Chain  │  │  │                                       │ │║
║  │ • Customer Seg. │  │  │  🎯 Drop files here to upload         │ │║
║  │                 │  │  │     or click to browse                │ │║
║  │                 │  │  │                                       │ │║
║  └─────────────────┘  │  │  Supports: .md .txt .pdf              │ │║
║                       │  └──────────────────────────────────────┘ │║
║                       └─────────────────────────────────────────────┘║
║                                                                      ║
║  Selected: fraud_requirements.md (2 items)      [Bulk Actions ▼]    ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ Preview                                      [Edit] [Fullscreen] │ ║
║  │ ──────────────────────────────────────────────────────────────  │ ║
║  │                                                                  │ ║
║  │ # Fraud Detection Requirements                                  │ ║
║  │                                                                  │ ║
║  │ ## Objective                                                    │ ║
║  │ Identify fraudulent transaction patterns in our payment         │ ║
║  │ network to reduce financial losses and improve security.        │ ║
║  │                                                                  │ ║
║  │ ## Success Criteria                                             │ ║
║  │ - Detect suspicious transaction clusters                        │ ║
║  │ - Identify high-risk accounts (risk score >0.9)                 │ ║
║  │ - Generate actionable alerts for investigation                  │ ║
║  │ ...                                                              │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Folder organization by document type
- Drag & drop upload area
- Inline document preview
- Quick actions (Edit, Download, Delete)
- Bulk operations
- Search functionality
- Template library

---

## 3. New Analysis Wizard (Step 1: Select Documents)

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔷 Graph Analytics AI    New Analysis              [🔔] [👤] [⚙️]   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  New Analysis: Fraud Detection                         [× Cancel]    ║
║  ─────────────────────────────────────────────────────────────────  ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  ① Select Documents  →  ② Database  →  ③ LLM  →  ④ Review   │   ║
║  │  ═══════════════════     ──────────     ────     ────────     │   ║
║  └──────────────────────────────────────────────────────────────┘   ║
║                                                                      ║
║  Select Input Documents                                              ║
║  Choose documents that describe your business requirements,          ║
║  domain knowledge, and analysis objectives.                          ║
║                                                                      ║
║  Requirements Documents                              [+ Add]         ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ✓ fraud_requirements.md                               [Remove] │ ║
║  │   2.3 KB • Updated 2h ago                                      │ ║
║  │   "Identify fraudulent transaction patterns..."                │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  Context Documents                                   [+ Add]         ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ✓ fraud_domain_knowledge.md                           [Remove] │ ║
║  │   1.8 KB • Updated 1d ago                                      │ ║
║  │   "Known fraud patterns include..."                            │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  Business Context (Optional)                         [+ Add]         ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ No documents selected                                           │ ║
║  │ [Browse Documents] or [Upload New]                              │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ℹ️ Tip: More context helps AI generate better recommendations      ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │  Selected: 2 documents (4.1 KB total)                          │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║                                         [Cancel]      [Next Step →] ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Step indicator (progress through wizard)
- Document selection by category
- Document preview snippets
- Add/remove documents
- Helpful tips
- Clear navigation

---

## 4. Workflow Execution Monitor

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔷 Graph Analytics AI    Fraud Detection          [🔔] [👤] [⚙️]    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  [←] Fraud Detection Analysis                [⏸ Pause] [× Cancel]   ║
║  ─────────────────────────────────────────────────────────────────  ║
║                                                                      ║
║  Overall Progress: 57%                                               ║
║  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ║
║                                                                      ║
║  Status: Generating Use Cases (4/7)                                  ║
║  ⏱ Elapsed: 3m 42s  |  ⏳ Remaining: ~4m 30s  |  💰 Cost: $0.008   ║
║                                                                      ║
║  Workflow Steps                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ✅ 1. Schema Analysis              ⏱ 12.3s    💰 $0.001       │ ║
║  │    Analyzed 5K vertices, 80K edges                             │ ║
║  │    Identified 4 vertex collections, 4 edge types               │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ ✅ 2. Process Requirements         ⏱ 8.7s     💰 $0.002       │ ║
║  │    Extracted 5 objectives, 4 constraints                       │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ ✅ 3. Generate PRD                 ⏱ 15.2s    💰 $0.003       │ ║
║  │    Created comprehensive PRD with feasibility validation       │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ 🟡 4. Generate Use Cases           ⏱ 8.5s...  💰 $0.002       │ ║
║  │    Generated 3 use cases so far (PageRank, WCC, Label Prop)   │ ║
║  │    ████████████████████████████████░░░░░░░░░ 80%              │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ ⏸ 5. Generate Templates            ⏱ —        💰 —            │ ║
║  │    Waiting...                                                  │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ ⏸ 6. Execute Analyses              ⏱ —        💰 —            │ ║
║  │    Waiting...                                                  │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ ⏸ 7. Generate Report               ⏱ —        💰 —            │ ║
║  │    Waiting...                                                  │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  Live Log                                       [📥 Download] [🔍]   ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ [14:32:28] Generated use case 2: WCC for fraud ring detection │ ║
║  │ [14:32:30] Analyzing graph patterns for community detection   │ ║
║  │ [14:32:33] Mapping algorithms to business requirements...     │ ║
║  │ [14:32:35] Generated use case 3: Label Propagation            │ ║
║  │ [14:32:38] Validating use case feasibility...                 │ ║
║  │ [14:32:40] ✓ All use cases validated                          │ ║
║  │ [14:32:42] Starting template generation...                    │ ║
║  │ █                                                              │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Overall progress bar
- Real-time status updates
- Step-by-step breakdown with individual progress
- Time and cost tracking
- Live log stream with auto-scroll
- Pause/Cancel controls
- Visual indicators (✅ done, 🟡 running, ⏸ waiting)

---

## 5. Results View - Summary Tab

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔷 Graph Analytics AI    Fraud Detection          [🔔] [👤] [⚙️]    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  [←] Fraud Detection Analysis              [📤 Export ▼] [🔗 Share] ║
║  ─────────────────────────────────────────────────────────────────  ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  Summary | PRD | Use Cases | Results | Recommendations       │   ║
║  │  ════════   ───   ─────────   ───────   ───────────────      │   ║
║  └──────────────────────────────────────────────────────────────┘   ║
║                                                                      ║
║  Executive Summary                                                   ║
║                                                                      ║
║  🎯 Key Findings                                                     ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ • 23 high-risk accounts identified (risk score >0.95)          │ ║
║  │ • 5 potential fraud rings detected (127 participants total)    │ ║
║  │ • Estimated fraud exposure: $1,237,450                         │ ║
║  │ • 3 critical fraud patterns requiring immediate action         │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  📊 Risk Analysis                                                    ║
║  ┌──────────────────────────┐  ┌───────────────────────────────┐   ║
║  │  High Risk:  23 accounts │  │  Fraud Rings by Size          │   ║
║  │  Medium:     156 accounts│  │  ┌─┐                          │   ║
║  │  Low:        4,821 accts │  │50│█│                          │   ║
║  │                          │  │40│█│  ▄                        │   ║
║  │  Total: 5,000 analyzed   │  │30│█│  █  ▄                    │   ║
║  │                          │  │20│█│  █  █  ▄  ▄              │   ║
║  │  [View Distribution]     │  │10│█│  █  █  █  █              │   ║
║  └──────────────────────────┘  │  └┴───┴───┴───┴──            │   ║
║                                │    1  2  3  4  5              │   ║
║                                └───────────────────────────────┘   ║
║                                                                      ║
║  💡 Top 5 Recommendations                            [View All (12)] ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ 1. ⚠️ CRITICAL: Freeze accounts #4521, #8834, #2341          │ ║
║  │    Impact: $680K exposure | Effort: Low | Priority: 10/10     │ ║
║  │    [View Details] [Take Action]                                │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ 2. ⚠️ HIGH: Investigate fraud ring #1 (47 accounts)           │ ║
║  │    Impact: $450K exposure | Effort: High | Priority: 9/10     │ ║
║  │    [View Details] [Assign Team]                                │ ║
║  ├────────────────────────────────────────────────────────────────┤ ║
║  │ 3. ⚡ MEDIUM: Enhance monitoring for 156 medium-risk accounts  │ ║
║  │    Impact: $107K exposure | Effort: Medium | Priority: 7/10   │ ║
║  │    [View Details] [Schedule]                                   │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  📈 Analysis Metadata                                                ║
║  Runtime: 11m 23s  |  Total Cost: $0.46  |  Completed: 2 hours ago  ║
║  LLM: $0.01 (34 calls) | GAE: $0.45 (4 analyses)                    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Tab navigation
- Executive summary with key findings
- Visual charts and statistics
- Priority-ranked recommendations
- Action buttons for immediate response
- Metadata and cost breakdown

---

## 6. Results View - Results Tab (Analysis Details)

```
╔══════════════════════════════════════════════════════════════════════╗
║  Results Tab                                                         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  Summary | PRD | Use Cases | Results | Recommendations       │   ║
║  │  ───────   ───   ─────────   ════════   ───────────────      │   ║
║  └──────────────────────────────────────────────────────────────┘   ║
║                                                                      ║
║  Analysis Results (4 analyses)                      [⬇️ Export All]  ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ▼ high_risk_accounts (PageRank)              ✅ Success         │ ║
║  │   Runtime: 2m 15s | Cost: $0.12 | Documents: 5,000 updated     │ ║
║  │   ──────────────────────────────────────────────────────────   │ ║
║  │                                                                 │ ║
║  │   Top 10 High-Risk Accounts        [View All] [Export CSV]     │ ║
║  │   ┌──────┬────────────┬──────────┬─────────┬────────────────┐ │ ║
║  │   │ Rank │ Account ID │   Score  │  Txns   │  Action        │ │ ║
║  │   ├──────┼────────────┼──────────┼─────────┼────────────────┤ │ ║
║  │   │  1   │  ACC-4521  │  0.9847  │   847   │ [🚨 Freeze]    │ │ ║
║  │   │  2   │  ACC-8834  │  0.9823  │   1,203 │ [🚨 Freeze]    │ │ ║
║  │   │  3   │  ACC-2341  │  0.9801  │   672   │ [🚨 Freeze]    │ │ ║
║  │   │  4   │  ACC-9123  │  0.9756  │   423   │ [⚠️ Review]    │ │ ║
║  │   │  5   │  ACC-7832  │  0.9723  │   891   │ [⚠️ Review]    │ │ ║
║  │   │  6   │  ACC-1234  │  0.9698  │   234   │ [⚠️ Review]    │ │ ║
║  │   │  7   │  ACC-5567  │  0.9645  │   567   │ [⚠️ Review]    │ │ ║
║  │   │  8   │  ACC-4490  │  0.9621  │   345   │ [⚠️ Review]    │ │ ║
║  │   │  9   │  ACC-3389  │  0.9598  │   678   │ [⚠️ Review]    │ │ ║
║  │   │ 10   │  ACC-8871  │  0.9567  │   912   │ [⚠️ Review]    │ │ ║
║  │   └──────┴────────────┴──────────┴─────────┴────────────────┘ │ ║
║  │                                                                 │ ║
║  │   Score Distribution               [Switch to Chart View]      │ ║
║  │   ████████████████████████████░░░░  High (>0.9): 23            │ ║
║  │   ██████████████░░░░░░░░░░░░░░░░░  Medium: 156                 │ ║
║  │   ████████████████████████████████  Low (<0.5): 4,821          │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ▶ fraud_rings (WCC)                       ✅ Success           │ ║
║  │   Runtime: 1m 52s | Cost: $0.07 | Documents: 10,000 created   │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ▶ transaction_patterns (Label Propagation) ✅ Success          │ ║
║  │   Runtime: 2m 28s | Cost: $0.11 | Documents: 5,000 updated    │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ ▶ merchant_risk (PageRank)                ✅ Success           │ ║
║  │   Runtime: 3m 42s | Cost: $0.15 | Documents: 10,000 updated   │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Expandable/collapsible analysis sections
- Detailed results tables with sorting
- Action buttons for immediate response
- Visual distributions
- Export options (CSV, JSON, Excel)
- Switch between table/chart views

---

## 7. Settings Page

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔷 Graph Analytics AI    Settings                 [🔔] [👤] [⚙️]   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Settings                                                            ║
║  ─────────────────────────────────────────────────────────────────  ║
║                                                                      ║
║  ┌─Navigation──┐  ┌─ Content ────────────────────────────────────┐ ║
║  │             │  │                                               │ ║
║  │ General     │  │ LLM Provider Configuration                    │ ║
║  │ Database    │  │                                               │ ║
║  │ ▶ LLM       │  │ Provider                                      │ ║
║  │ Workflow    │  │ ┌───────────────────────────────────────────┐│ ║
║  │ Security    │  │ │ OpenRouter              ▼                 ││ ║
║  │ Costs       │  │ └───────────────────────────────────────────┘│ ║
║  │ Users       │  │                                               │ ║
║  │             │  │ API Key                      [🔍 Test]        │ ║
║  │             │  │ ┌───────────────────────────────────────────┐│ ║
║  │             │  │ │ sk-or-v1-0d28c4861f61eaa... [Show]        ││ ║
║  │             │  │ └───────────────────────────────────────────┘│ ║
║  │             │  │ ✅ Connection successful (tested 5 min ago)   │ ║
║  │             │  │                                               │ ║
║  │             │  │ Default Model                                 │ ║
║  │             │  │ ┌───────────────────────────────────────────┐│ ║
║  │             │  │ │ google/gemini-2.5-flash   ▼               ││ ║
║  │             │  │ └───────────────────────────────────────────┘│ ║
║  │             │  │ Speed: Fast (11s avg) | Cost: $0.0001/1K     │ ║
║  │             │  │                                               │ ║
║  │             │  │ Parameters                                    │ ║
║  │             │  │ Max Tokens     [4000        ]                 │ ║
║  │             │  │ Temperature    [0.7         ] (0.0 - 1.0)     │ ║
║  │             │  │                                               │ ║
║  │             │  │ Cost Limits                                   │ ║
║  │             │  │ ☑ Enable budget limits                        │ ║
║  │             │  │ Max per workflow:  [$ 5.00   ]                │ ║
║  │             │  │ Monthly budget:    [$ 100.00 ]                │ ║
║  │             │  │                                               │ ║
║  │             │  │ Current month: $12.34 / $100.00 (12%)         │ ║
║  │             │  │ ████░░░░░░░░░░░░░░░░░░░░░░░░░░░                │ ║
║  │             │  │                                               │ ║
║  │             │  │ Notifications                                 │ ║
║  │             │  │ ☑ Warn when approaching budget limit (80%)    │ ║
║  │             │  │ ☑ Stop workflows if budget exceeded           │ ║
║  │             │  │                                               │ ║
║  │             │  │                        [Save Changes]         │ ║
║  └─────────────┘  └───────────────────────────────────────────────┘ ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Features:**
- Sidebar navigation
- Provider selection dropdown
- Secure API key input (masked)
- Model selection with cost/speed info
- Parameter configuration
- Cost limits and budget tracking
- Test connection button
- Real-time validation
- Save confirmation

---

## Mobile Responsive Views

### Dashboard (Mobile)
```
┌──────────────────────┐
│ 🔷 Graph Analytics   │
│                   ☰  │
├──────────────────────┤
│ Quick Stats          │
│ ┌────────┐ ┌───────┐│
│ │   23   │ │ $12.34││
│ │ Analyses│ │  Cost ││
│ └────────┘ └───────┘│
│ ┌────────┐ ┌───────┐│
│ │ 4.5hrs │ │   3   ││
│ │  Time  │ │Running││
│ └────────┘ └───────┘│
│                      │
│ Recent   [+ New]     │
│ ┌──────────────────┐│
│ │ 🟢 Supply Chain  ││
│ │    ✓ Complete    ││
│ │    $0.46  2h ago ││
│ │ [View] [Export]  ││
│ ├──────────────────┤│
│ │ 🟡 Fraud         ││
│ │    ⟳ Running     ││
│ │    $0.12  now    ││
│ │ [Progress]       ││
│ └──────────────────┘│
└──────────────────────┘
```

---

## Color & Icon Legend

### Status Colors
- 🟢 Green: Complete, Success, Active
- 🟡 Yellow: In Progress, Warning, Pending
- 🔴 Red: Error, Failed, Critical
- ⚪ Gray: Inactive, Disabled, Future

### Icons
- ✅ Success / Complete
- ⟳ Running / In Progress
- ⏸ Paused / Waiting
- ❌ Error / Failed
- ⚠️ Warning / Attention
- ℹ️ Information
- 🔍 Search
- 📤 Export
- 📥 Download
- 🔗 Share
- ⚙️ Settings
- 👤 User
- 🔔 Notifications
- ➕ Add / Create
- 📊 Chart / Stats
- 💰 Cost
- ⏱ Time
- 🎯 Target / Goal
- 📁 Folder
- 📄 Document

---

## Interaction Patterns

### Hover States
- **Cards:** Subtle elevation/shadow
- **Buttons:** Darken/lighten by 10%
- **Links:** Underline appears
- **Tables:** Row highlight (light background)

### Loading States
- **Buttons:** Spinner icon + "Loading..."
- **Cards:** Skeleton loading animation
- **Tables:** Shimmer effect on rows
- **Progress:** Animated bar with pulse

### Empty States
```
┌────────────────────────────────┐
│                                │
│         📭                     │
│                                │
│    No analyses yet             │
│    Create your first analysis  │
│    to get started              │
│                                │
│    [➕ New Analysis]            │
│                                │
└────────────────────────────────┘
```

### Error States
```
┌────────────────────────────────┐
│                                │
│         ⚠️                     │
│                                │
│    Failed to load results      │
│    The server returned an error│
│                                │
│    [🔄 Retry]  [📧 Report]     │
│                                │
└────────────────────────────────┘
```

---

## Accessibility Features

- **Keyboard Navigation:** Full keyboard support (Tab, Enter, Esc)
- **Screen Readers:** ARIA labels on all interactive elements
- **Focus Indicators:** Clear focus rings on all focusable elements
- **Color Contrast:** WCAG AA compliant (4.5:1 minimum)
- **Text Scaling:** Responsive to browser text size settings
- **Alt Text:** Descriptive alt text for all icons and images

---

## Summary

This UI design provides:
- ✅ **Intuitive Navigation** - Clear hierarchy and flow
- ✅ **Visual Feedback** - Real-time updates and status
- ✅ **Responsive Design** - Works on desktop, tablet, mobile
- ✅ **Professional Look** - Modern, clean interface
- ✅ **Accessibility** - WCAG compliant
- ✅ **User-Friendly** - Minimal learning curve

**Ready for implementation after core AI features complete.**
