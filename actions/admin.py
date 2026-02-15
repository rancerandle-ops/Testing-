from django.contrib import admin

from .models import ActionItem, ActionResponse, Category, InboundEmail, TeamMember


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "description", "created_at")
    search_fields = ("name",)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "email")


class ActionResponseInline(admin.TabularInline):
    model = ActionResponse
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = (
        "title", "status", "priority", "category", "owner",
        "due_date", "week_number", "year", "created_at",
    )
    list_filter = ("status", "priority", "category", "owner", "year", "week_number")
    search_fields = ("title", "description")
    date_hierarchy = "created_at"
    inlines = [ActionResponseInline]
    readonly_fields = ("created_at", "updated_at", "completed_at")


@admin.register(ActionResponse)
class ActionResponseAdmin(admin.ModelAdmin):
    list_display = ("action_item", "author", "created_at")
    list_filter = ("author",)
    search_fields = ("body",)


@admin.register(InboundEmail)
class InboundEmailAdmin(admin.ModelAdmin):
    list_display = ("sender", "subject", "received_at", "processed", "error")
    list_filter = ("processed",)
    search_fields = ("sender", "subject", "body_plain")
    readonly_fields = ("received_at",)
