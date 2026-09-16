from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from apps.core.utils import paginate
from .models import Notification


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user)
    counts = notifications.aggregate(
        total=Count('id'),
        unread=Count('id', filter=Q(is_read=False))
    )
    page_obj = paginate(request, notifications, 10)

    return render(request, 'notifications/notifications_list.html', {
        'page_obj': page_obj,
        'notifications': page_obj,
        'total_count': counts['total'],
        'unread_count': counts['unread'],
    })


@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')


@login_required
def mark_all_as_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:list')
