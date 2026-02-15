from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from actions.models import ActionItem, ActionResponse, Category, TeamMember


@login_required
def home(request):
    """Main dashboard showing current week summary and recent items."""
    now = timezone.now()
    current_week = now.isocalendar()[1]
    current_year = now.year

    items = ActionItem.objects.select_related("category", "owner")

    # Filters from query params
    status = request.GET.get("status")
    owner_id = request.GET.get("owner")
    category_id = request.GET.get("category")
    priority = request.GET.get("priority")
    week = request.GET.get("week", str(current_week))
    year = request.GET.get("year", str(current_year))

    if week and year:
        items = items.filter(week_number=int(week), year=int(year))
    if status:
        items = items.filter(status=status)
    if owner_id:
        items = items.filter(owner_id=owner_id)
    if category_id:
        items = items.filter(category_id=category_id)
    if priority:
        items = items.filter(priority=priority)

    # Summary stats
    total = items.count()
    open_count = items.filter(status__in=["open", "in_progress", "blocked"]).count()
    completed_count = items.filter(status="completed").count()

    # Status breakdown
    status_counts = dict(items.values_list("status").annotate(c=Count("id")))

    context = {
        "items": items[:50],
        "total": total,
        "open_count": open_count,
        "completed_count": completed_count,
        "status_counts": status_counts,
        "categories": Category.objects.all(),
        "team_members": TeamMember.objects.filter(is_active=True),
        "statuses": ActionItem.Status.choices,
        "priorities": ActionItem.Priority.choices,
        "current_week": current_week,
        "current_year": current_year,
        "filter_status": status or "",
        "filter_owner": owner_id or "",
        "filter_category": category_id or "",
        "filter_priority": priority or "",
        "filter_week": week,
        "filter_year": year,
    }
    return render(request, "dashboard/home.html", context)


@login_required
def action_detail(request, pk):
    """View a single action item with its responses."""
    item = get_object_or_404(
        ActionItem.objects.select_related("category", "owner"),
        pk=pk,
    )
    responses = item.responses.select_related("author").all()
    return render(request, "dashboard/detail.html", {
        "item": item,
        "responses": responses,
        "team_members": TeamMember.objects.filter(is_active=True),
        "categories": Category.objects.all(),
    })


@login_required
def action_update(request, pk):
    """Update an action item's status, owner, category, or priority."""
    item = get_object_or_404(ActionItem, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        new_owner = request.POST.get("owner")
        new_category = request.POST.get("category")
        new_priority = request.POST.get("priority")
        due_date = request.POST.get("due_date")

        if new_status and new_status in dict(ActionItem.Status.choices):
            item.status = new_status
        if new_owner:
            item.owner_id = int(new_owner) if new_owner != "none" else None
        if new_category:
            item.category_id = int(new_category) if new_category != "none" else None
        if new_priority and new_priority in dict(ActionItem.Priority.choices):
            item.priority = new_priority
        if due_date:
            item.due_date = due_date
        elif "due_date" in request.POST:
            item.due_date = None

        item.save()

    return redirect("dashboard:detail", pk=pk)


@login_required
def add_response(request, pk):
    """Add a response/comment to an action item."""
    item = get_object_or_404(ActionItem, pk=pk)
    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        if body:
            # Try to find a TeamMember matching the logged-in user's email
            author = TeamMember.objects.filter(
                email__iexact=request.user.email,
            ).first()
            ActionResponse.objects.create(
                action_item=item,
                author=author,
                body=body,
            )
    return redirect("dashboard:detail", pk=pk)


@login_required
def action_create(request):
    """Manually create a new action item from the dashboard."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            return redirect("dashboard:home")

        item = ActionItem(
            title=title,
            description=request.POST.get("description", ""),
            priority=request.POST.get("priority", ActionItem.Priority.MEDIUM),
            created_by=request.user,
        )
        owner_id = request.POST.get("owner")
        if owner_id:
            item.owner_id = int(owner_id)
        category_id = request.POST.get("category")
        if category_id:
            item.category_id = int(category_id)
        due_date = request.POST.get("due_date")
        if due_date:
            item.due_date = due_date

        item.save()
        return redirect("dashboard:detail", pk=item.pk)

    return render(request, "dashboard/create.html", {
        "categories": Category.objects.all(),
        "team_members": TeamMember.objects.filter(is_active=True),
        "priorities": ActionItem.Priority.choices,
    })


@login_required
def weekly_report(request, year, week):
    """View a weekly report for a specific year/week."""
    items = ActionItem.objects.filter(
        year=year, week_number=week,
    ).select_related("category", "owner")

    by_category = {}
    for item in items:
        cat_name = item.category.name if item.category else "Uncategorized"
        by_category.setdefault(cat_name, []).append(item)

    by_owner = {}
    for item in items:
        owner_name = item.owner.name if item.owner else "Unassigned"
        by_owner.setdefault(owner_name, []).append(item)

    total = items.count()
    completed = items.filter(status="completed").count()

    return render(request, "dashboard/weekly_report.html", {
        "year": year,
        "week": week,
        "items": items,
        "by_category": by_category,
        "by_owner": by_owner,
        "total": total,
        "completed": completed,
    })
