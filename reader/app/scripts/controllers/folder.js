'use strict';

angular.module('readerApp')
    .controller('FolderCtrl', function ($scope, User, Articles, $routeParams) {
        User.feeds.then(function (feeds) {
            $scope.feeds = feeds;
        });
        User.info.then(function (info) {
            $scope.userInfo = info;
        });
        User.starred.then(function (starred) {
            $scope.starred = starred;
        });
        $scope.articles = new Articles('/api/v1/account/articles/?folder=' + $routeParams.folderName);
    });