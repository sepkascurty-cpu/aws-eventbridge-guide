#!/usr/bin/env python3
"""AWS EventBridge demo — publish events, create rules, archive & replay.

Usage:
    python eventbridge_demo.py --demo        # offline simulation, no AWS needed
    python eventbridge_demo.py --live --bus orders-bus --region ap-southeast-1
"""
import argparse
import json
import sys
import uuid
from datetime import datetime, timezone


def build_event(source, detail_type, detail, bus="orders-bus"):
    """Build a well-formed EventBridge event (past tense, stable ID, version)."""
    return {
        "Source": source,
        "DetailType": detail_type,
        "Detail": json.dumps(
            {
                "eventId": str(uuid.uuid4()),
                "version": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **detail,
            }
        ),
        "EventBusName": bus,
    }


def pattern_matches(pattern, event):
    """Tiny subset of EventBridge event-pattern matching (demo only).

    A rule matches when EVERY field in the pattern matches the event.
    Supports exact-value lists and {"numeric": [op, value]} conditions.
    """
    detail = json.loads(event["Detail"])
    if "source" in pattern and event["Source"] not in pattern["source"]:
        return False
    if "detail-type" in pattern and event["DetailType"] not in pattern["detail-type"]:
        return False
    for key, conditions in pattern.get("detail", {}).items():
        value = detail.get(key)
        matched = False
        for cond in conditions:
            if isinstance(cond, dict) and "numeric" in cond:
                op, threshold = cond["numeric"]
                ops = {">=": value >= threshold, ">": value > threshold,
                       "<=": value <= threshold, "<": value < threshold,
                       "=": value == threshold}
                matched = ops.get(op, False)
            elif value == cond:
                matched = True
            if matched:
                break
        if not matched:
            return False
    return True


RULES = [
    {
        "name": "high-value-orders",
        "pattern": {
            "source": ["com.myapp.orders"],
            "detail-type": ["OrderPlaced"],
            "detail": {"total": [{"numeric": [">=", 1000]}]},
        },
        "target": "Lambda: process-high-value-order",
    },
    {
        "name": "premium-orders",
        "pattern": {
            "source": ["com.myapp.orders"],
            "detail-type": ["OrderPlaced"],
            "detail": {"customerTier": ["premium"]},
        },
        "target": "Step Functions: premium-onboarding",
    },
    {
        "name": "all-orders-to-queue",
        "pattern": {
            "source": ["com.myapp.orders"],
            "detail-type": ["OrderPlaced"],
        },
        "target": "SQS: order-processing-queue",
    },
]


def demo():
    print("== EventBridge offline demo ==\n")
    events = [
        build_event("com.myapp.orders", "OrderPlaced",
                    {"orderId": "ORD-1001", "total": 250, "currency": "USD",
                     "customerTier": "standard"}),
        build_event("com.myapp.orders", "OrderPlaced",
                    {"orderId": "ORD-1002", "total": 1450, "currency": "USD",
                     "customerTier": "premium"}),
        build_event("com.myapp.orders", "OrderCancelled",
                    {"orderId": "ORD-1003", "total": 80, "currency": "USD",
                     "customerTier": "standard"}),
    ]
    archive = []
    for event in events:
        detail = json.loads(event["Detail"])
        archive.append(event)  # archive stores EVERYTHING on the bus
        print(f"Published {event['DetailType']} {detail['orderId']} "
              f"(total ${detail['total']}, {detail['customerTier']})")
        hits = [r for r in RULES if pattern_matches(r["pattern"], event)]
        if not hits:
            print("  -> no rule matched (event still archived)")
        for rule in hits:
            print(f"  -> rule '{rule['name']}' matched -> {rule['target']}")
    print(f"\nArchive holds {len(archive)} events — replay can re-deliver "
          "them to a fixed consumer at any time.")
    print("\nTry it: change ORD-1002 total to 999 and re-run — "
          "'high-value-orders' stops matching.")


def live(bus, region):
    import boto3

    client = boto3.client("events", region_name=region)
    print(f"== Live mode: bus '{bus}' in {region} ==\n")

    # 1. Create the custom bus (idempotent-ish: ignore if it exists)
    try:
        client.create_event_bus(Name=bus)
        print(f"Created event bus '{bus}'")
    except client.exceptions.ResourceAlreadyExistsException:
        print(f"Event bus '{bus}' already exists")

    # 2. Create rules + targets
    for rule in RULES:
        client.put_rule(
            Name=rule["name"],
            EventBusName=bus,
            EventPattern=json.dumps(rule["pattern"]),
            State="ENABLED",
            Description=f"Demo rule: {rule['name']}",
        )
        print(f"Rule '{rule['name']}' up (target: {rule['target']} — "
              "wire a real ARN in the console)")

    # 3. Enable an archive so events can be replayed later
    try:
        client.create_archive(
            ArchiveName=f"{bus}-archive",
            EventSourceArn=f"arn:aws:events:{region}:{boto3.client('sts').get_caller_identity()['Account']}:event-bus/{bus}",
            RetentionDays=30,
        )
        print(f"Archive '{bus}-archive' enabled (30-day retention)")
    except client.exceptions.ResourceAlreadyExistsException:
        print("Archive already exists")

    # 4. Publish a test event
    event = build_event("com.myapp.orders", "OrderPlaced",
                        {"orderId": "ORD-DEMO", "total": 1200,
                         "currency": "USD", "customerTier": "premium"},
                        bus=bus)
    resp = client.put_events(Entries=[event])
    entry = resp["Entries"][0]
    if "EventId" in entry:
        print(f"\nPublished OrderPlaced ORD-DEMO -> EventId {entry['EventId']}")
        print("Check CloudWatch Logs / your targets, then replay the archive "
              "from the console to re-deliver it.")
    else:
        print(f"\nPublish failed: {entry}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AWS EventBridge demo")
    parser.add_argument("--demo", action="store_true",
                        help="offline simulation (default)")
    parser.add_argument("--live", action="store_true",
                        help="run against a real AWS account")
    parser.add_argument("--bus", default="orders-bus",
                        help="event bus name for --live")
    parser.add_argument("--region", default="ap-southeast-1",
                        help="AWS region for --live")
    args = parser.parse_args()
    if args.live:
        live(args.bus, args.region)
    else:
        demo()


if __name__ == "__main__":
    main()
