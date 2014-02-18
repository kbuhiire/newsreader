'use strict';

angular.module('readerApp', [
    'ngCookies',
    'ngResource',
    'ngSanitize',
    'ngRoute',
    'http-auth-interceptor',
    'infinite-scroll',
    'truncate',
    'wu.masonry',
    'angularMoment',
    'ui.bootstrap',
    'ngProgressLite',
])
    .config(function ($routeProvider) {
        $routeProvider
            .when('/', {
                templateUrl: 'views/main.html',
                controller: 'MainCtrl'
            })
            .when('/stream', {
                templateUrl: 'views/items.html',
                controller: 'ItemsCtrl'
            })
            .when('/settings', {
                templateUrl: 'views/settings.html',
                controller: 'SettingsCtrl'
            })
            .when('/starred', {
                templateUrl: 'views/items.html',
                controller: 'StarredCtrl'
            })
            .when('/folder/:folderName', {
                templateUrl: 'views/items.html',
                controller: 'FolderCtrl'
            })
            .when('/feed/:feedId', {
                templateUrl: 'views/items.html',
                controller: 'FeedCtrl'
            })
            .when('/search', {
                templateUrl: 'views/items.html',
                controller: 'SearchCtrl'
            })
            .otherwise({
                redirectTo: '/'
            });
    })
    .run(function ($location, $rootScope, $cookies, $http, ngProgressLite) {
        $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
        $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
        $rootScope.$on('event:auth-loginRequired', function () {
            window.location = '/';
        });
        $rootScope.$on('$routeChangeStart', function (next, current) {
            ngProgressLite.start();
            ngProgressLite.done();
        });
    });