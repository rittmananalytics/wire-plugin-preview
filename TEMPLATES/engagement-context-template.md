---
engagement_name: "{{ENGAGEMENT_NAME}}"
client_name: "{{CLIENT_NAME}}"
created_date: "{{CREATED_DATE}}"
engagement_lead: "{{ENGAGEMENT_LEAD}}"
repo_mode: "{{REPO_MODE}}"  # combined | dedicated_delivery

# If repo_mode is dedicated_delivery, provide client repo details:
client_repo:
  github_url: null
  local_path: null
  default_branch: "main"

docstore:
  provider: null  # confluence | notion | both | null
  confluence:
    space_key: null
    parent_page_url: null
  notion:
    parent_page_url: null

data_model_registry:
  vertical: null  # education | insurance | manufacturing | marketplace | retail | subscription-commerce | null
                  # May be a confident match, or the closest adjacent match when no vertical is an
                  # exact industry fit (e.g. subscription-commerce for a SaaS client's MRR/NRR model).
                  # Advisory only — see wire/schemas/data-model-registry.md. null (the default)
                  # means data_model-generate/validate behave exactly as if this didn't exist.
  cross_vertical_schemas: []  # e.g. [crm_identity_resolution, revenue_recognition] — accepted independently
                  # of any vertical match; a client can need these whether or not `vertical` above is set.
---

# Engagement Context: {{ENGAGEMENT_NAME}}

**Client**: {{CLIENT_NAME}}
**Engagement Lead**: {{ENGAGEMENT_LEAD}}
**Created**: {{CREATED_DATE}}
**Repo mode**: {{REPO_MODE}}

---

## Engagement Overview

[1–3 paragraphs describing the engagement: what the client does, why they engaged Rittman Analytics, and what the broad goal is.]

## Business Objectives

1. [Primary objective]
2. [Secondary objective]
3. [Additional objective if applicable]

## Key Stakeholders

| Name | Role | Responsibilities | Contact |
|------|------|------------------|---------|
| [name] | [role] | [what they are accountable for] | [email or Slack] |
| [name] | [role] | [what they are accountable for] | [email or Slack] |

## Current State Architecture

[Brief description of the client's current data infrastructure — what they have today. Include key systems, data volumes, and any known constraints.]

**Key systems**:
- [System 1]: [brief description]
- [System 2]: [brief description]

## Engagement Releases

| # | Release Name | Type | Status | Start | End |
|---|-------------|------|--------|-------|-----|
| 01 | Discovery | discovery | In progress | {{CREATED_DATE}} | |

## SOW Reference

Statement of Work: `engagement/sow.md` (if available)

[Note any key contract terms, budget ceiling, payment milestones, or compliance requirements.]

## Working Agreements

[Any working patterns, meeting cadence, communication preferences, or team norms agreed with the client.]

- **Meeting cadence**: [e.g. Weekly status call, Tuesday 10am]
- **Primary contact**: [who to reach for decisions]
- **Code review**: [process for reviewing and approving deliverables]
- **Access provisioning**: [how the team gets access to client systems]

## Client Repo Details

{{#if repo_mode == "dedicated_delivery"}}
This engagement uses a dedicated delivery repo. The client's code repo is separate:

- **GitHub URL**: {{client_repo.github_url}}
- **Local path**: {{client_repo.local_path}}
- **Default branch**: {{client_repo.default_branch}}

Wire commands that need to reference or modify client code should use this repo path.
{{else}}
This engagement uses the combined client + delivery repo. The `.wire/` folder lives directly in the client's code repo.
{{/if}}

## Notes

[Any other context relevant to the engagement that doesn't fit the sections above.]
