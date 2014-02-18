'use strict';

angular.module('readerApp')
    .controller('StarredCtrl', function ($scope, User, Articles) {
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
        $scope.articles = new Articles('/api/v1/account/star/', null, null, $scope.loader);
    });