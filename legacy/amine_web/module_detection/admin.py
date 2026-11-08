from django.contrib import admin

from .models import Querydata, Modules_result, Gene

admin.site.register(Querydata)
admin.site.register(Modules_result)
admin.site.register(Gene)
