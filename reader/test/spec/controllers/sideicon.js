'use strict';

describe('Controller: SideiconCtrl', function () {

  // load the controller's module
  beforeEach(module('readerApp'));

  var SideiconCtrl,
    scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    SideiconCtrl = $controller('SideiconCtrl', {
      $scope: scope
    });
  }));

  it('should attach a list of awesomeThings to the scope', function () {
    expect(scope.awesomeThings.length).toBe(3);
  });
});
