
# tabletapapp/views.py
import os
import json
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View

from dotenv import load_dotenv
import openai
from openai import OpenAI

from .forms import CustomUserCreationForm, CustomLoginForm, CustomUserUpdateForm
from .models import Menu, MenuItem, CustomUser, Table, Order, OrderItem, MenuCategory


def index(request):
    return render(request, "index.html")

@login_required
def editmenu(request):
    return render(request, 'editmenu.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = CustomUser.objects.get(username=username, email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, 'Invalid username or email.')
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            if user.is_superuser:
                return redirect('manage')
            else:
                return redirect('login')
        else:
            messages.error(request, 'Invalid password.')
            return render(request, 'login.html')

    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('manage')
        else:
            return render(request, 'login.html', {'dashboard': True})

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def order(request):
    # Get all orders with their related items
    orders = Order.objects.all().order_by('-updated_at')
    
    # Store order items for each order
    orders_with_items = []
    
    for order in orders:
        # Get all items for this order
        order_items = OrderItem.objects.filter(order=order).select_related('item')
        
        # Calculate total items
        total_items = sum(item.quantity for item in order_items)
        
        # Format items for JSON inclusion in template
        formatted_items = []
        for item in order_items:
            formatted_items.append({
                'name': item.item.name,
                'quantity': item.quantity,
                'price': float(item.price),
                'subtotal': float(item.price * item.quantity)
            })
        
        # Create a data structure with order and its items
        order_data = {
            'id': order.id,
            'table_number': order.table.id if hasattr(order.table, 'id') else order.table.number,
            'status': order.status,
            'updated_at': order.updated_at,
            'date': order.updated_at.strftime('%Y-%m-%d'),
            'time': order.updated_at.strftime('%I:%M %p'),
            'total_items': total_items,
            'total_price': float(order.total_amount),
            'items': json.dumps(formatted_items)  # JSON encode the items list
        }
        
        orders_with_items.append(order_data)
    
    # Pass the orders with their items to the template
    return render(request, 'order.html', {'orders': orders_with_items})

@login_required
def qrcode(request):
    return render(request, 'qrcode.html')

def table_view(request, table_number):
    # Get the active menu
    active_menu = Menu.objects.filter(active=True, archived=False).first()
    
    if not active_menu:
        return HttpResponseBadRequest("No active menu available")
    
    # Get active categories from active menu
    menu_categories = MenuCategory.objects.filter(
        menu=active_menu,
        active=True
    ).order_by('order')
    
    context = {
        'table_number': table_number,
        'menu': active_menu,
        'menu_categories': menu_categories,
    }
    
    return render(request, 'table_view.html', context)



def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Make sure that all fields are filled in
        if not username or not email or not password1 or not password2:
            messages.error(request, 'Please fill in all fields.')
            return redirect('register')

        # Ensure password matching
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        # Check whether the username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')

        # Check whether the email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already in use.')
            return redirect('register')

        try:
            # create user
            user = CustomUser.objects.create_user(username=username, email=email, password=password1)
            messages.success(request, 'Account created successfully!')
            return redirect('login')
        except Exception as e:
            print("Registration error:", e)
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('register')

    return render(request, 'register.html')  


@csrf_exempt
@require_http_methods(["POST"])
def generate_menu(request):
    try:
        if not request.body:
            return JsonResponse({'error': 'Request body is empty'}, status=400)

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'JSON Parsing error: {str(e)}'}, status=400)

        description = data.get('description')
        if not description:
            return JsonResponse({'error': 'Lack of description fields'}, status=400)

        try:
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert in dish description"},
                    {"role": "user", "content": f"Please generate a concise description of the dish based on the following description:\n{description}"}
                ],
                temperature=0.7,
                max_tokens=150
            )
            ai_output = response.choices[0].message.content.strip()
            return JsonResponse({'menu': ai_output})

        except Exception as e:
            return JsonResponse({'error': f'OpenAI API Call failed: {str(e)}'}, status=500)

    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

# A class-based view to manage and display a paginated list of subscribers
class ManageSubscribersView(ListView):
    model = CustomUser
    template_name = "manage_subscribers.html"
    context_object_name = "users"
    paginate_by = 5

    def test_func(self):
        return self.request.user.is_superuser  # only superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return HttpResponseForbidden("You do not have permission to view this page.")
        else:
            return super().handle_no_permission()

    def get_queryset(self):
        queryset = CustomUser.objects.all()
        search_query = self.request.GET.get("search", "")
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        return queryset



