'use strict';

describe('Controller: ChangefolderCtrl', function () {

  // load the controller's module
  beforeEach(module('readerApp'));

  var ChangefolderCtrl,
    scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    ChangefolderCtrl = $controller('ChangefolderCtrl', {
      $scope: scope
    });
  }));

  it('should attach a list of awesomeThings to the scope', function () {
    expect(scope.awesomeThings.length).toBe(3);
  });
});
