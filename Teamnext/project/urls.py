from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from myapp.sitemaps import StaticViewSitemap
from myapp.views import ads_txt

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    path('ads.txt', ads_txt, name='ads_txt'),
    path('', include('myapp.urls')),
]