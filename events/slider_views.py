"""
Slider management views — admin-only CRUD for SliderItem.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import SliderItem, Event
from .slider_forms import SliderItemForm


@login_required
def slider_list(request):
    """Admin: list all slider items with drag-to-reorder."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    items = SliderItem.objects.all().select_related('linked_event')
    return render(request, 'slider/slider_list.html', {'items': items})


@login_required
def slider_create(request):
    """Admin: create a new slider item."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = SliderItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            messages.success(request, f'✅ Slide "{item.title}" added to the homepage slider.')
            return redirect('slider_list')
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    label = field.replace('_', ' ').title() if field != '__all__' else 'Error'
                    messages.error(request, f'{label}: {e}')
    else:
        form = SliderItemForm()

    return render(request, 'slider/slider_form.html', {
        'form': form,
        'title': 'Add New Slide',
    })


@login_required
def slider_edit(request, pk):
    """Admin: edit an existing slider item."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    item = get_object_or_404(SliderItem, pk=pk)

    if request.method == 'POST':
        form = SliderItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Slide "{item.title}" updated.')
            return redirect('slider_list')
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    label = field.replace('_', ' ').title() if field != '__all__' else 'Error'
                    messages.error(request, f'{label}: {e}')
    else:
        form = SliderItemForm(instance=item)

    return render(request, 'slider/slider_form.html', {
        'form': form,
        'item': item,
        'title': f'Edit Slide: {item.title}',
    })


@login_required
def slider_delete(request, pk):
    """Admin: delete a slider item."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    item = get_object_or_404(SliderItem, pk=pk)
    title = item.title
    item.delete()
    messages.success(request, f'Slide "{title}" deleted.')
    return redirect('slider_list')


@login_required
def slider_toggle(request, pk):
    """Admin: AJAX toggle active status."""
    if not request.user.is_admin_user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    item = get_object_or_404(SliderItem, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active'])
    return JsonResponse({'is_active': item.is_active})


@login_required
def slider_reorder(request):
    """Admin: AJAX save new order after drag-and-drop."""
    if not request.user.is_admin_user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    import json
    data = json.loads(request.body)
    order_list = data.get('order', [])   # list of PKs in new order

    for i, pk in enumerate(order_list):
        SliderItem.objects.filter(pk=pk).update(order=i)

    return JsonResponse({'success': True})


def public_slider_data(request):
    """Public JSON endpoint — returns active slider items for AJAX refresh."""
    items = SliderItem.objects.filter(is_active=True).values(
        'pk', 'title', 'subtitle', 'slide_type', 'text_color', 'cta_text',
        'order',
    )
    result = []
    for item in items:
        obj = SliderItem.objects.get(pk=item['pk'])
        result.append({
            **item,
            'image_url': obj.image.url if obj.image else '',
            'cta_url':   obj.final_cta_url,
            'type_label': obj.get_slide_type_display(),
        })
    return JsonResponse({'slides': result})
