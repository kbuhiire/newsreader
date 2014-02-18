from __future__ import unicode_literals
from haystack import indexes
from celery_haystack.indexes import CelerySearchIndex
from readbox.models import Article, Feed


class ArticleIndex(CelerySearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, model_attr='content')
    title = indexes.CharField(model_attr='title', indexed=True)
    feed_id = indexes.IntegerField(model_attr='feed_id', indexed=False)
    feed_title = indexes.CharField(model_attr='feed__title', indexed=False)
    feed_favicon = indexes.CharField(model_attr='feed__favicon', indexed=False, null=True)
    article_id = indexes.IntegerField(model_attr='id', indexed=False)
    date_parsed = indexes.DateTimeField(model_attr='date_parsed', indexed=True)

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.select_related('feed').all().order_by('-date_parsed')


class FeedIndex(CelerySearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, model_attr='title')
    feed_id = indexes.IntegerField(model_attr='id', indexed=False)
    home_url = indexes.CharField(model_attr='home', indexed=True)
    keywords = indexes.CharField(model_attr='keywords', indexed=True)

    def prepare(self, obj):
        self.prepared_data = super(FeedIndex, self).prepare(obj)
        self.prepared_data['keywords'] = ' '.join([x.name for x in obj.keywords.all()])
        return self.prepared_data

    def get_model(self):
        return Feed

    def index_queryset(self, using=None):
        return self.get_model().objects.select_related('keywords__name').all()

