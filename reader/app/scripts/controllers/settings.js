'use strict';

angular.module('readerApp')
    .controller('SettingsCtrl', function ($scope, User, $http, $window, ngProgressLite, Alerts) {
        User.info.then(function (info) {
            $scope.userInfo = info;
        });

        $scope.changePassword = function () {
            return;
        };

        $scope.connectPocket = function () {
            $window.location = '/accounts/pocket/';
        };

        $scope.connectEvernote = function () {
            $window.location = '/accounts/evernote/';
        };

        $scope.connectReadability = function () {
            $window.location = '/accounts/readability/';
        };

        $scope.logout = function (extra) {
            $http.post('/api/v1/user/extras/', {extra: extra, logout: true})
            .success(function () {
                User.info.then(function (data) {
                    delete data.enabled[extra];
                    return data;
                });
            });
        };

        $scope.undoAllread = function () {
            ngProgressLite.start();
            $http.delete('/api/v1/account/read/').success(function () {
                User.info.then(function (data) {
                    data.read_from = null;
                    return data;
                });
                Alerts.addAlert('info', 'Mark all as read succefully reverted.');
                ngProgressLite.done();
            }).error(function () {
                Alerts.addAlert('error', 'Whoops. There was an error.');
                ngProgressLite.done();
            });
        };

        $scope.showReadItems = function () {
            ngProgressLite.start();
            $http.post('/api/v1/user/extras/', {extra: 'show_read'}).success(function () {
                ngProgressLite.done();
            }).error(function () {
                ngProgressLite.done();
                Alerts.addAlert('error', 'Whoops. There was an error.');
            });
        };
    });