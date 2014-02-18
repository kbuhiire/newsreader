'use strict';

angular.module('readerApp')
    .controller('SidebarCtrl', function ($scope, User, ngProgressLite) {
        $scope.vars = {};
        $scope.userInfo = {};

        User.info.then(function (data) {
            $scope.userInfo = data;
        });

        User.vars.items.then(function (items) {
            if (items > 1000) {
                items = "+1k";
            }
            $scope.vars.items = items;
        });

        User.vars.stars.then(function (stars) {
            $scope.vars.stars = stars;
        });

        User.feeds.then(function (feeds) {
            $scope.feeds = feeds;
        });
    });