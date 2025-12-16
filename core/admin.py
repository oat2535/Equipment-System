from django.contrib import admin
from .models import Category, Equipment, Requisition, UserProfile

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'total_quantity', 'available_quantity', 'image', 'description', 'serial_number', 'status')
    list_filter = ('category', 'status')
    search_fields = ('name', 'serial_number', 'description')

@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'equipment', 'quantity', 'date', 'status', 'reason', 'return_date', 'actual_return_date', 'approve_date', 'reject_date', 'reject_reason', 'approved_by', 'rejected_by', 'received_by')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'equipment__name', 'reason')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company', 'branch', 'department', 'employee_id')
    search_fields = ('user__username', 'employee_id', 'department')

