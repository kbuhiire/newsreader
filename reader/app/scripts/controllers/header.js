'use strict';

angular.module('readerApp')
    .controller('HeaderCtrl', function ($scope, $location, Subscription, $window, User, ngProgressLite, $http, Alerts) {
        $scope.searchQuery = undefined;

        $scope.searchArticles = function () {
            $location.search('q', $scope.searchQuery).path('/search').replace();
            $scope.searchQuery = undefined;
        };
    });