from django.conf.urls import patterns, include, url
from tastypie.api import Api
from readbox.api import UserResource, UserArticlesResource, UserFeedsResource
from readbox.api import UserReadingsResource, FeedStatistics
from readbox.api import UserStarredResource, FeedResource, ArticleResource
from readbox.views import index_view, login_view, logout_view, registration_view, activation_view
from readbox.views import connect_pocket, connect_evernote, connect_readability
from readbox.views import callback_evernote, callback_pocket, callback_readability
from django.contrib import admin

admin.autodiscover()

api = Api(api_name='v1')
api.register(ArticleResource())
api.register(FeedResource())
api.register(UserFeedsResource())
api.register(UserResource())
api.register(UserArticlesResource())
api.register(UserReadingsResource())
api.register(UserStarredResource())
api.register(FeedStatistics())

urlpatterns = patterns('',
                       url(r'^api/', include(api.urls)),
                       url(r'^oauth/', include('provider.oauth2.urls', namespace='oauth2')),
                       url(r'^$', index_view, name='index'),
                       url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^login/', login_view, name='login'),
                       url(r'^logout/', logout_view, name='logout'),
                       url(r'^confirm/', activation_view),
                       url(r'^registration/', registration_view, name='registration'),
                       url(r'^facebook/', include('django_facebook.urls')),
                       url(r'^accounts/', include('django_facebook.auth_urls')),
                       url(r'^accounts/pocket/', connect_pocket, name='connect_pocket'),
                       url(r'^accounts/evernote/', connect_evernote, name='connect_evernote'),
                       url(r'^accounts/readability/', connect_readability, name='connect_readability'),
                       url(r'^accounts/callbacks/pocket/', callback_pocket, name='callback_pocket'),
                       url(r'^accounts/callbacks/evernote/', callback_evernote, name='callback_evernote'),
                       url(r'^accounts/callbacks/readability/', callback_readability, name='callback_readability'),
                       )
