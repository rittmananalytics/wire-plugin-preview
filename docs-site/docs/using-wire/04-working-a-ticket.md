---
sidebar_position: 4
title: "Working a Ticket"
---

# Working a Ticket

Six weeks after the Northwind Retail dashboards went live, the retail operations director raises a ticket. Her regional managers have started asking about returns: one region is refunding more than the others and nobody can see it. She wants a returns rate on the Sales Overview page, by store and by month, and she would like it before the next regional review, which is a fortnight away. The ticket is number 31 in the client's tracker, it is one paragraph long, and it is the whole of the brief.

This is how most of the work on a live platform arrives. Not a statement of work and a fresh repository, but a ticket against something that already exists, raised by someone who has been using the dashboards long enough to know what is missing. The release that built the platform is still there, with its requirements, its design documents, its business definitions and its record of every decision, and the repository now belongs to the client, whose analytics engineer reviews every pull request before it is merged. The question is how to make a change that is small, correct and consistent with everything already built, without redoing the work that built it.

In Chapter 2 Wire planned the release from the statement of work and the release-type definition. Here it plans from the ticket, inside the release that already exists. Everything else is the same: you say what you want, Wire says what it will do and why, does it, and stops where a decision is yours. The difference is what Wire plans from, and how much of the earlier work it can reuse rather than repeat.

## Before You Begin

You will need the Northwind repository checked out, with the Store Performance release in it from Chapter 2, and the ticket text. You will also need to know who accepts the change: at Northwind the analytics engineer approves the code through the pull request, and the retail operations director owns the definition of a return, because a return is a business fact about how her stores trade and not a technical one.

At a high level, the ticket runs through five stages:

1. Open the release and find what already bears on the ticket.
2. Agree a plan, one step at a time, before anything is built.
3. Build the change, and deal with a test that fails.
4. Raise the pull request and let the client's review stand as acceptance.
5. Close the ticket, and bring the release's documents back into line with the code.

Let's take each in turn.

## Stage 1: Opening the Release

Open Claude Code in the Northwind repository and say what you want to work on. Wire's first job is not to plan but to read: it goes back through the release and tells you what it found that bears on this ticket, so that the plan it proposes in the next stage starts from what Northwind already agreed rather than from a blank page.

| You say | Wire replies |
|---|---|
| "Ticket 31 on the Store Performance release. Add a returns rate to the Sales Overview page, by store and by month. The ticket text is in the tracker." | "Store Performance release opened. Two pieces of work have been done on it since go-live: ticket 24 (the footfall conversion rename, merged) and ticket 27 (a fix to the like-for-like exclusion for refitted stores, merged). Reading the release for anything that bears on returns. Three things. The till export already carries refund transactions: they are loaded but excluded from the sales fact by a decision made in the build, recorded on 14 March with the reason 'refunds out of scope for release one'. The business definitions register has no entry for a return, and the requirements do not mention one. The Sales Overview page has four headline tiles and the design allows six. Ticket 31 opened on the release. Anything to add to the ticket text before I plan?" |
| "The director has said exchanges shouldn't count as returns. Otherwise no." | "Noted against the ticket. One question the plan depends on: is a return a refund transaction, or a refund line? The till export has both, and the store league table counts transactions. I will propose transactions, matching the rest of the page, and flag it for the director to confirm." |

Notice that Wire did not ask you what a return is. It found the refund transactions in the till data, found the decision that excluded them and the reason, found that the definition had never been agreed, and proposed the one reading of the ticket that is consistent with what the page already shows. It also told you what has changed on the release since you last looked, which matters when more than one person works on it.

:::note
A ticket is opened on the release, not as a release of its own. Everything Wire found in that first reply came from the release's record: the requirements, the design, the definitions and the decisions log. Had the ticket been given a release of its own, none of that would have been in front of it, and the decision that excluded refunds in March would have been rediscovered the hard way, in a failing reconciliation.
:::

## Stage 2: The Plan

Wire proposes a plan before it touches anything, and the plan names each step in the words of the method rather than in Wire's own terms: what will be agreed, designed, built, checked and published, and in what order. Where a step is a piece of work Wire will do, it says so. Where a step belongs to a person, it says whose.

