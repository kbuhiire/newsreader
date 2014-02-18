from django.db import models
from django.contrib.auth.models import UserManager, PermissionsMixin, AbstractBaseUser
from django.db.models.signals import post_save, post_delete
from django_facebook.signals import facebook_user_registered
from django_facebook.models import BaseFacebookProfileModel
from pytz import utc
from datetime import datetime
from taggit.managers import TaggableManager
import jsonfield
import hashlib


class UserEx(AbstractBaseUser, PermissionsMixin, BaseFacebookProfileModel):
    username = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField()
    is_staff = models.BooleanField()
    date_joined = models.DateTimeField()
    email = models.EmailField(unique=True)
    picture = models.TextField(null=True)
    feeds = models.ManyToManyField('Feed', through='UserFeeds', related_name='feeds')
    reads = models.ManyToManyField('Article', through='UserReads', related_name='reads')
    stars = models.ManyToManyField('Article', through='UserStars', related_name='stars')
    read_from = models.DateTimeField(null=True)
    extras = jsonfield.JSONField(default={}, blank=True, null=True)

    USERNAME_FIELD = 'username'

    objects = UserManager()

    def get_short_name(self):
        return self.facebook_name


class Article(models.Model):
    feed = models.ForeignKey('Feed', db_index=True)
    author = models.CharField(max_length=150, null=True)
    url = models.URLField(max_length=255)
    media = models.TextField(null=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    content_ex = models.TextField(null=True)
    excerpt = models.TextField(null=True)
    word_count = models.IntegerField(default=0)
    date_parsed = models.DateTimeField(db_index=True)
    language = models.CharField(max_length=100, default=None, null=True)
    summary = models.TextField(default=None, null=True)
    keywords = TaggableManager()

    def __unicode__(self):
        return self.title

    class Meta:
        unique_together = (('feed', 'url'), ('feed', 'title'))


class Feed(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    url = models.URLField(max_length=255, unique=True)
    home = models.TextField()
    favicon = models.URLField(null=True)
    disabled = models.BooleanField(default=0)
    language = models.CharField(max_length=100, default=None, null=True)
    keywords = TaggableManager()
    featured = models.BooleanField(default=False)
    summarize = models.BooleanField(default=False)
    summarize_excerpt = models.BooleanField(default=False)
    top = models.BooleanField(default=False)

    def __unicode__(self):
        return self.title


class Category(models.Model):
    category = models.CharField(max_length=200, unique=True)
    feeds = models.ManyToManyField('Feed', related_name='categories', through='CategoryFeeds')
    points = models.FloatField(default=0)

    def __unicode__(self):
        return self.category


class CategoryFeeds(models.Model):
    feed = models.ForeignKey('Feed')
    category = models.ForeignKey('Category')


class UserFeeds(models.Model):
    user = models.ForeignKey('UserEx')
    feed = models.ForeignKey('Feed')
    folder = models.CharField(max_length=30)
    subscribed_at = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ('user', 'feed')


class UserReads(models.Model):
    user = models.ForeignKey('UserEx')
    article = models.ForeignKey('Article')
    read = models.BooleanField()
    marked_at = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-marked_at']


class UserStars(models.Model):
    user = models.ForeignKey('UserEx')
    article = models.ForeignKey('Article')
    star = models.IntegerField(default=0)
    marked_at = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-marked_at']


# Signals
def fb_user_registered_handler(sender, user, facebook_data, **kwargs):
    if user and facebook_data:
        user.picture = 'http://www.gravatar.com/avatar/' + hashlib.md5(user.email.lower()).hexdigest() \
                       + '?s=100&d=identicon&r=G'
        user.save()
facebook_user_registered.connect(fb_user_registered_handler, sender=UserEx)


#def first_feed(sender, **kw):
#    user = kw["instance"]
#    if kw["created"]:
#        up = UserFeeds(user=user, feed_id=1, folder='~~Root', subscribed_at=datetime.utcnow().replace(tzinfo=utc))
#        up.save()
#post_save.connect(first_feed, sender=UserEx)


def first_feed(sender, **kw):
    user = kw["instance"]
    if kw["created"]:
        if user.raw_data and 'it_IT' in user.raw_data:
            up = UserFeeds(user=user, feed_id=82, folder='~~Root', subscribed_at=datetime.utcnow().replace(tzinfo=utc))
            up.save()
post_save.connect(first_feed, sender=UserEx)


def post_delete_userfeed(sender, **kw):
    user_feed = kw['instance']
    UserReads.objects.select_related('article').filter(article__feed_id=user_feed.feed_id,
                                                       user_id=user_feed.user_id).delete()
    UserStars.objects.select_related('article').filter(article__feed_id=user_feed.feed_id,
                                                       user_id=user_feed.user_id).delete()
post_delete.connect(post_delete_userfeed, sender=UserFeeds)