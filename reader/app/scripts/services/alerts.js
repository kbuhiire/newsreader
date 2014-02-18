'use strict';

angular.module('readerApp')
    .service('Alerts', function Alerts($timeout) {
        var Alerts = function () {
            this.alerts = [];
        };
        Alerts.prototype.addAlert = function (alertType, message) {
            var that = this;
            this.alerts.push({
                type: alertType,
                msg: message
            });
            $timeout(function () {
                that.alerts.splice(0, 1);
            }, 5000);
        };
        Alerts.prototype.closeAlert = function (index) {
            this.alerts.splice(index, 1);
        };
        return new Alerts();
    });