| You say | Wire replies |
|---|---|
| *(nothing)* | "Plan for ticket 31, in six steps. **1. Agree the definition.** Add 'return' to the business definitions register: a refund transaction against a sale, exchanges excluded, counted in the month of the refund. Proposed, for the operations director to confirm. **2. Change the sales fact.** Add two counts to the sales fact table, returned transactions and sold transactions, per store per day, citing the new definition. Nothing else in the table changes. **3. Build and test.** Build the changed table and everything that reads from it, and run the tests. **4. Add the measure.** Add returns rate to the store sales definitions Looker uses, as returned over sold. **5. Add the tile.** One tile on the Sales Overview page, returns rate by month with the store and region filters, matching the style of the four tiles beside it. **6. Publish.** A pull request on the client's template with the test results attached, for the analytics engineer to review. Not in this plan: the requirements, the business concepts and the data model design. The ticket does not add a concept or change a table's grain, so those documents are not redrafted; the two lines in them that this change affects are patched at the end, and you see the patches first. Approve the plan, change it, or ask me to explain a step?" |
| "Explain step 1. The director just wants a number." | "The number depends on the definition. Whether an exchange is a return changes the rate by about a fifth at the two stores with the highest exchange volume, on last quarter's till data. If the definition is written down and cited by the table, the measure and the tile, there is one thing for the director to confirm and one place to change it if she changes her mind. If it is not, there are three implementations to keep in step, and the March decision to exclude refunds shows how a reason gets lost when it lives only in code. It adds about two minutes to the plan." |
| "Approve." | "Approved under your name. Starting step 1." |

Three things are worth noticing. The plan is small, because the release already holds the requirements and the design and Wire could see that the ticket does not disturb either. It says what it leaves out and why, which is how you know Wire has considered the whole method and not just the part in front of it. And when you asked for the reasoning behind a step, you got the consequence of skipping it in Northwind's own numbers rather than a general principle.

In Chapter 7 you will see this same kind of plan with the command that runs each step written beside it. The steps are the method; the commands are how each one is invoked, and the plan is the same either way.

## Stage 3: The Build, and a Test That Fails

From here the pattern is the one you saw in Chapter 2: Wire says what it is about to do, does it, checks it and reports. The difference on a ticket is that each step is scoped to the change and no wider, and Wire tells you the scope each time.

| You say | Wire replies |
|---|---|
| *(later)* | "Step 1 done. 'Return' added to the definitions register as proposed, status: awaiting the operations director. Step 2: changing the sales fact table only. Two new counts, named to the convention, each with a description and a citation of the new definition. No other table is touched. Written. Convention checks pass." |
| *(later)* | "Step 3: built the sales fact and the three things that read from it, and ran 23 tests. One failed. The sold-transactions count is empty for 212 store-days, all of them days when a store was closed for refit and the till recorded no sales at all. The test says the count must never be empty. Three ways to resolve this. Count zero for those days, which is what the like-for-like rule already does for closed stores; recommended. Leave those days out of the table, which changes the league table's day counts from ticket 27. Or stop and ask the director. Which?" |
| "Zero." | "Recorded as a decision under your name, with the reason: consistent with the like-for-like treatment of closed stores. Plan step 2 amended to say so. Rebuilt and retested: 23 of 23 pass. Step 4: returns rate added to the store sales definitions, citing the return definition. Step 5: one tile added to Sales Overview, between Average Basket and Like-for-Like, region and store filters applied, same colour and number format as its neighbours. Cross-check against the page design: pass. Open the development dashboard to see it." |

The failing test is the useful part of that exchange. Wire did not fix it quietly, because a fix is a decision about what the data means, and it did not stop dead either. It told you what failed, on which rows and why, proposed the treatment consistent with a rule the release already had, told you what the alternative would disturb, and recorded your answer with its reason next to the decisions from the original build. The plan now shows the amendment, so that anyone reading it later sees what was approved and what changed during the work.

:::note
Wire built and tested only the changed table and the things that depend on it, not the whole project. On a platform with a few dozen models that is the difference between a minute and twenty, and it is safe because the tests on the untouched models passed when they were last built and nothing upstream of them has changed. If something had, Wire would have widened the build and said so.
:::

## Stage 4: The Pull Request, and Whose Approval Counts

On a client-owned repository the client's pull request review is the acceptance step for code, and Wire treats it as one rather than asking you to hold a separate review of your own. What it adds is the evidence the reviewer needs: the tests that ran, the checks that passed, the definitions cited and the decisions made along the way.

| You say | Wire replies |
|---|---|
| *(later)* | "Step 6: pull request 91 raised on Northwind's template. Body: the ticket, the six steps, 23 of 23 tests passing, convention checks passing, the return definition cited by the table, the measure and the tile, and the closed-store decision with its reason. Assigned to the analytics engineer for review. Two things are now waiting on other people: the pull request review, and the operations director's confirmation of the return definition. The second is not something the analytics engineer can give, because it is a business definition and not a code review, so I will keep it open until she confirms it or you tell me she has." |

That last sentence is the point of the stage. A pull request approval accepts the code. It does not settle what a return is, and Wire will not let one stand in for the other, because the director owns that definition and a rate built on a definition she has not seen is exactly the situation the register exists to prevent.

## Stage 5: Closing the Ticket

Before Wire calls the ticket done, it does two things in order. It looks at the release's documents and tells you which of them the change has made out of date, proposing the smallest patch to each and showing it to you before writing anything. Then it brings the release's status and log up to date, so that the record shows the ticket and what ran for it.

