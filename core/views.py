from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
import csv
from django.utils import timezone
from django import forms
from django.core.paginator import Paginator
from .models import Equipment, Requisition, Category
from .forms import RequisitionForm, EquipmentForm, RequisitionFilterForm

# Create your views here.
@login_required
def dashboard(request):
    equipment_count = Equipment.objects.count()
    requisition_count = Requisition.objects.count()
    pending_count = Requisition.objects.filter(status='PENDING').count()
    my_pending_count = Requisition.objects.filter(user=request.user, status='PENDING').count()
    
    context = {
        'equipment_count': equipment_count,
        'requisition_count': requisition_count,
        'pending_count': pending_count,
        'my_pending_count': my_pending_count,
    }
    return render(request, 'dashboard.html', context)

@login_required
def equipment_list(request):
    equipment_list = Equipment.objects.all().order_by('-pk')
    return render(request, 'equipment_list.html', {'equipment_list': equipment_list})

@login_required
def search_equipment(request):
    query = request.GET.get('q', '')
    page_number = request.GET.get('page', 1)
    
    if query:
        equipment_list = Equipment.objects.filter(
            Q(name__icontains=query) | 
            Q(serial_number__icontains=query) |
            Q(category__name__icontains=query)
        ).order_by('-pk')
    else:
        equipment_list = Equipment.objects.all().order_by('-pk')
        
    paginator = Paginator(equipment_list, 8) # 8 items per page
    page_obj = paginator.get_page(page_number)
    
    results = list(page_obj.object_list.values('id', 'name', 'serial_number', 'available_quantity', 'image', 'status', 'category__name'))
    
    data = {
        'results': results,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    }
        
    return JsonResponse(data)

# @login_required
# def add_to_cart(request, equipment_id):
#     cart = request.session.get('cart', [])
#     if equipment_id not in cart:
#         cart.append(equipment_id)
#         request.session['cart'] = cart
#     return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

# @login_required
# def remove_from_cart(request, equipment_id):
#     cart = request.session.get('cart', [])
#     if equipment_id in cart:
#         cart.remove(equipment_id)
#         request.session['cart'] = cart
#     return redirect('cart_detail')

# @login_required
# def clear_cart(request):
#     request.session['cart'] = []
#     return redirect('cart_detail')

# @login_required
# def cart_detail(request):
#     cart = request.session.get('cart', [])
#     equipment_in_cart = Equipment.objects.filter(id__in=cart)
#     return render(request, 'cart_detail.html', {'equipment_list': equipment_in_cart})

# @login_required
# def checkout(request):
#     cart = request.session.get('cart', [])
#     if not cart:
#         return redirect('dashboard')

#     if request.method == 'POST':
#         return_date = request.POST.get('return_date') # Global return date for simplicity
        
#         for equipment_id in cart:
#             equipment = get_object_or_404(Equipment, pk=equipment_id)
            
#             # Get quantity from form
#             try:
#                 request_qty = int(request.POST.get(f'quantity_{equipment_id}', 1))
#             except (ValueError, TypeError):
#                 request_qty = 1
            
#             # Validate max quantity
#             if request_qty > equipment.available_quantity:
#                  request_qty = equipment.available_quantity # Cap at available? Or skip? Let's cap.

#             if request_qty > 0:
#                 # Create Requisition
#                 Requisition.objects.create(
#                     user=request.user,
#                     equipment=equipment,
#                     quantity=request_qty,
#                     return_date=return_date if return_date else None,
#                     status='PENDING'
#                 )
                
#                 # Deduct stock immediately
#                 equipment.available_quantity -= request_qty
#                 equipment.save()
#             else:
#                  # Skip invalid qty
#                  pass
                
#         # Clear cart
#         request.session['cart'] = []
#         return redirect('my_requests')
        
#     return redirect('cart_detail')

