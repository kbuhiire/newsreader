from __future__ import unicode_literals
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError
from django.db.models import Count, Q
from django.forms import model_to_dict
from tastypie import fields
from tastypie.cache import NoCache, SimpleCache
from tastypie.exceptions import BadRequest
from tastypie.resources import ModelResource
from tastypie.throttle import CacheThrottle
from tastypie.utils import trailing_slash
from tastypie.http import HttpUnauthorized
from tastypie.paginator import Paginator
from tastypie.authorization import DjangoAuthorization, Authorization
from tastypie.authentication import MultiAuthentication, SessionAuthentication
from readbox.authentication import OAuth20Authentication, FacebookAuthentication
from django.contrib.auth import logout
from django.conf.urls import url
from readbox.models import UserEx, Feed, Article, UserReads, UserStars, UserFeeds, CategoryFeeds
from readbox.tasks import search_and_add_feed, send_activation_email, get_evernote_client
from readbox.tasks import share_evernote, share_pocket, share_readability
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from datetime import datetime, timedelta
from pytz import utc
import oauth2 as oauth
import urllib
import requests
import hashlib
import json
import urlparse


class FeedResource(ModelResource):
    class Meta:
        queryset = Feed.objects.all()
        fields = ['id', 'title', 'favicon', 'url', 'home']
        allowed_method = ['post']
        resource_name = 'feeds'
        include_resource_uri = False
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = DjangoAuthorization()
        cache = SimpleCache(timeout=180)
        throttle = CacheThrottle(throttle_at=120, timeframe=60, expiration=60)

    # Custom search endpoint
    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search/?$" % self._meta.resource_name, self.wrap_view('get_search'),
                name="api_get_search"),
        ]

    def get_search(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)

        query = request.GET.get('q', None)
        if not query:
            raise BadRequest('Please supply the search parameter (e.g. "/api/v1/feeds/search/?q=query")')

        results = SearchQuerySet().filter(content__contains=query).filter_or(keywords__contains=query).models(Feed)
        paginator = Paginator(request.GET, results, resource_uri='/api/v1/feeds/search/')

        bundles = []
        for result in paginator.page()['objects']:
            bundle = self.build_bundle(obj=result.object, request=request)
            bundles.append(self.full_dehydrate(bundle))

        object_list = {
            'meta': paginator.page()['meta'],
            'objects': bundles
        }
        object_list['meta']['search_query'] = query

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

    def get_object_list(self, request):
        raise BadRequest('You cannot use this resource')

    def post_list(self, request, **kwargs):
        try:
            body = json.loads(request.body)
            results = search_and_add_feed(body['feed'])
            if results and len(results) > 0:
                return self.create_response(request, {'success': True, 'feed_id': results[0].id,
                                                      'title': results[0].title, 'home': results[0].home,
                                                      'favicon': results[0].favicon})
            else:
                return self.create_response(request, {'success': False})
        except (ValueError, KeyError):
            raise BadRequest('Your JSON is invalid')

    def post_detail(self, request, **kwargs):
        raise BadRequest('You cannot use this resource')


