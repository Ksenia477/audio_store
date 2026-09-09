from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from .models import Category, Product


class ProductListView(ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Product.objects.active()
            .filter(category__is_active=True)
            .select_related('category')
            .prefetch_related('images', 'specifications')
        )

        self.selected_category = None
        category_slug = self.kwargs.get('slug')
        if category_slug:
            self.selected_category = get_object_or_404(
                Category.objects.active(),
                slug=category_slug,
            )
            queryset = queryset.filter(category=self.selected_category)

        self.search_query = self.request.GET.get('q', '').strip()
        if self.search_query:
            queryset = queryset.filter(
                Q(name__icontains=self.search_query)
                | Q(short_description__icontains=self.search_query)
                | Q(description__icontains=self.search_query)
                | Q(specifications__name__icontains=self.search_query)
                | Q(specifications__value__icontains=self.search_query)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.active().annotate(
            product_count=Count('products', filter=Q(products__is_active=True)),
        )
        context['selected_category'] = self.selected_category
        context['search_query'] = self.search_query
        context['show_showcase'] = (
            not self.selected_category
            and not self.search_query
            and context['page_obj'].number == 1
        )
        if context['show_showcase']:
            featured = []
            for category in context['categories']:
                product = (
                    category.products.active()
                    .filter(stock__gt=0, images__isnull=False)
                    .select_related('category')
                    .prefetch_related('images')
                    .order_by('-is_featured', 'name')
                    .first()
                )
                if product:
                    featured.append(product)
                if len(featured) == 2:
                    break
            context['featured_products'] = featured
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return (
            Product.objects.active()
            .filter(category__is_active=True)
            .select_related('category')
            .prefetch_related('images', 'specifications')
        )
