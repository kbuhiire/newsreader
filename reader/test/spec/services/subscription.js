'use strict';

describe('Service: Subscription', function () {

  // load the service's module
  beforeEach(module('readerApp'));

  // instantiate service
  var Subscription;
  beforeEach(inject(function (_Subscription_) {
    Subscription = _Subscription_;
  }));

  it('should do something', function () {
    expect(!!Subscription).toBe(true);
  });

});
