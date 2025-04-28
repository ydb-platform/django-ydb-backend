from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import BookStoreForm
from .models import BookStore

ALLOWED_SORT_FIELDS = {
    "title": "Title",
    "author": "Author",
    "price": "Price",
    "quantity": "Quantity",
    "release_dt": "Release Date",
    "record_dttm": "Added Date",
    "limited_edition": "Limited edition"
}


def item_list(request):
    search_query = request.GET.get("q", "").strip()
    sort_field = request.GET.get("sort", "title")
    sort_direction = request.GET.get("dir", "asc")
    page_number = request.GET.get("page", 1)

    if sort_field not in ALLOWED_SORT_FIELDS:
        sort_field = "title"

    if sort_direction == "desc":
        sort_field = f"-{sort_field}"

    books = BookStore.objects.all()

    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query)
        )

    books = books.order_by(sort_field)

    paginator = Paginator(books, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, "myapp/record_list.html", {
        "items": page_obj,
        "search_query": search_query,
        "sort_field": sort_field.lstrip("-"),
        "sort_direction": sort_direction,
        "allowed_sort_fields": ALLOWED_SORT_FIELDS,
        "current_sort_name": ALLOWED_SORT_FIELDS.get(sort_field.lstrip("-"), "Title")
    })


def item_create(request):
    if request.method == "POST":
        form = BookStoreForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("item_list")
    else:
        form = BookStoreForm()
    return render(request, "myapp/record_form.html", {"form": form, "action": "Create"})


def item_update(request, pk):
    item = get_object_or_404(BookStore, pk=pk)
    if request.method == "POST":
        form = BookStoreForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("item_list")
    else:
        form = BookStoreForm(instance=item)
    return render(request, "myapp/record_form.html", {"form": form, "action": "Update"})


def item_delete(request, pk):
    item = get_object_or_404(BookStore, pk=pk)
    if request.method == "POST":
        item.delete()
        return redirect("item_list")
    return render(request, "myapp/record_confirm_delete.html", {"item": item})
