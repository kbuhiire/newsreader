'use strict';

angular.module('readerApp')
    .controller('CollapsedCtrl', function ($scope, Subscription, $http, User, $timeout, $location) {
        $scope.selected = undefined;
        $scope.buttonSubscribe = false;
        $scope.buttonShowSpinner = true;
        $scope.buttonSubscribeText = 'Add';
        $scope.formSubscribedClass = undefined;
        $scope.submit = undefined;
        $scope.lock = false;

        $scope.$watch(function () {
            return Subscription.show;
        }, function (newValue) {
            $scope.show = newValue;
        });

        // Helper to manage dynamic typeahead form
        $scope.manageTypeahead = function () {
            if ($scope.submit !== undefined) {
                $scope.submit();
            }
        };

        $scope.resetTypeahead = function () {
            $scope.selected = undefined;
            $scope.buttonSubscribe = false;
            $scope.submit = undefined;
            $scope.lock = false;
            $scope.buttonSubscribeText = 'Add';
        };

        $scope.close = function () {
            Subscription.show = false;
        };

        $scope.typeaheadSearch = function (item) {
            if ($scope.lock) {
                return [];
            }
            $scope.lock = true;
            $scope.resetTypeahead();
            if (item.length >= 8 && (S(item).startsWith('http://') || S(item).startsWith('https://'))) {
                $scope.buttonSubscribeText = 'Go';
                $scope.submit = $scope.tryToAdd;
                $scope.lock = false;
                return [];
            }
            return $http.get('/api/v1/feeds/search', {
                params: {
                    q: item
                }
            }).then(function (data) {
                var results = [];
                var obj = data.data.objects;
                for (var i = 0; i < obj.length; i++) {
                    results.push(obj[i]);
                }
                if (obj.length > 0) {
                    $scope.flood = 0;
                }
                $scope.lock = false;
                return results;
            });
        };

        $scope.tryToAdd = function () {
            if (!$scope.lock) {
                $scope.lock = true;
                $scope.buttonSubscribeText = '<i class="fa fa-spinner fa-spin" />';
                $scope.submit = undefined;
                return $http.post('/api/v1/feeds/', {
                    feed: $scope.selected
                }).error(function () {
                    $scope.formSubscribedClass = 'has-error';
                    $timeout($scope.resetTypeahead, 5000);
                    return [];
                }).then(function (data) {
                    if (!data.data.success) {
                        $scope.formSubscribedClass = 'has-error';
                        $timeout($scope.resetTypeahead, 5000);
                        return [];
                    } else {
                        User.feeds.then(function (res) {
                            if (res.ids.indexOf(data.data.feed_id) > -1) {
                                $scope.buttonSubscribeText = 'Show';
                                $scope.submit = $scope.manageFeed;
                                $scope.adding = {
                                    id: data.data.feed_id
                                };
                                $scope.mode = 0;
                            } else {
                                $scope.adding = {
                                    id: data.data.feed_id
                                };
                                $scope.buttonFeed = true;
                                $scope.buttonFeedClass = 'btn-success';
                                $scope.buttonSubscribeText = 'Add';
                                $scope.submit = $scope.manageFeed;
                                $scope.mode = 1;
                            }
                        });
                        $scope.lock = false;
                        return [data.data];
                    }
                });
            } else {
                return [];
            }
        };

        $scope.selectMatch = function (item) {
            User.feeds.then(function (data) {
                $scope.submit = $scope.manageFeed;
                if (data.ids.indexOf(item.id) > -1) {
                    $scope.buttonSubscribeText = 'Show';
                    $scope.submit = $scope.manageFeed;
                    $scope.adding = item;
                    $scope.mode = 0;
                } else {
                    $scope.adding = item;
                    $scope.buttonSubscribeText = 'Add';
                    $scope.mode = 1;
                }
            });
        };

        $scope.manageFeed = function () {
            if ($scope.mode === 0) {
                $scope.resetTypeahead();
                $scope.close();
                $location.search('q', null).path('/feed/' + $scope.adding.id).replace();
            } else if ($scope.adding !== undefined && $scope.lock !== true) {
                $scope.lock = true;
                $http.post('/api/v1/account/feeds/' + $scope.adding.id + '/', {}, {
                    params: {
                        folder: '~~Root'
                    }
                }).success(function () {
                    User.feeds.then(function (res) {
                        $http.get('/api/v1/account/feeds/', {
                            params: {
                                feed: $scope.adding.id
                            }
                        }).success(function (info) {
                            console.log(info);
                            if (info.objects.length > 0) {
                                var addThis = info.objects[0];
                                res.ids.splice(0, 0, addThis.id);
                                res.ind[addThis] = true;
                                res.title[addThis.id] = addThis.title;
                                res.favicon[addThis.id] = addThis.favicon;
                                if (addThis.folder === '~~Root') {
                                    res.root.push(addThis);
                                } else if (res.folders[addThis.folder] === undefined || !res.folders[addThis.folder]) {
                                    res.folders[addThis.folder] = [];
                                    res.folders[addThis.folder].push(addThis);
                                } else {
                                    res.folders[addThis.folder].push(addThis);
                                }
                                return res;
                            }
                        });
                    });
                    $scope.resetTypeahead();
                    $scope.close();
                    $scope.lock = false;
                }).error(function () {});
            }
            return [];
        };
    });