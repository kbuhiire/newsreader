'use strict';

angular.module('readerApp')
    .controller('ChangefolderCtrl', function ($scope, $http, ngProgressLite, User) {
        $scope.newFolder = undefined;
        $scope.folderChoice = undefined;
        $scope.lock = false;

        $scope.folders = User.feeds.then(function (data) {
            var folders = [];
            for (var key in data.folders) {
                folders.push(key);
            }
            return folders;
        });

        $scope.save = function () {
            if ($scope.lock) {
                return;
            }
            $scope.lock = true;
            User.feeds.then(function (data) {
                if ($scope.folderChoice === undefined && $scope.newFolder === undefined) {
                    return;
                }
                var feedFound;
                for (var x in data.folders) {
                    for (var i = data.folders[x].length - 1; i >= 0; i--) {
                        if (data.folders[x][i].id === parseInt(User.vars.toMove)) {
                            feedFound = data.folders[x][i];
                            data.folders[x].splice(i, 1);
                        }
                    }
                }
                for (var i = data.root.length - 1; i >= 0; i--) {
                    if (data.root[i].id === parseInt(User.vars.toMove)) {
                        feedFound = data.root[i];
                        data.root.splice(i, 1);
                    }
                }
                if ($scope.newFolder !== undefined && $scope.newFolder !== '') {
                    if (data.folders[$scope.newFolder] === undefined || !data.folders[$scope.newFolder]) {
                        data.folders[$scope.newFolder] = [];
                    } else {
                        feedFound.folder = $scope.newFolder;
                    }
                    feedFound.folder = $scope.newFolder;
                    data.folders[$scope.newFolder].push(feedFound);
                }
                if ($scope.folderChoice !== undefined && $scope.folderChoice !== '') {
                    if ($scope.folderChoice === 'Main Folder') {
                        feedFound.folder = '~~Root';
                        data.root.push(feedFound);
                    } else {
                        feedFound.folder = $scope.folderChoice;
                        data.folders[$scope.folderChoice].push(feedFound);
                    }
                }
                $http.put('/api/v1/account/feeds/' + feedFound.id + '/', {
                    folder: feedFound.folder
                });
                $scope.folders = User.feeds.then(function (data) {
                    var folders = [];
                    for (var key in data.folders) {
                        folders.push(key);
                    }
                    return folders;
                });
                $scope.lock = false;
                $('#moveModal').modal('hide');
                $scope.newFolder = undefined;
                $scope.folderChoice = undefined;
            });
        };
    });