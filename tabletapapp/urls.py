from django.urls import path
from . import views
from django.contrib import admin


urlpatterns = [
    path("", views.index, name="index"),
    path('index/', views.index, name='index'),
    path('editmenu/', views.editmenu, name='editmenu'),
    path('login/', views.login_view, name='login'),
    path('order/', views.order, name='order'),
    path('get-order-details/<int:order_id>/', views.get_order_details, name='get_order_details'),
    path('qrcode/', views.qrcode, name='qrcode'),
    path('register/', views.register_view, name='register'),
    path('table/<int:table_number>/', views.table_view, name='table_view'),
    path('generate_menu/', views.generate_menu, name='generate_menu'),
    path("admin/", admin.site.urls),
    path("manage/", views.ManageSubscribersView.as_view(), name="manage"),
    path("manage/add/", views.SubscriberCreateView.as_view(), name="subscriber_add"),
    path("manage/edit/<int:pk>/", views.SubscriberUpdateView.as_view(), name="subscriber_edit"),
    path("manage/archive/<int:pk>/", views.SubscriberArchiveView.as_view(), name="subscriber_archive"),
    path('submit-order/', views.submit_order, name='submit_order'),
    path('logout/', views.logout_view, name='logout'),
    path('api/menus/', views.menu_list, name='menu_list'),
    path('api/menus/create/', views.create_menu, name='create_menu'),
    path('api/menu/<int:menu_id>/', views.update_menu, name='update_menu'),
    path('api/menu/<int:menu_id>/data/', views.save_menu_data, name='save_menu_data'),
]

