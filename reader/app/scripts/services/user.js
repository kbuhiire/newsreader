'use strict';

angular.module('readerApp')
    .service('User', function User($http) {
        return {
            info: $http.get('/api/v1/user/').then(function (response) {
                return response.data.objects[0];
            }),
            feeds: $http.get('/api/v1/account/feeds/?limit=0').then(function (response) {
                var userFeeds = {
                    ids: [],
                    ind: {},
                    favicon: {},
                    title: {},
                    folders: {
                        'Main Folder': true
                    },
                    root: []
                };
                for (var i = 0; i < response.data.objects.length; i++) {
                    var thisFeed = response.data.objects[i];
                    if (thisFeed.folder === '~~Root') {
                        userFeeds.root.push(thisFeed);
                    } else if (userFeeds.folders[thisFeed.folder] === undefined || !userFeeds.folders[thisFeed.folder]) {
                        userFeeds.folders[thisFeed.folder] = [];
                        userFeeds.folders[thisFeed.folder].push(thisFeed);
                    } else {
                        userFeeds.folders[thisFeed.folder].push(thisFeed);
                    }
                    userFeeds.ids.push(thisFeed.id);
                    userFeeds.ind[thisFeed.id] = true;
                    userFeeds.favicon[thisFeed.id] = thisFeed.favicon;
                    userFeeds.title[thisFeed.id] = thisFeed.title;
                }
                return userFeeds;
            }),
            starred: $http.get('/api/v1/account/star/ids/').then(function (response) {
                var res = {};
                for (var i = 0; i < response.data.objects.length; i++) {
                    res[response.data.objects[i].article_id] = 1;
                }
                return res;
            }),
            vars: {
                items: $http.get('/api/v1/account/articles/').then(function (response) {
                    return response.data.meta.total_count;
                }),
                stars: $http.get('/api/v1/account/star/').then(function (response) {
                    return response.data.meta.total_count;
                })
            }
        };
    });