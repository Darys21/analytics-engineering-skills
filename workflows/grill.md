# Workflow: GRILL — Goal-Revealing Iterative Limning Listener

## Purpose

Resolve stakeholder ambiguity before producing any deliverable. Extract the actual decision problem, success metrics, grain, constraints, and boundary conditions so downstream work targets the correct problem instead of a proxy. This workflow is the mandatory entry point for any analytical engagement, dashboard request, or data initiative. Skipping it guarantees rework.

## When to use

- A stakeholder requests a dashboard, report, analysis, or data model
- The request contains phrases like "we need visibility" or "can you build something that shows..."
- Multiple interpretations of the requirement are plausible
- Stakeholder language describes outputs (charts, lists) rather than decisions or outcomes
- A previous attempt at the request failed to produce action
- The requestor is not the end decision-maker

## Inputs

- Raw stakeholder request (email, ticket, meeting notes, verbal brief)
- Any attached mockups, screenshots, Excel files, or existing reports
- Access to the requestor and (ideally) the end decision-maker for a synchronous session
- Historical context: prior analyses, existing dashboards, or failed attempts in this problem space

## Preconditions

- At least 30 minutes of synchronous time with the requestor is scheduled (or a written Q&A thread is agreed)
- The facilitator has authority to pause downstream work until ambiguity is resolved
- No solutioning has begun; no SQL, no models, no charts have been drafted

## Procedure

1. **Capture the raw request verbatim.** Write down the exact wording used. Do not paraphrase. Label it `Raw Request` in the working document.
2. **Ask the Objective question.** "What are we trying to accomplish? Finish this sentence: 'At the end of this work, the stakeholder will be able to ___.'" Record the answer. If the answer describes a chart or a file, re-ask: "What will the person do with that chart?" Repeat until the answer describes an action, decision, or behaviour change.
3. **Ask the Why question.** "Why does this matter? What happens if we do not do this work? What is the cost of delay or the cost of being wrong?" Record the answer. If the answer is "we should just know" or "management wants it," escalate: ask who the ultimate decision-maker is and whether they can join the session.
4. **Identify the Who.** "Who is the primary decision-maker? Who else will consume this output? What roles do they hold?" Record each persona separately. For each, ask: "What decision does this persona make on the basis of this output?" If a persona has no decision attached, they are optional and should be deprioritized.
5. **Define the Decision.** "Specifically, what decision is this output informing? What are the options? When does the decision get made? How often is it revisited?" Record the decision name, its options, its frequency, and its deadline. If no deadline exists, agree to one or mark the work as non-urgent.
6. **Define Success.** "What would make this work successful? If this is a dashboard, what action will a user take after seeing it, and how will we know they took it?" Write measurable success criteria. Prefer behavioural metrics ("user opens dashboard and changes a parameter in the ERP within 1 hour") over vanity metrics ("dashboard is accessed 100 times").
7. **Pin down the Grain.** "What is the smallest unit of observation we need to support the decision? A row in our output should represent one ___." Write the grain explicitly (e.g., "one invoice-line per day", "one truck-trip per route", "one employee per month"). Confirm it with the decision: "If grain is X, can the decision maker still choose between options?" If not, refine.
8. **Inventory the Data.** "What systems hold the raw facts? What systems hold the reference dimensions? Who owns each source? What is the freshness SLA for each?" List every source by system name and owner. Mark any sources that the team does not currently have access to as blockers.
9. **Enumerate Constraints.** "What is in scope? What is explicitly out of scope? What technical, regulatory, or budget constraints apply? When is the hard deadline versus the soft deadline?" Record each constraint. For anything marked out of scope, confirm the consequence: "If we exclude X, the decision can still be made? Yes / No."
10. **Catalog Existing Work.** "What dashboards, reports, spreadsheets, or queries already attempt to solve this? What do they get right? What do they get wrong? Who maintains them?" Inspect each existing artifact. Record what is reusable versus what must be replaced.
11. **State the Unchanged.** "What part of the business process, org structure, or data landscape will NOT change during this engagement, upon which we can rely?" Record stable assumptions (e.g., "the GL chart of accounts is not changing this quarter").
12. **Surface Assumptions.** "What assumptions are we making about the data, the business, the users, or the timeline that, if wrong, would invalidate the work?" Write every assumption explicitly. For each, attach a risk level (low / medium / high) and a verification step.
13. **Synthesize and feed back.** Read aloud the synthesized answers to Objective, Why, Who, Decision, Success, Grain, Data, Constraints, Existing, Unchanged, and Assumptions. Ask the stakeholder: "Have I got this right? Is anything missing? Is anything wrong?" Iterate until the stakeholder confirms with an unqualified "yes."
14. **Sign off.** Record the confirmation (written, meeting-minuted, or email) and attach it to the work item. Proceed to `business-analysis.md` only after sign-off.

