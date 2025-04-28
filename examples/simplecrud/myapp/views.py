from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import ItemForm
from .models import Item


def item_list(request):
    items = Item.objects.all()
    return render(request, "myapp/item_list.html", {"items": items})


def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("item_list")
    else:
        form = ItemForm()
    return render(request, "myapp/item_form.html", {"form": form, "action": "Create"})


def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("item_list")
    else:
        form = ItemForm(instance=item)
    return render(request, "myapp/item_form.html", {"form": form, "action": "Update"})


def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        item.delete()
        return redirect("item_list")
    return render(request, "myapp/item_confirm_delete.html", {"item": item})