# A class-based view for creating a new subscriber entry
class SubscriberCreateView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = "subscriber_form.html"
    success_url = reverse_lazy("manage")



# A class-based view  for updating an existing subscriber
class SubscriberUpdateView(UpdateView):
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = "subscriber_form.html"
    success_url = reverse_lazy("manage")


# A class-based view for archiving a subscriber (UserDetail and its associated User)
class SubscriberArchiveView(View):
    template_name = "subscriber_archive.html"

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(CustomUser, pk=kwargs["pk"])
        return render(request, self.template_name, {"object": user})

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(CustomUser, pk=kwargs["pk"])
        user.is_archived = True
        user.save()
        messages.success(request, f"User '{user.username}' has been archived.")
        return redirect(reverse_lazy("manage"))

def submit_order(request):
    if request.method == 'POST':
        table_number = request.POST.get('table')
        total_price = request.POST.get('total_price')
        special_instructions = request.POST.get('special_instructions', '')
        user = request.user if request.user.is_authenticated else None
        
        if not table_number or not total_price:
            return HttpResponseBadRequest("Missing table number or total price")
        
        # Find or create table
        table, created = Table.objects.get_or_create(
            table_number=table_number,
            defaults={'user': user, 'active': True}
        )
        
        # Create order
        order = Order.objects.create(
            table=table,
            user=user,
            total_amount=total_price,
            special_instructions=special_instructions if hasattr(Order, 'special_instructions') else None
        )
        
        # Process order items
        item_count = 0
        while True:
            item_id = request.POST.get(f'item_id_{item_count}')
            item_name = request.POST.get(f'item_name_{item_count}')
            item_quantity = request.POST.get(f'item_quantity_{item_count}')
            item_price = request.POST.get(f'item_price_{item_count}')
            
            if not item_name or not item_quantity or not item_price:
                break
                
            try:
                # Try to find the menu item
                menu_item = MenuItem.objects.get(id=item_id, active=True)
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    item=menu_item,
                    quantity=item_quantity,
                    price=item_price
                )
                
                item_count += 1
            except MenuItem.DoesNotExist:
                # If the item doesn't exist, log error but continue with other items
                print(f"Menu item '{item_name}' not found or not active")
                item_count += 1
                continue
        
        if request.accepts("application/json"):
            return JsonResponse({
                "success": True,
                "order_id": order.id,
                "message": "Order submitted successfully"
            })
        else:
            # Redirect back to the table view with a success parameter
            return redirect(f"{reverse('table_view', args=[table_number])}?order_success=true")
            
    return HttpResponseBadRequest("Invalid request method")

