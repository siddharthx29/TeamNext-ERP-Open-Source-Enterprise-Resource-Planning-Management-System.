from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "login",
            "signup",
            "forgot_password",
            "dashboard",
            "projects_page",
            "analytics_page",
            "finance_page",
            "hr_page",
            "inventory_page",
            "reports_page",
            "help_centre_page"
        ]

    def location(self, item):
        return reverse(item)