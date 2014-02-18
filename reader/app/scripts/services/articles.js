'use strict';

angular.module('readerApp')
    .factory('Articles', function ($http, User, $window, ngProgressLite, Alerts) {
        var Articles = function (after, params, byDate, loader) {
            this.items = [];
            this.ids = {};
            this.busy = false;
            this.after = after || '/api/v1/account/articles/';
            this.byDate = byDate === true;
            this.date = undefined;
            this.params = undefined || params;
            this.loader = loader;
            this.full_count = undefined;
        };

        Articles.prototype.nextPage = function () {
            if (this.busy) {
                this.loader.spin = false;
                return;
            }
            this.busy = true;
            this.loader.spin = true;
            $http.get(this.after, {
                params: this.params
            }).success(function (data) {
                    var obj = data.objects;
                    if (obj === undefined) {
                        return;
                    }
                    if (obj.length === 0) {
                        this.loader.end = true;
                        this.loader.spin = false;
                        return;
                    }
                    if (this.full_count === undefined) {
                        this.full_count = data.meta.total_count;
                    }
                    for (var i = 0; i < obj.length; i++) {
                        if (this.ids[obj[i].id] === undefined) {
                            obj[i].date_parsed = obj[i].date_parsed + 'Z';
                            this.items.push(obj[i]);
                            this.ids[obj[i].id] = true;
                        }
                    }
                    this.after = data.meta.next;
                    this.loader.spin = false;
                    this.busy = false;
                }.bind(this)).error(function () {
                    this.loader.spin = false;
                });
        };

        Articles.prototype.star = function (article_id) {
            $http.post('/api/v1/account/star/' + article_id + '/', {})
                .then(function (data) {
                    if (data.data.success) {
                        User.vars.stars = User.vars.stars.then(function (data) {
                            return data + 1;
                        });
                    }
                    User.starred.then(function (starred) {
                        starred[article_id] = true;
                        return starred;
                    });
                });
        };

        Articles.prototype.unstar = function (article_id) {
            $http.delete('/api/v1/account/star/' + article_id + '/', {})
                .success(function () {
                    User.starred.then(function (data) {
                        delete data[article_id];
                        return data;
                    });
                    User.vars.stars = User.vars.stars.then(function (data) {
                        return data - 1;
                    });
                });
        };

        Articles.prototype.share = function (extra, article_id) {
            ngProgressLite.start();
            $http.post('/api/v1/user/extras_share/', {
                'extra': extra,
                'article': article_id
            }).success(function () {
                ngProgressLite.done();
            }).error(function () {
                ngProgressLite.done();
                Alerts.addAlert('error', 'There was an error saving to your ' + extra + ' account.')
            });
        };

        Articles.prototype.shareFacebook = function (article_url) {
            $window.open('https://www.facebook.com/sharer/sharer.php?u=' + article_url,
                'facebook-share-dialog', 'width=626,height=436');
        };

        Articles.prototype.shareTwitter = function (article_url) {
            $window.open('https://twitter.com/share?url=' + article_url + '&via=readboxapp&text=Just read ',
                'twitter-share-dialog', 'width=626,height=436');
        };

        Articles.prototype.shareGoogle = function (article_url) {
            $window.open('https://plus.google.com/share?url=' + article_url, 'google-share-dialog',
                'width=626,height=436');
        };

        Articles.prototype.read = function (article_id) {};

        Articles.prototype.unread = function (article_id) {};

        return Articles;
    });