## Decision points

- **Step 2 (Objective).** If after three passes the answer still describes an output rather than an outcome, stop the workflow, escalate to the requestor's manager, and schedule a second session with a decision-maker present. Do not proceed.
- **Step 5 (Decision).** If no concrete decision with options and a deadline can be articulated, classify the work as exploratory, cap scope to a single one-page diagnostic, and state explicitly that no dashboard or recurring deliverable will be built.
- **Step 7 (Grain).** If the grain is ambiguous (e.g., "it's by order but sometimes by line"), require a concrete example from the stakeholder using real identifiers ("show me one row from the ideal output using actual order numbers and line numbers").
- **Step 8 (Data).** If a required source is inaccessible or its owner cannot confirm freshness, log a risk and present the stakeholder with two options: (a) proceed without the source and accept a reduced decision quality, or (b) delay the engagement until access is granted. Do not silently omit the source.
- **Step 13 (Feedback).** If the stakeholder says "mostly" or "sort of" instead of "yes," treat every missing or incorrect item as a gap and re-run the relevant steps. Do not accept partial agreement.

## Validation

- The 11-element synthesis (Objective, Why, Who, Decision, Success, Grain, Data, Constraints, Existing, Unchanged, Assumptions) is written down, each element in a single sentence or bullet, with no ambiguous pronouns.
- For every stakeholder persona listed, a concrete decision is attached. No persona is listed without a decision.
- Grain is expressed as "one [entity] per [unit of time / unit of context]" using nouns that appear in the stakeholder's own systems.
- Every assumption has a risk level and a verification step.
- The stakeholder has provided written or minuted confirmation of the synthesis.

## Expected outputs

- A single-page (max 500 words) ambiguity-resolution document titled `GRILL - <Engagement Name>.md`.
- A signed-off entry in the work tracking system linking to the document.
- A list of open blockers (if any) with named owners and due dates.

## Common failure modes

1. **Facilitator solutioning during questioning.** The analyst hears the raw request and begins describing charts or models, derailing ambiguity extraction. Remedy: enforce a "no solution talk" rule until step 14 is complete.
2. **Proxy requestor.** The person in the room is not the decision-maker and cannot answer Objective/Why/Decision questions. Remedy: require the actual decision-maker to join the next session or confirm the synthesis in writing.
3. **Grain stated at report level, not row level.** Stakeholder says "it's a sales report" instead of "one invoice-line per day." Remedy: insist on a concrete example row using real identifiers.
4. **Vague success criteria like "stakeholders are happy."** Remedy: replace with behavioural or outcome metrics; if none are available, state explicitly that success will be measured by a decision-maker survey at 4 weeks post-deployment and attach it as a follow-up task.
5. **Unwritten constraints surface mid-project.** Remedy: in step 9, explicitly prompt for "regulatory, HR, legal, IT security, and cost constraints" in addition to functional ones.
6. **Existing artifacts ignored.** The team rebuilds a dashboard that already exists in a different form, wasting effort. Remedy: in step 10, open and inspect every existing artifact rather than taking the stakeholder's word about their quality.

## References to load

- `references/stakeholder-question-checklist.md` — exhaustive list of follow-up probes per category
- `references/grain-definition-examples.md` — 20 concrete examples of well- and poorly-stated grain across industries (manufacturing, logistics, finance, HR)
- `references/success-metric-patterns.md` — templates for turning vague "visibility" requests into measurable behavioural outcomes
- `references/decision-problem-canvas.md` — fillable canvas template for steps 2–12
- `references/out-of-scope-negotiation-script.md` — script for professionally pushing back on scope creep discovered during grilling

## Completion criteria

- The `GRILL - <Engagement Name>.md` document exists and contains all 11 categories with non-empty answers.
- Every persona in the `Who` section has at least one decision attached in the `Decision` section.
- Grain is written as a concrete row-level definition.
- Stakeholder confirmation of the synthesis is on file (email, ticket comment, or signed minutes).
- Any blockers are logged with an owner and a due date, or the stakeholder has explicitly accepted the reduced scope.
- The work item is transitioned out of the "Ambiguity" state and into "Business Analysis."
