# SIGNALRanker

**Team Apex01 | India Runs Hackathon | Track 1 — Intelligent Candidate Discovery**

## What is SIGNAL?

SIGNAL is a multi-signal, intent-aware candidate ranking system that goes beyond keywords to find the truly best candidates from 100,000 profiles.

## How it works

- Skills scoring (35%) — 40+ must-have keyword taxonomy with endorsement trust filter
- Career trajectory (35%) — product vs services ratio, AI-relevant months, YOE fit
- Behavioral availability (20%) — all 23 Redrob platform signals
- Education fit (10%) — institution tier, field relevance, degree level
- Honeypot detection — 3-layer system eliminates fake profiles

## How to run

1. Clone this repo
2. Place candidates.jsonl and job_description.docx in the same folder
3. Run: python3 rank.py
4. Output: Apex01.csv — top 100 ranked candidates

## Results

- 100,000 candidates ranked in ~60 seconds on CPU
- Zero external API calls
- Official validator: PASSED
- Honeypots in top 100: 0

## Team

- Poovarasu S (Team Leader)
- Ajai Kumar R
