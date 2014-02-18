'use strict';

angular.module('readerApp')
    .controller('ItemsCtrl', function ($scope, Articles, User, $timeout) {
        $scope.loader = {spin: false};
        $scope.articles = new Articles(null, null, null, $scope.loader);
        User.feeds.then(function (feeds) {
            $scope.feeds = feeds;
        });
        User.info.then(function (info) {
            $scope.userInfo = info;
        });
        User.starred.then(function (starred) {
            $scope.starred = starred;
        });

        $scope.$watch(function () {
            if ($scope.articles !== undefined) {
                return $scope.articles.full_count;
            }
        }, function (newValue) {
            User.vars.items = User.vars.items.then(function (data) {
                data = newValue;
                return data;
            });
        });
    });