class ArticleResource(ModelResource):
    class Meta:
        queryset = Article.objects.all()
        include_resource_uri = True
        resource_name = 'articles'
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = DjangoAuthorization()
        cache = SimpleCache(timeout=300)

    # Custom search endpoint
    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search/?$" % self._meta.resource_name, self.wrap_view('get_search'),
                name="api_get_search"),
            url(r"^(?P<resource_name>%s)/populars/?$" % self._meta.resource_name, self.wrap_view('get_populars'),
                name="api_get_populars")
        ]

    def get_search(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        query = request.GET.get('q', None)
        if not query:
            raise BadRequest('Please supply the search parameter (e.g. "/api/v1/articles/search/?q=query")')
        results = SearchQuerySet().models(Article).filter(
            feed_id__in=[x['id'] for x in request.user.feeds.values('id')])\
            .filter(content=query).filter_or(title=query).order_by('-date_parsed')
        if not results:
            results = EmptySearchQuerySet()

        paginator = Paginator(request.GET, results, resource_uri='/api/v1/articles/search/')

        bundles = []
        for result in paginator.page()['objects']:
            bundle = self.build_bundle(obj=result.object, request=request)
            bundles.append(self.full_dehydrate(bundle))

        object_list = {
            'meta': paginator.page()['meta'],
            'objects': bundles
        }
        object_list['meta']['search_query'] = query

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

    def get_populars(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        time_frame = datetime.utcnow() - timedelta(days=1)
        most_read = UserReads.objects.filter(marked_at__gte=time_frame)\
            .annotate(occ=Count('article')).order_by('-occ')

        if not most_read or len(most_read) < 1000:
            results = Article.objects.filter(Q(id__in=most_read.values('article')) |
                                             Q(feed_id__in=CategoryFeeds.objects.all().values('feed_id')))\
                .order_by('-date_parsed')
        else:
            results = Article.objects.filter(id__in=most_read.values('article')).order_by('-date_parsed')

        paginator = Paginator(request.GET, results, resource_uri='/api/v1/articles/populars/')

        bundles = []
        for result in paginator.page()['objects']:
            bundle = self.build_bundle(obj=result, request=request)
            bundles.append(self.full_dehydrate(bundle))

        object_list = {
            'meta': paginator.page()['meta'],
            'objects': bundles
        }

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

    def full_dehydrate(self, bundle, for_list=False):
        bundle = super(ArticleResource, self).full_dehydrate(bundle, for_list)
        bundle.data['feed_favicon'] = bundle.obj.feed.favicon
        bundle.data['feed_title'] = bundle.obj.feed.title
        return bundle

    def get_object_list(self, request):
        raise BadRequest('You cannot use this resource.')

    # We need this for feed_id
    def dehydrate(self, bundle):
        try:
            bundle.data['feed'] = bundle.obj.feed_id
        except Article.DoesNotExist:
            pass
        return bundle


# User Management
# Login, Logout and Registration
class UserResource(ModelResource):
    class Meta:
        queryset = UserEx.objects.all()
        resource_name = 'user'
        fields = ['email', 'facebook_name', 'picture', 'extras', 'read_from']
        allowed_methods = ['get']
        include_resource_uri = False
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = DjangoAuthorization()
        cache = NoCache()

    # This will reroute the requests
    def prepend_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/logout%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('logout'), name='api_logout'),
            url(r'^(?P<resource_name>%s)/register%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('register'), name='api_register'),
            url(r'^(?P<resource_name>%s)/extras%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('extras'), name='api_extras'),
            url(r'^(?P<resource_name>%s)/extras_success%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('extras_success'), name='api_extras_success'),
            url(r'^(?P<resource_name>%s)/extras_share%s$' %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('extras_share'), name='api_extras_share'),
        ]

    # TODO: Logout with OAuth2
    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        if request.user and request.user.is_authenticated():
            logout(request)
            return self.create_response(request, {'success': True})
        else:
            return self.create_response(request, {'success': False}, HttpUnauthorized)

    def register(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        try:
            req = json.loads(request.body)
            if any(x not in req for x in ['full_name', 'username', 'password', 'password_verification']):
                raise BadRequest('You have a missing parameter in your request.')
            full_name = req['full_name']
            username = req['username']
            password = req['password']
            password_verification = req['password_verification']

            #try:
            #    validate_email(username)
            #except ValidationError:
            #    return self.create_response(request, {'success': False,
            #                                          'reason': 'Please enter a valid email address.'})

            if UserEx.objects.filter(email=username).exists():
                return self.create_response(request, {'success': False,
                                                      'reason': 'The email address is already registered.'})
            if password != password_verification:
                return self.create_response(request, {'success': False,
                                                      'reason': 'The passwords do not match.'})
            else:
                new_user = UserEx.objects.create_user(username=username, email=username, password=password,
                                                      facebook_name=full_name,
                                                      picture='http://www.gravatar.com/avatar/' +
                                                              hashlib.md5(str(username).lower()).hexdigest() +
                                                              '?s=100&d=identicon&r=G')
                new_user.is_active = 0
                new_user.save()
                if isinstance(new_user, UserEx):
                    send_activation_email(new_user)
                    return self.create_response(request, {'success': True})
                else:
                    return self.create_response(request, {'success': False})
        except (ValueError, KeyError):
            raise BadRequest('Your JSON is invalid')


    def get_object_list(self, request):
        self.is_authenticated(request)
        return super(UserResource, self).get_object_list(request).filter(id=request.user.id)


# Manage User Feeds
# GET: Returns all the user's feeds as {}
# POST: Add a new feed to user calling add_feed_to_user (tasks.py) returns a success message or not
# PUT: Let a user search through our DB! Returns a list of feeds for a given tag
# DELETE: Remove a user feed, user the URI!
class UserFeedsResource(ModelResource):
    class Meta:
        queryset = UserFeeds.objects.all()
        resource_name = 'account/feeds'
        allowed_methods = ['get', 'post', 'put', 'delete']
        fields = ['folder']
        include_resource_uri = False
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = Authorization()

    def apply_filters(self, request, applicable_filters):
        object_list = super(UserFeedsResource, self).apply_filters(request, applicable_filters)
        if 'feed' in request.GET:
            object_list = object_list.filter(feed_id=request.GET['feed'])
        return object_list

    def get_object_list(self, request):
        return super(UserFeedsResource, self).get_object_list(request).select_related('feed')\
            .filter(user_id=request.user.id)

    def dehydrate(self, bundle):
        bundle.data['id'] = bundle.obj.feed.id
        bundle.data['title'] = bundle.obj.feed.title
        bundle.data['favicon'] = bundle.obj.feed.favicon
        return bundle

    def post_detail(self, request, **kwargs):
        if 'folder' in request.GET:
            folder = request.GET['folder']
        else:
            try:
                folder = json.loads(request.body)['folder']
            except ValueError:
                raise BadRequest('Your JSON is invalid')
        try:
            this_feed = Feed.objects.get(id=kwargs['pk'])
        except Feed.DoesNotExist:
            raise BadRequest('Please check the feed id you are trying to add')
        if this_feed:
            obj, created = UserFeeds.objects.get_or_create(user=request.user, feed=this_feed, defaults={'folder': folder,
                                                           'subscribed_at': datetime.utcnow().replace(tzinfo=utc)})
            if created or obj:
                res = model_to_dict(obj.feed)
                res['folder'] = folder
                return self.create_response(request, res)
        raise BadRequest('Please check the feed id you are trying to add')

    def delete_detail(self, request, **kwargs):
        try:
            UserFeeds.objects.get(user_id=request.user.id, feed_id=kwargs['pk']).delete()
            return self.create_response(request, {'success': True})
        except UserFeeds.DoesNotExist:
            raise BadRequest()

    def put_detail(self, request, **kwargs):
        try:
            req = json.loads(request.body)
            if UserFeeds.objects.filter(user_id=request.user.id, feed_id=kwargs['pk']).update(
                    folder=req['folder']) > 0:
                return self.create_response(request, {'success': True, 'id': kwargs['pk'], 'folder': req['folder']})
            else:
                raise BadRequest()
        except ValueError:
            raise BadRequest('You need to specify a folder as json parameter.')

    def put_list(self, request, **kwargs):
        raise BadRequest('You cannot use this resource')

    def delete_list(self, request, **kwargs):
        raise BadRequest('You cannot use this resource')

    def post_list(self, request, **kwargs):
        raise BadRequest('You cannot use this resource')


# Class to manage users articles
# GET: Returns all the articles in the user's feed list
class UserArticlesResource(ModelResource):
    class Meta:
        queryset = Article.objects.all()
        resource_name = 'account/articles'
        detail_allowed_methods = ['get']
        excluded = ['keywords']
        include_resource_uri = False
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = DjangoAuthorization()

        filtering = {
            'date_parsed': ('gt', 'lte',),
        }

    def get_detail(self, request, **kwargs):
        obj = Article.objects.get(id=kwargs['pk'])
        bundle = self.build_bundle(obj=obj[0], request=request)
        bundle = self.full_dehydrate(bundle)
        bundle = self.alter_detail_data_to_serialize(request, bundle)
        return self.create_response(request, bundle)

    def get_object_list(self, request):
        user_feeds = [x['id'] for x in request.user.feeds.all().values('id')]
        return super(UserArticlesResource, self).get_object_list(request)\
            .filter(feed_id__in=user_feeds).order_by('-date_parsed')

    def apply_filters(self, request, applicable_filters):
        object_list = super(UserArticlesResource, self).apply_filters(request, applicable_filters)
        if 'folder' in request.GET:
            object_list = object_list.filter(feed_id__in=request.user.feeds.filter(
                userfeeds__folder=request.GET['folder']).values('id'))
        if 'feed' in request.GET:
            object_list = object_list.filter(feed_id=request.GET['feed'])
        if 'read' in request.GET and request.GET['read'] == '1':
                return object_list
        else:
            if request.user.read_from:
                return object_list.exclude(Q(id__in=request.user.reads.filter(userreads__read=1).values('id')) |
                                           Q(date_parsed__lte=request.user.read_from,
                                             feed_id__in=request.user.feeds.filter(
                                             userfeeds__subscribed_at__lte=request.user.read_from)))
            else:
                return object_list.exclude(id__in=request.user.reads.filter(userreads__read=1).values('id'))

    def dehydrate(self, bundle):
        bundle.data['feed'] = bundle.obj.feed_id
        return bundle


# Readings and article management
# POST: Mark an article as read
# DELETE: Mark an article as unread
class UserReadingsResource(ModelResource):
    class Meta:
        queryset = UserReads.objects.all()
        resource_name = 'account/read'
        resource_uri = False
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = DjangoAuthorization()
        cache = NoCache()

        filtering = {
            'marked_at': ('gt',),
        }

    def get_object_list(self, request):
        return super(UserReadingsResource, self).get_object_list(request).filter(user_id=request.user.id)

    def apply_filters(self, request, applicable_filters):
        object_list = super(UserReadingsResource, self).apply_filters(request, applicable_filters)
        if 'article_id__in' in request.GET:
            object_list = object_list.filter(article_id__in=[int(x) for x in request.GET['article_id__in'].split(',')])
        return object_list.filter(user_id=request.user.id)

    def post_list(self, request, **kwargs):
        try:
            request.user.read_from = datetime.utcnow()
            request.user.save()
            return self.create_response(request, {'success': True})
        except DatabaseError:
            raise BadRequest('An error has occurred saving this request')
        except ValueError:
            raise BadRequest()
        except KeyError:
            raise BadRequest()

    def delete_list(self, request, **kwargs):
        try:
            request.user.read_from = None
            request.user.save()
            return self.create_response(request, {'success': True})
        except DatabaseError:
            return BadRequest()

    def patch_detail(self, request, **kwargs):
        try:
            article = Article.objects.get(id=kwargs['pk'])
            request.user.feeds.get(id=article.feed_id)
            try:
                read = json.loads(request.body)['read']
            except ValueError:
                raise BadRequest()
            except KeyError:
                raise BadRequest()
            obj, created = UserReads.objects.get_or_create(
                user_id=request.user.id, article_id=article.id,
                defaults={'read': read, 'marked_at': datetime.utcnow().replace(tzinfo=utc)})
            if not created and obj:
                if obj.read != read:
                    obj.read = read
                    obj.save()
                return self.create_response(request, {'success': True, 'id': article.id, 'read': read})
            if created:
                return self.create_response(request, {'success': True, 'id': article.id, 'read': read})
            raise BadRequest()
        except ObjectDoesNotExist:
            raise BadRequest()

    def post_detail(self, request, **kwargs):
        try:
            article = Article.objects.get(id=kwargs['pk'])
            request.user.feeds.get(id=article.feed_id)
            obj, created = UserReads.objects.get_or_create(user_id=request.user.id, article_id=article.id,
                                                           defaults={'read': 1,
                                                                     'marked_at': datetime.utcnow().replace(tzinfo=utc)})
            if not created and obj:
                if obj.read == 0:
                    obj.read = 1
                    obj.save()
                return self.create_response(request, {'success': True, 'id': article.id, 'read': 1})
            if created:
                return self.create_response(request, {'success': True, 'id': article.id, 'read': 1})
            raise BadRequest()
        except ObjectDoesNotExist:
            raise BadRequest()

    def delete_detail(self, request, **kwargs):
        try:
            article = Article.objects.get(id=kwargs['pk'])
            request.user.feeds.get(id=article.feed_id)
            obj, created = UserReads.objects.get_or_create(
                user_id=request.user.id, article_id=article.id,
                defaults={'read': 0, 'marked_at': datetime.utcnow().replace(tzinfo=utc)})
            if not created and obj:
                if obj.read == 1:
                    obj.read = 0
                    obj.save()
                return self.create_response(request, {'success': True, 'id': article.id, 'read': 0})
            if created:
                return self.create_response(request, {'success': True, 'id': article.id, 'read': 0})
        except ObjectDoesNotExist:
            raise BadRequest()

    def dehydrate(self, bundle):
        bundle.data['id'] = bundle.obj.article_id
        return bundle

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/refresh/?$" % self._meta.resource_name, self.wrap_view('get_refresh'),
                name="api_read_refresh"),
        ]

    def get_refresh(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if 'marked_at__gt' not in request.GET:
            results = UserReads.objects.filter(user_id=request.user.id).order_by('-marked_at')
        else:
            results = UserReads.objects.filter(user_id=request.user.id,
                                               marked_at__gt=request.GET['marked_at__gt']).order_by('-marked_at')

        paginator = Paginator(request.GET, results, resource_uri='/api/v1/account/read/refresh/')

        bundles = []
        for result in paginator.page()['objects']:
            bundle = self.build_bundle(obj=result, request=request)
            bundle.data['id'] = bundle.obj.article_id
            bundles.append(self.full_dehydrate(bundle))

        object_list = {
            'meta': paginator.page()['meta'],
            'objects': bundles
        }

        self.log_throttled_access(request)
        return self.create_response(request, object_list)


# Management of starred article
# GET: Get every starred article (you can specified from when)
# POST: Star an article
# DELETE: Unstar an article
class UserStarredResource(ModelResource):
    article = fields.ForeignKey(UserArticlesResource, 'article', full=False)

    class Meta:
        queryset = UserStars.objects.all()
        resource_name = 'account/star'
        allowed_methods = ['get', 'post', 'patch', 'delete']
        include_resource_uri = False
        excludes = ['id', 'star']
        authentication = MultiAuthentication(OAuth20Authentication(), SessionAuthentication(), FacebookAuthentication())
        authorization = DjangoAuthorization()
        cache = NoCache()
        filtering = {
            'marked_at': ('gt',),
        }

    def apply_filters(self, request, applicable_filters):
        object_list = super(UserStarredResource, self).apply_filters(request, applicable_filters).exclude(star=0)
        return object_list.filter(user_id=request.user.id).select_related('article')

    def patch_detail(self, request, **kwargs):
        try:
            star = json.loads(request.body)['star']
            article = Article.objects.get(id=kwargs['pk'])
            request.user.feeds.get(id=article.feed_id)
            if star == 1:
                obj, created = UserStars.objects.get_or_create(
                    user_id=request.user.id, article_id=article.id,
                    defaults={'star': 1, 'marked_at': datetime.utcnow().replace(tzinfo=utc)})
                if not created and obj and obj.star == 0:
                    obj.star = 1
                    obj.save()
                    return self.create_response(request, {'success': True, 'id': article.id, 'star': 1})
                if created:
                    return self.create_response(request, {'success': True, 'id': article.id, 'star': 1})
            elif star == 0:
                if UserStars.objects.filter(user_id=request.user.id, article_id=article.id, star=1)\
                        .update(star=0, marked_at=datetime.utcnow().replace(tzinfo=utc)) > 0:
                    return self.create_response(request, {'success': True, 'id': article.id, 'star': 0})
            raise BadRequest()
        except (ValueError, KeyError, ObjectDoesNotExist):
            raise BadRequest()

    def post_detail(self, request, **kwargs):
        try:
            article = Article.objects.get(id=kwargs['pk'])
            request.user.feeds.get(id=article.feed_id)
            obj, created = UserStars.objects.get_or_create(user_id=request.user.id, article_id=article.id,
                                                           defaults={'star': 1,
                                                                     'marked_at': datetime.utcnow().replace(tzinfo=utc)})
            if not created and obj and obj.star == 0:
                obj.star = 1
                obj.save()
                return self.create_response(request, {'success': True, 'id': article.id, 'star': 1})
            if created:
                return self.create_response(request, {'success': True, 'id': article.id, 'star': 1})
            raise BadRequest()
        except ObjectDoesNotExist:
            raise BadRequest()

    def delete_detail(self, request, **kwargs):
        try:
            article = Article.objects.get(id=kwargs['pk'])
            request.user.feeds.get(id=article.feed_id)
            if UserStars.objects.filter(user_id=request.user.id, article_id=article.id, star=1)\
                    .update(star=0, marked_at=datetime.utcnow().replace(tzinfo=utc)) > 0:
                return self.create_response(request, {'success': True, 'id': article.id, 'star': 0})
            else:
                BadRequest()
        except ObjectDoesNotExist:
            BadRequest()

    def post_list(self, request, **kwargs):
        raise BadRequest('You cannot use this resource')

    def delete_list(self, request, **kwargs):
        raise BadRequest('You cannot use this resource.')

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/ids/?$" % self._meta.resource_name, self.wrap_view('get_ids'),
                name="api_star_ids"),
            url(r"^(?P<resource_name>%s)/refresh/?$" % self._meta.resource_name, self.wrap_view('get_refresh'),
                name="api_star_refresh"),
        ]

    def get_ids(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        object_list = UserStars.objects.filter(user_id=request.user.id).exclude(star=0).values('article_id')
        return self.create_response(request, {'objects': list(object_list)})

    def get_refresh(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if 'marked_at__gt' not in request.GET:
            results = UserStars.objects.filter(user_id=request.user.id).order_by('-marked_at').exclude(star=1)
        else:
            results = UserStars.objects.filter(user_id=request.user.id,
                                               marked_at__gt=request.GET['marked_at__gt'])\
                .order_by('-marked_at').exclude(star=1)

        paginator = Paginator(request.GET, results, resource_uri='/api/v1/account/star/refresh/')

        bundles = []
        for result in paginator.page()['objects']:
            bundle = self.build_bundle(obj=result, request=request)
            bundle.data['refresh'] = True
            bundle.data['id'] = bundle.obj.article_id
            bundles.append(self.full_dehydrate(bundle))

        object_list = {
            'meta': paginator.page()['meta'],
            'objects': bundles
        }

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

    def dehydrate(self, bundle):
        if not 'refresh' in bundle.data:
            marked = bundle.data['marked_at']
            self.article.full = True
            bundle = self.article.dehydrate(bundle)
            bundle.data['marked_at'] = marked
        else:
            del bundle.data['refresh']
        return bundle


class FeedStatistics(ModelResource):
    class Meta:
        queryset = Feed.objects.all()
        excludes = ['delta_fetch', 'summarize', 'disabled', 'featured']
        allowed_method = ['get']
        resource_name = 'stats'
        include_resource_uri = False
        cache = SimpleCache(timeout=30)

    def get_detail(self, request, **kwargs):
        if 'users_only' in request.GET:
            return self.create_response(request, UserFeeds.objects.filter(feed_id=kwargs['pk']).count())
        obj = Feed.objects.get(id=kwargs['pk'])
        bundle = self.build_bundle(obj=obj, request=request)
        bundle.data['users'] = UserFeeds.objects.filter(feed_id=kwargs['pk']).count()
        bundle.data['keywords'] = [x.name for x in obj.keywords.all()]
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)