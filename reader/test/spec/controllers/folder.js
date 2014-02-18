'use strict';

describe('Controller: FolderCtrl', function () {

  // load the controller's module
  beforeEach(module('readerApp'));

  var FolderCtrl,
    scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    FolderCtrl = $controller('FolderCtrl', {
      $scope: scope
    });
  }));

  it('should attach a list of awesomeThings to the scope', function () {
    expect(scope.awesomeThings.length).toBe(3);
  });
});
