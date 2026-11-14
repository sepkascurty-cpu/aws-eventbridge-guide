# Quiz — AWS EventBridge ⚡

5 questions. Answers are hidden below each question — try them first!

---

## 1. What is the difference between the default bus and a custom bus?

A. The default bus is faster than a custom bus
B. The default bus receives AWS service events; a custom bus receives your own application events
C. The default bus can only have one rule
D. A custom bus cannot have archives

<details>
<summary>Answer</summary>

**B.** Every account has a default bus that receives events emitted by AWS services themselves (EC2 state changes, S3, health events…). Custom buses are for *your* application events — create one per domain (`orders`, `payments`) to keep rules small and blast radius contained.

</details>

---

## 2. A rule has this event pattern:

```json
{
  "source": ["com.myapp.orders"],
  "detail-type": ["OrderPlaced"],
  "detail": { "total": [{ "numeric": [">=", 1000] }] }
}
```

Which event matches it?

A. `OrderPlaced`, total 250
B. `OrderCancelled`, total 5000
C. `OrderPlaced`, total 1000
D. `OrderPlaced` from source `com.myapp.payments`, total 2000

<details>
<summary>Answer</summary>

**C.** A rule matches only when **every** field in the pattern matches: source must be `com.myapp.orders`, detail-type must be `OrderPlaced`, and total must be ≥ 1000. A fails the numeric check, B fails detail-type, D fails source. Note the boundary: `>=` includes exactly 1000.

</details>

---

## 3. A downstream consumer had a bug for 3 days and dropped every order event. The bug is now fixed. What is the fastest way to recover the lost events?

A. Ask the producers to re-publish everything
B. Replay the bus archive for the last 3 days to the consumer
C. Increase the rule's retry count to 72 hours
D. Nothing — events that failed delivery are gone forever

<details>
<summary>Answer</summary>

**B.** If an **archive** was enabled on the bus, every event is stored. Create a **replay** for the affected time range and EventBridge re-delivers those events. This only works if archiving was turned on *before* the incident — enable archives on production buses from day one. Retries (C) only cover delivery failures within 24 hours, and only while the rule is still trying.

</details>

---

## 4. You need to run a report job every weekday at 02:00 Asia/Jakarta time, with retries if the first attempt fails. What should you use?

A. A Lambda function with a `time.sleep()` loop
B. A CloudWatch alarm
C. EventBridge Scheduler with a cron expression and a retry policy
D. An SQS queue with a visibility timeout

<details>
<summary>Answer</summary>

**C.** EventBridge Scheduler is the serverless cron: timezone-aware schedules, one-time or recurring, flexible time windows, built-in retry policy and DLQ — and it can invoke 270+ AWS API actions directly, no Lambda middleman needed. A is a server you babysit; B only watches metrics; D is a queue, not a scheduler.

</details>

---

## 5. You have an SQS queue full of order messages. You want to forward only messages where `total >= 1000` to a Step Functions workflow, enriching each one with customer data from an API first. Which EventBridge feature does this?

A. A rule with an input transformer
B. EventBridge Pipes (source → filter → enrichment → target)
C. EventBridge Scheduler
D. A partner event bus

<details>
<summary>Answer</summary>

**B.** **Pipes** connect a source (SQS, Kinesis, DynamoDB Streams, MSK…) to a target with optional **filtering** (only matching records pass through) and **enrichment** (a Lambda or API Destination adds data before delivery). Rules (A) match events already on a bus — they don't pull from queues. Scheduler (C) is for time-based triggers, and partner buses (D) are for SaaS events.

</details>

---

**Score:** 5/5 — you run the bus. 3–4/5 — solid, re-read the Rules and Pipes sections. 0–2/5 — re-read the README, then try again!
