'use strict';

angular.module('readerApp')
    .controller('AlertsCtrl', function ($scope, Alerts) {
        $scope.alerts = Alerts;
    });