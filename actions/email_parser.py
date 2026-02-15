"""
Parse inbound emails to extract action items and responses.

Supports two email flows:
1. New action items — a fresh email sent to the tracker address
2. Responses — replies to existing action item notification emails
"""

import re

from .models import ActionItem, ActionResponse, Category, InboundEmail, TeamMember


# Patterns that indicate an action item line in the email body
ACTION_PATTERNS = [
    re.compile(r"^[-*]\s*\[?\s*\]?\s*(.+)$", re.MULTILINE),        # - [ ] task  or  - task
    re.compile(r"^\d+[.)]\s+(.+)$", re.MULTILINE),                   # 1. task  or  1) task
    re.compile(r"^(?:action|todo|task|ai)\s*[:]\s*(.+)$", re.MULTILINE | re.IGNORECASE),
]

# Pattern to detect @mentions for owner assignment
OWNER_PATTERN = re.compile(r"@(\S+)")

# Pattern to detect category tags like [Engineering] or #engineering
CATEGORY_PATTERN = re.compile(r"(?:\[([^\]]+)\]|#(\w+))")

# Priority keywords
PRIORITY_MAP = {
    "urgent": ActionItem.Priority.URGENT,
    "high": ActionItem.Priority.HIGH,
    "medium": ActionItem.Priority.MEDIUM,
    "low": ActionItem.Priority.LOW,
    "p0": ActionItem.Priority.URGENT,
    "p1": ActionItem.Priority.HIGH,
    "p2": ActionItem.Priority.MEDIUM,
    "p3": ActionItem.Priority.LOW,
}
PRIORITY_PATTERN = re.compile(
    r"(?:!!(urgent|high|medium|low)|!!(p[0-3]))", re.IGNORECASE
)


def _detect_priority(text):
    """Extract priority from text, defaulting to MEDIUM."""
    match = PRIORITY_PATTERN.search(text)
    if match:
        keyword = (match.group(1) or match.group(2)).lower()
        return PRIORITY_MAP.get(keyword, ActionItem.Priority.MEDIUM)
    if any(word in text.lower() for word in ("urgent", "asap", "critical")):
        return ActionItem.Priority.URGENT
    if "high priority" in text.lower():
        return ActionItem.Priority.HIGH
    return ActionItem.Priority.MEDIUM


def _detect_category(text):
    """Extract or create a category from text."""
    match = CATEGORY_PATTERN.search(text)
    if match:
        name = (match.group(1) or match.group(2)).strip()
        category, _ = Category.objects.get_or_create(
            name__iexact=name, defaults={"name": name}
        )
        return category
    return None


def _detect_owner(text):
    """Find a team member mentioned with @ in the text."""
    match = OWNER_PATTERN.search(text)
    if match:
        identifier = match.group(1).lower()
        member = TeamMember.objects.filter(
            is_active=True,
        ).filter(
            email__istartswith=identifier,
        ).first()
        if not member:
            member = TeamMember.objects.filter(
                is_active=True,
                name__icontains=identifier,
            ).first()
        return member
    return None


def _clean_action_text(text):
    """Remove inline markers (@mentions, categories, priority) for the title."""
    text = OWNER_PATTERN.sub("", text)
    text = CATEGORY_PATTERN.sub("", text)
    text = PRIORITY_PATTERN.sub("", text)
    return text.strip()


def _extract_action_lines(body):
    """Pull individual action item lines from the email body."""
    lines = []
    for pattern in ACTION_PATTERNS:
        for match in pattern.finditer(body):
            line = match.group(1).strip()
            if line and len(line) > 3:
                lines.append(line)
    return lines


def _find_existing_action_item_by_reply(in_reply_to):
    """Find an action item that matches the In-Reply-To header."""
    if not in_reply_to:
        return None
    return ActionItem.objects.filter(source_email_id=in_reply_to).first()


def process_inbound_email(email_record: InboundEmail):
    """
    Process a single InboundEmail record.

    Returns a list of created ActionItem or ActionResponse objects.
    """
    created = []
    sender_member = TeamMember.objects.filter(email__iexact=email_record.sender).first()

    # Check if this is a reply to an existing action item
    existing_item = _find_existing_action_item_by_reply(email_record.in_reply_to)
    if existing_item:
        response = ActionResponse.objects.create(
            action_item=existing_item,
            author=sender_member,
            body=email_record.body_plain,
            source_email_id=email_record.message_id,
        )
        created.append(response)
        email_record.processed = True
        email_record.save()
        return created

    # Otherwise, parse the email for new action items
    action_lines = _extract_action_lines(email_record.body_plain)

    # If no structured action items found, treat the whole email as one item
    if not action_lines:
        action_lines = [email_record.subject]

    # Shared category from subject line
    subject_category = _detect_category(email_record.subject)

    for line in action_lines:
        title = _clean_action_text(line)
        if not title:
            continue

        category = _detect_category(line) or subject_category
        owner = _detect_owner(line) or sender_member
        priority = _detect_priority(line)

        item = ActionItem(
            title=title,
            description=email_record.body_plain,
            category=category,
            owner=owner if isinstance(owner, TeamMember) else None,
            priority=priority,
            source_email_id=email_record.message_id,
        )
        item.save()
        created.append(item)

    email_record.processed = True
    email_record.save()
    return created