@login_required
def equipment_request(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    if request.method == 'POST':
        form = RequisitionForm(request.POST)
        if form.is_valid():
            requisition = form.save(commit=False)
            
            # Check availability
            request_qty = requisition.quantity
            if request_qty > equipment.available_quantity:
                # Add error to form
                form.add_error('quantity', f'Only {equipment.available_quantity} items available.')
                return render(request, 'request_form.html', {'form': form, 'equipment': equipment})
                
            # Deduct from available quantity
            equipment.available_quantity -= request_qty
            equipment.save()
            
            requisition.user = request.user
            requisition.equipment = equipment
            requisition.save()
            return redirect('my_requests')
    else:
        form = RequisitionForm()
    
    return render(request, 'request_form.html', {'form': form, 'equipment': equipment})

@login_required
def my_requests(request):
    requisitions = Requisition.objects.filter(user=request.user).order_by('-date')
    return render(request, 'my_requests.html', {'requisitions': requisitions, 'now': timezone.now()})

@login_required
def manage_requests(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    requisitions = Requisition.objects.all().order_by('-date')
    return render(request, 'manage_requests.html', {'requisitions': requisitions})

@login_required
def approve_request(request, requisition_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    requisition = get_object_or_404(Requisition, pk=requisition_id)
    requisition.status = 'APPROVED'
    requisition.approve_date = timezone.now()
    requisition.save()
    return redirect('manage_requests')

@login_required
def reject_request(request, requisition_id):
    if not request.user.is_staff:
        return redirect('dashboard')
        
    requisition = get_object_or_404(Requisition, pk=requisition_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reject_reason', '')
        
        # Restore quantity if rejected (Actually we deducted on Request, so we MUST restore on Reject)
        equipment = requisition.equipment
        equipment.available_quantity += requisition.quantity
        equipment.save()
        
        requisition.status = 'REJECTED'
        requisition.reject_date = timezone.now()
        requisition.reject_reason = reason
        requisition.save()
        
    return redirect('manage_requests')

@login_required
def receive_request(request, requisition_id):
    if not request.user.is_staff:
        return redirect('dashboard')
        
    requisition = get_object_or_404(Requisition, pk=requisition_id)
    
    # Only process if currently Approved
    if requisition.status == 'APPROVED':
        requisition.status = 'RETURNED'
        requisition.actual_return_date = timezone.now()
        requisition.save()
        
        # Restore stock
        equipment = requisition.equipment
        equipment.available_quantity += requisition.quantity
        equipment.save()
        
    return redirect('manage_requests')

@login_required
def scan_qr(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'scan_qr.html')

@login_required
def request_report(request):
    if not request.user.is_staff:
        return redirect('dashboard')
        
    form = RequisitionFilterForm(request.GET)
    requisitions = None
    
    # Check if any filter parameters are present (even if empty strings)
    # This implies the user clicked "Filter"
    if request.GET:
        if form.is_valid():
            requisitions = Requisition.objects.all().order_by('-date')
            
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            category = form.cleaned_data.get('category')
            
            if start_date:
                requisitions = requisitions.filter(date__date__gte=start_date)
            if end_date:
                requisitions = requisitions.filter(date__date__lte=end_date)
            if category:
                requisitions = requisitions.filter(equipment__category=category)
                
            # CSV Export
            if request.GET.get('export') == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="requisition_report.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['ID', 'Equipment', 'Quantity', 'User', 'Request Date', 'Approve Date', 'Reject Date', 'Returned Date', 'Status'])
                
                for req in requisitions:
                    writer.writerow([
                        req.pk,
                        req.equipment.name,
                        req.quantity,
                        req.user.username,
                        req.date.strftime('%Y-%m-%d %H:%M'),
                        req.approve_date.strftime('%Y-%m-%d %H:%M') if req.approve_date else '-',
                        req.reject_date.strftime('%Y-%m-%d %H:%M') if req.reject_date else '-',
                        req.actual_return_date.strftime('%Y-%m-%d %H:%M') if req.actual_return_date else '-',
                        req.get_status_display()
                    ])
                
                return response
            
    return render(request, 'request_report.html', {'requisitions': requisitions, 'form': form})

@login_required
def add_equipment(request):
    if not request.user.is_staff:
        return redirect('equipment_list')
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    
    return render(request, 'add_equipment.html', {'form': form})

@login_required
def edit_equipment(request, equipment_id):
    if not request.user.is_staff:
        return redirect('equipment_list')
    
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            form.save()
            return redirect('equipment_list')
    else:
        form = EquipmentForm(instance=equipment)
    
    return render(request, 'edit_equipment.html', {'form': form, 'equipment': equipment})

@login_required
def delete_equipment(request, equipment_id):
    if not request.user.is_staff:
        return redirect('equipment_list')
    
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    if request.method == 'POST':
        equipment.delete()
        return redirect('equipment_list')
    
    return redirect('equipment_list')

# User Management Views
from django.contrib.auth.models import User
from django.db import models
from .forms import UserForm, UserProfileForm
from .models import UserProfile

# Monkey patch User model to support Integer fields for booleans
# This fixes the ProgrammingError where DB expects 0/1 but Django sends true/false
try:
    User._meta.get_field('is_superuser').__class__ = models.IntegerField
    User._meta.get_field('is_staff').__class__ = models.IntegerField
    User._meta.get_field('is_active').__class__ = models.IntegerField
except Exception as e:
    pass


@login_required
def user_list(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})

@login_required
def add_user(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            
            # Handle is_staff from profile form mapping
            is_staff_val = int(profile_form.cleaned_data['is_staff'])
            user.is_staff = is_staff_val
            
            # Fix for integer column types in auth_user
            if is_staff_val == 1:
                user.is_superuser = 1 
            else:
                user.is_superuser = 0
                
            user.is_active = 1 # Force active to integer 1
            
            user.save()
            
            # Profile is auto-created by signal, so we update it
            # But wait, signal creates empty profile. We should update it.
            # actually we can save profile form with commit=False to get instance, 
            # but user instance must be assigned.
            
            # Easier: Get the created profile and update it
            if not hasattr(user, 'userprofile'):
                 UserProfile.objects.create(user=user)
            
            profile = user.userprofile
            profile.company = profile_form.cleaned_data['company']
            profile.branch = profile_form.cleaned_data['branch']
            profile.department = profile_form.cleaned_data['department']
            profile.employee_id = profile_form.cleaned_data['employee_id']
            profile.save()
            
            return redirect('user_list')
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()
        
    return render(request, 'add_user.html', {
        'user_form': user_form, 
        'profile_form': profile_form
    })

@login_required
def edit_user(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
        
    user_obj = get_object_or_404(User, pk=user_id)
    
    # Ensure profile exists
    if not hasattr(user_obj, 'userprofile'):
        UserProfile.objects.create(user=user_obj)
        
    if request.method == 'POST':
        # Pass instance to update existing
        # Use EditUserForm here
        from .forms import EditUserForm
        user_form = EditUserForm(request.POST, instance=user_obj)
        profile_form = UserProfileForm(request.POST, instance=user_obj.userprofile)
        
        if user_form.is_valid() and profile_form.is_valid():
             user = user_form.save(commit=False)
             
             # Only update password if provided
             password = user_form.cleaned_data.get('password')
             if password:
                user.set_password(password)
             
             is_staff_val = int(profile_form.cleaned_data['is_staff'])
             user.is_staff = is_staff_val
             
             # Fix for integer column types in auth_user
             if is_staff_val == 1:
                user.is_superuser = 1 
             else:
                user.is_superuser = 0
                
             user.is_active = 1

             user.save()
             
             profile_form.save()
             return redirect('user_list')
    else:
        from .forms import EditUserForm
        user_form = EditUserForm(instance=user_obj)
        # Pre-populate is_staff
        initial_staff = 1 if user_obj.is_staff else 0
        profile_form = UserProfileForm(instance=user_obj.userprofile, initial={'is_staff': initial_staff})
        # Clear password field for display (handled by form definition, but specific overwrite if needed)
        # user_form.fields['password'].widget = forms.HiddenInput() # No longer needed as we want to show empty optional field
        
    return render(request, 'edit_user.html', {
        'user_form': user_form, 
        'profile_form': profile_form,
        'edit_user': user_obj
    })

@login_required
def delete_user(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user_obj.delete()
        return redirect('user_list')
    return redirect('user_list')
