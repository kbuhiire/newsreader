'use strict';

angular.module('readerApp')
    .controller('SearchCtrl', function ($scope, Articles, $routeParams, User) {
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
        $scope.articles = new Articles('/api/v1/articles/search/', {
            q: $routeParams.q
        }, null, $scope.loader);
    });