def get_menus(request):
    """API endpoint to get all menus for the current user."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    menus = Menu.objects.filter(user=request.user, archived=False).order_by('-updated_at')
    menus_data = []
    
    for menu in menus:
        # Get categories for this menu
        categories = MenuCategory.objects.filter(menu=menu, active=True).order_by('order')
        menu_data = {
            'id': menu.id,
            'name': menu.name,
            'description': menu.description or '',
            'data': {},
            "active": menu.active,
        }
        
        # Add categories and items
        for category in categories:
            items = MenuItem.objects.filter(category=category, active=True)
            category_items = []
            
            for item in items:
                item_data = {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description or '',
                    'price': float(item.price),
                    'image': item.image.url if item.image else '',
                }
                category_items.append(item_data)
            
            menu_data['data'][category.name] = category_items
        
        menus_data.append(menu_data)
    
    return JsonResponse({'menus': menus_data})

@csrf_exempt
def create_menu(request):
    print("create_menu called")

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        print('request.user:', request.user)
        print('request.user.id:', request.user.id)

        User = get_user_model()
        if not User.objects.filter(id=request.user.id).exists():
            return JsonResponse({'error': f'User {request.user.id} not found in database.'}, status=500)

        data = json.loads(request.body)
        print('Received data:', data)

        menu_name = data.get('name', '').strip()
        menu_description = data.get('description', '').strip()

        if not menu_name:
            return JsonResponse({'error': 'Menu name is required'}, status=400)

        menu = Menu.objects.create(
            user=request.user,
            name=menu_name,
            description=menu_description
        )

        return JsonResponse({
            'success': True,
            'id': menu.id,
            'name': menu.name,
            'description': menu.description or ''
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def update_menu(request, menu_id):
    """API endpoint to update a menu's info."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    menu = get_object_or_404(Menu, id=menu_id, user=request.user)
    
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            menu_name = data.get('name', '').strip()
            menu_description = data.get('description', '').strip()
            menu_active = data.get('active')
            print("Received data:", data)
            print("menu_active:", menu_active)

            if menu_name:
                menu.name = menu_name
            
            menu.description = menu_description

            if menu_active is not None:
                menu.active = bool(menu_active)
            
            menu.save()
            
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        try:
            # Soft delete by marking as archived
            menu.archived = True
            menu.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def save_menu_data(request, menu_id):
    """API endpoint to save the entire menu structure."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    menu = get_object_or_404(Menu, id=menu_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        menu_data = data.get('data', {})
        
        # Deactivate all existing categories for this menu first
        # This is a soft delete approach
        MenuCategory.objects.filter(menu=menu).update(active=False)
        
        # Process each category
        for order, (category_name, items) in enumerate(menu_data.items()):
            # Get or create the category
            category, created = MenuCategory.objects.get_or_create(
                menu=menu,
                name=category_name,
                defaults={'order': order, 'active': True}
            )
            
            if not created:
                # If the category already existed but was deactivated, reactivate it
                category.active = True
                category.order = order
                category.save()
            
            # Deactivate all existing items for this category
            MenuItem.objects.filter(category=category).update(active=False)
            
            # Process items in this category
            for item_data in items:
                item_name = item_data.get('name', '').strip()
                item_price = item_data.get('price', 0)
                item_description = item_data.get('description', '').strip()
                item_image = item_data.get('image', '')
                item_id = item_data.get('id', None)
                
                if not item_name:
                    continue
                
                if item_id:
                    # Try to update existing item
                    try:
                        item = MenuItem.objects.get(id=item_id, category__menu=menu)
                        item.name = item_name
                        item.price = item_price
                        item.description = item_description
                        item.active = True
                        
                        # Handle image if it's a new data URL
                        if item_image and item_image.startswith('data:image'):
                            # Code to save the data URL as an image file
                            # This is a simplified approach and may need refinement
                            import base64, uuid
                            from django.core.files.base import ContentFile
                            
                            format, imgstr = item_image.split(';base64,')
                            ext = format.split('/')[-1]
                            data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                            item.image = data
                        
                        item.save()
                    except MenuItem.DoesNotExist:
                        # If the item doesn't exist or belongs to another menu, create a new one
                        item_id = None
                
                if not item_id:
                    # Create new item
                    item = MenuItem(
                        category=category,
                        name=item_name,
                        price=item_price,
                        description=item_description,
                        active=True
                    )
                    
                    # Handle image if provided
                    if item_image and item_image.startswith('data:image'):
                        import base64, uuid
                        from django.core.files.base import ContentFile
                        
                        format, imgstr = item_image.split(';base64,')
                        ext = format.split('/')[-1]
                        data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                        item.image = data
                    
                    item.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def menu_list(request):
    if request.method == 'GET':
        return get_menus(request)
    elif request.method == 'POST':
        return create_menu(request)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@require_GET
def get_order_details(request, order_id):
    try:
        # Get the order
        order = Order.objects.get(id=order_id)
        
        # Get all items for this order
        order_items = OrderItem.objects.filter(order=order).select_related('item')
        
        # Format date and time
        date_str = order.updated_at.strftime('%Y-%m-%d')
        time_str = order.updated_at.strftime('%I:%M %p')
        
        # Format items
        items_data = []
        for item in order_items:
            items_data.append({
                'item_name': item.item.name,
                'quantity': item.quantity,
                'price': float(item.price),
                'subtotal': float(item.price * item.quantity)
            })
        
        # Create response data
        order_data = {
            'id': order.id,
            'table_number': order.table.id,
            'status': order.status,
            'date': date_str,
            'time': time_str,
            'total_amount': float(order.total_amount),
            'items': items_data
        }
        
        return JsonResponse(order_data)
    
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)