| You say | Wire replies |
|---|---|
| *(nothing)* | "Steps 1 to 6 done. Steps waiting on others: the review, and the director's confirmation. Checking the release's documents against the change. Two are out of date. The data model design lists the sales fact's columns and does not have the two new counts: a two-line patch. The requirements say nothing about returns, and there is now a tile that the client asked for and no requirement behind it: a one-line addition, traced to ticket 31, marked as raised after go-live. The business concepts and the page design need no change. Apply both patches?" |
| "Yes." | "Applied and shown in the pull request as two further files. Status updated: ticket 31 is on the release's iterations list as 'awaiting client review', with its branch and pull request. The record shows what ran for it: the six steps, the failing test, the decision and the two patches, in order. The ticket is not closed. Waiting on the analytics engineer and the operations director." |

The patches matter more than their size suggests. Without them the data model document would describe a table that no longer exists as described, and the next person to open the release, six months from now, would trust the document over the code and be wrong. Wire keeps the documents true by patching them at the end of each ticket, with your agreement, rather than by regenerating them, which would be slower and would risk changing things the ticket never touched.

## Two Days Later

The analytics engineer approves and merges the pull request the next afternoon. The operations director is harder to pin down, but she was on Tuesday's regional call, which was recorded.

| You say | Wire replies |
|---|---|
| "Ticket 31. Where are we?" | "Pull request 91 was approved by the analytics engineer and merged yesterday at 16:20. That accepts the code. The return definition is still awaiting the operations director. Tuesday's regional call was recorded, and at 14 minutes in she says, of the returns tile on the development dashboard, 'that's the right number, as long as swaps aren't in it.' Exchanges are excluded, as she asked. Treat that as her confirmation and record it against the recording, or wait for her in writing?" |
| "Record it." | "Return definition confirmed by the operations director, source: regional call, Tuesday, 14:10. All six steps done, both approvals in from the people who own them, tests passing, documents patched, record complete. Ticket 31 closed. The tile is live in production with the Wednesday morning refresh." |

The ticket took two sessions and about ten messages from you, and most of the messages were decisions. Every one of them, and every step Wire took, is in the release's record beside the decisions from the original build, so that the release still tells one story from the statement of work to the latest ticket.

## A Request That Is Not a Ticket

Not every request that arrives as a ticket is one. The following week the director asks, in ticket 34, for customer complaints to appear alongside sales, and the complaints live in a helpdesk system that Northwind has never connected.

| You say | Wire replies |
|---|---|
| "Ticket 34. Add complaints per store from the helpdesk system, on the Store League Table." | "This is not a change I would make as a ticket on the Store Performance release, and I want to say why before proposing anything. It adds a source system that has never been assessed, it adds a business concept (a complaint) that the design does not have, and it needs a pipeline that does not exist. Any of those on its own is a design change; together they are a small release. Two ways forward. Plan it as a new release alongside this one, which starts with a short look at the helpdesk data and an agreed definition of a complaint, and would take about a week; recommended. Or add it to this release as a formal design phase, which keeps it in one place but reopens the design documents that ticket 31 left settled. Which?" |

Wire refused to treat the request as a small change, said exactly which of its properties made it larger than it looked, and offered the two sensible shapes for it with a recommendation. That boundary is one you will lean on. A ticket that quietly grows into a redesign is how a fortnight becomes a quarter, and it is far cheaper to notice at the planning step than in the third week.

## What You Should Now Have

| Produced | Detail |
|---|---|
| Business definitions register | One new entry, 'return', confirmed by the operations director against a recording |
| Sales fact table | Two new counts, cited to the definition, closed-store days counted as zero by a recorded decision |
| Tests | 23 passing, one of them the test that failed and drove the decision |
| Store sales definitions | Returns rate measure |
| Sales Overview page | One new tile, matching its neighbours |
| Pull request 91 | Merged, with the evidence attached, on the client's template |
| Data model and requirements | Two small patches, shown before they were written |
| The release record | Ticket 31 on the iterations list, with its branch, pull request, steps, decision and approvals |

## What If Something Goes Wrong?

The commonest problem on a ticket is discovering, part way through, that it is bigger than it looked: the test that fails turns out to expose a design fault rather than a data quirk, or the change needs a second table after all. Wire's behaviour then is the one you saw at the failing test: it stops, says what it found, offers a plan amendment or, if the change has crossed the line described above, a formal release, and waits. The other common problem is an approval that never quite arrives, and there the record is your friend: the ticket stays open, the status says exactly who it is waiting on, and nothing is called done that is not.

In the next chapter we leave code behind entirely and look at a discovery, where the sources are interview recordings and the most important gate belongs to the client's sponsor rather than to you.
