from django.contrib import admin
from readbox.models import UserEx, Article, Feed, Category, CategoryFeeds


class ArticleAdmin(admin.ModelAdmin):
    search_fields = ('title', 'feed')
    list_display = ('title', 'feed', 'date_parsed')
    list_filter = ('date_parsed', 'feed')
    ordering = ('-date_parsed',)


class UserExAdmin(admin.ModelAdmin):
    search_fields = ('username', 'email', 'facebook_name')
    list_display = ('username', 'email', 'facebook_name', 'date_joined')
    list_filter = ('date_joined',)


class CategoryFeedInline(admin.TabularInline):
    model = CategoryFeeds
    extra = 1


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category',)
    inlines = (CategoryFeedInline,)


class FeedAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    list_display = ('title', 'home')
    inlines = (CategoryFeedInline,)


admin.site.register(UserEx, UserExAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Article, ArticleAdmin)