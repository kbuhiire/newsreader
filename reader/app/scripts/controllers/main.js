'use strict';

angular.module('readerApp')
    .controller('MainCtrl', function ($scope, User, Articles, $http) {
        $scope.loader = {spin: false};
        User.feeds.then(function (feeds) {
            $scope.feeds = feeds;
        });
        $scope.articles = new Articles('/api/v1/articles/populars/', null, null, $scope.loader);

        $scope.addFeed = function (feed_id) {
            $http.post('/api/v1/account/feeds/' + feed_id + '/', {}, {
                params: {
                    folder: '~~Root'
                }
            }).success(function () {
                User.feeds.then(function (res) {
                    $http.get('/api/v1/account/feeds/', {
                        params: {
                            feed: feed_id
                        }
                    }).success(function (info) {
                        if (info.objects.length > 0) {
                            var addThis = info.objects[0];
                            res.ids.splice(0, 0, addThis.id);
                            res.title[addThis.id] = addThis.title;
                            res.favicon[addThis.id] = addThis.favicon;
                            if (addThis.folder === '~~Root') {
                                res.root.push(addThis);
                            } else if (res.folders[addThis.folder] === undefined || !res.folders[addThis.folder]) {
                                res.folders[addThis.folder] = [];
                                res.folders[addThis.folder].push(addThis);
                            } else {
                                res.folders[addThis.folder].push(addThis);
                            }
                            return res;
                        }
                    });
                });
            }).error(function () {});
        }
    });