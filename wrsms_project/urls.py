from django.http import FileResponse
from django.conf import settings
import os
from django.contrib import admin
from django.urls import path, include
from wrsm_app.api import router
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView  
from wrsm_app import views
from wrsm_app import views_offline


urlpatterns = [
        path('admin/', admin.site.urls),
        # path('', include('pwa.urls')), # Disabled to use custom PWA implementation
        path('serviceworker.js', views_offline.pwa_serviceworker, name='serviceworker'),
        path('manifest.json', views_offline.pwa_manifest, name='manifest'),
        path('account/', include('account.urls')),
        path('', include('wrsm_app.urls')),
        path('api/', include(router.urls)),
    
        path("offline/", TemplateView.as_view(
            template_name="offline.html"), name="offline"),
        path('', views.index, name='index'),
        path('pricing/', views.pricing, name='pricing'),
        path('about/', views.about, name='about'),
        path('contact-us/', views.contact_us, name='contact-us'),
    
    ]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
