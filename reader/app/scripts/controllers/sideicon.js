'use strict';

angular.module('readerApp')
    .controller('SideiconCtrl', function ($scope, Subscription, User, ngProgressLite, Alerts, $http) {
        $scope.vars = {};
        $scope.toggleCollapse = function () {
            Subscription.show = !Subscription.show;
        };

        $scope.allread = function () {
            ngProgressLite.start();
            $http.get('/api/v1/account/articles/').success(
                function (articles) {
                    if (articles.objects.length === 0) {
                        Alerts.addAlert('error', 'You have already marked all your items as read.');
                        ngProgressLite.done();
                        return;
                    }
                    $http.post('/api/v1/account/read/', {
                        read_from: articles.objects[0].date_parsed + 'Z'
                    }).success(function () {
                        User.info.then(function (data) {
                            data.read_from = true;
                            return data;
                        });
                        Alerts.addAlert('info', 'All your articles are now marked as read.');
                        ngProgressLite.done();
                    }).error(function () {
                        Alerts.addAlert('error', 'Whoops. There was an error.');
                    });
                })
        };

        // User.vars.items.then(function (items) {
        //     if (items > 1000) {
        //         items = "+1k";
        //     }
        //     $scope.vars.items = items;
        // });

        $scope.$watch(function () {
            return User.vars.items;
        }, function (newValue) {
            newValue.then(function (items) {
                if (items > 1000) {
                    items = "+1k";
                }
                $scope.vars.items = items;
            });
        });

        $scope.$watch(function () {
            return User.vars.stars;
        }, function (newValue) {
            if (newValue !== undefined) {
                newValue.then(function (data) {
                    $scope.vars.stars = data;
                });
            }
        });
    });