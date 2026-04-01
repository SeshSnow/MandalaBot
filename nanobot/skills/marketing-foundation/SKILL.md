---
name: marketing-foundation
description: Generate all marketing foundation documents (market research, customer avatars, competitor analysis) in sequence. Use this skill when generating all documents at once or when starting fresh marketing strategy. This skill orchestrates the three research skills internally.
---

# Marketing Foundation Agent

## CRITICAL RULES

1. **NEVER STOP on tool errors**: If a tool returns `{"success": false, "error": "..."}`, this is INFORMATION, not a reason to stop. Continue with available data.
2. **ALWAYS SAVE**: You MUST call `save_research_document` for each document type at the end of its respective phase. An incomplete document is better than no document.
3. **NO BLOCKING**: No tool failure should prevent you from completing all phases.
4. **DEPENDENCY ORDER**: Market Research must complete before Customer Avatars and Competitor Analysis can run.

## Purpose

Generate all marketing foundation documents in a single workflow. This skill orchestrates three subordinate skills:
1. **Market Research** - Foundational strategic context (run first)
2. **Customer Avatars** - Target audience profiles with voice bank (run second)
3. **Competitor Analysis** - Competitive intelligence and ad patterns (run third)

**When to use:**
- When starting a new marketing strategy from scratch
- When regenerating all marketing documents
- As the single entry point for complete marketing foundation generation

**Key Principle:** This skill handles the workflow orchestration internally. Each subordinate skill focuses on its specific deliverable.

---

## Workflow

Execute the three phases in order. Each phase should complete and save before moving to the next.

### Phase 1: Market Research

1. Call `get_research_document(document_type="market_research")` to check if market research already exists
2. If not found:
   - Execute: "Execute the marketing-research skill. Generate comprehensive market research with all 8 sections."
   - Wait for completion
   - **CRITICAL**: Verify `save_research_document` returned `{"success": true, "document_id": "..."}`
   - If save failed, retry up to 2 times
   - If save still fails, abort the workflow and report the error
3. If found, note the `document_id` for use in subsequent phases
4. Proceed to Phase 2

### Phase 2: Customer Avatars

1. Call `get_research_document(document_type="customer_avatar")` to check if avatars already exist
2. If not found OR if you want to regenerate:
   - Execute: "Execute the customer-avatar skill. Generate customer avatars with voice bank. Market research document ID: {market_research_id}."
   - Wait for completion
   - **CRITICAL**: Verify `save_research_document` returned `{"success": true, "document_id": "..."}`
   - If save failed, retry up to 2 times
   - If save still fails, abort the workflow and report the error
3. If found, note the `document_id`
4. Proceed to Phase 3

### Phase 3: Competitor Analysis

1. Call `get_research_document(document_type="competitor_analysis")` to check if competitor analysis already exists
2. If not found OR if you want to regenerate:
   - Execute: "Execute the competitor-analysis skill. Generate competitor analysis with ad creative patterns. Market research document ID: {market_research_id}."
   - Wait for completion
   - **CRITICAL**: Verify `save_research_document` returned `{"success": true, "document_id": "..."}`
   - If save failed, retry up to 2 times
   - If save still fails, abort the workflow and report the error
3. If found, note the `document_id`

---

## Final Verification

Before completing, verify all three documents were saved:

1. Call `get_research_document(document_type="market_research")` - should return the market research
2. Call `get_research_document(document_type="customer_avatar")` - should return the avatar document
3. Call `get_research_document(document_type="competitor_analysis")` - should return the competitor analysis

If any document is missing, report which phase failed and the error encountered.

---

## Expected Output

A summary of all three documents generated:

```
# Marketing Foundation Complete

## Market Research
- Document ID: {id}
- Status: saved successfully / failed

## Customer Avatars
- Document ID: {id}
- Status: saved successfully / failed

## Competitor Analysis
- Document ID: {id}
- Status: saved successfully / failed
```

---

## Error Handling

If any phase fails to save after 2 retries:
- Report which phase failed: "Phase X (document_type) failed to save after 2 retries"
- Include the error message
- Do not continue to subsequent phases
- The workflow must have all three documents saved to be considered successful

If a subordinate skill execution returns an error or fails to complete:
- Note the error
- Attempt to continue to the next phase if possible
- Report all errors in the final summary

---

## Important Notes

- Each phase is independent in its research but dependent on market research for context
- Do not skip phases even if existing documents are found unless explicitly instructed to regenerate
- The `market_research_id` should be passed to subsequent skills so they can read the market research
- Always verify saves succeeded before moving to the next phase
