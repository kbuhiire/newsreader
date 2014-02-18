'use strict';

angular.module('readerApp')
    .controller('FeedCtrl', function ($scope, User, Articles, $routeParams, ngProgressLite, Alerts, $http, $location) {
        $scope.loader = {spin: false};
        User.feeds.then(function (feeds) {
            $scope.feeds = feeds;
        });
        User.info.then(function (info) {
            $scope.userInfo = info;
        });
        User.starred.then(function (starred) {
            $scope.starred = starred;
        });
        $scope.thisFeed = $routeParams.feedId
        $scope.articles = new Articles('/api/v1/account/articles/?feed=' + $routeParams.feedId, null, null, $scope.loader);

        $scope.removeFeed = function (feed_id) {
            ngProgressLite.start();
            $http.delete('/api/v1/account/feeds/' + feed_id + '/').success(function () {
                User.feeds.then(function (data) {
                    for (var x in data.folders) {
                        for (var i = data.folders[x].length - 1; i >= 0; i--) {
                            if (data.folders[x][i].id === parseInt(feed_id)) {
                                data.folders[x].splice(i, 1);
                            }
                        }
                    }
                    for (var i = data.root.length - 1; i >= 0; i--) {
                        if (data.root[i].id === parseInt(feed_id)) {
                            data.root.splice(i, 1);
                        }
                    }
                    delete data.ind[feed_id];
                    data.ids.splice(data.ids.indexOf(parseInt(feed_id)), 1);
                    return data;
                });
                $location.path('/');
                ngProgressLite.done();
            }).error(function () {
                Alerts.addAlert('error', 'There was an error deleting this feed.')
                ngProgressLite.done();
            });
        };

        $scope.moveFeed = function (feed_id) {
            User.vars.toMove = feed_id;
        };
    });