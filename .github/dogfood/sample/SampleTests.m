#import <XCTest/XCTest.h>

@interface SampleTests : XCTestCase
@end

@implementation SampleTests

- (void)testArithmetic
{
  XCTAssertEqual(1 + 1, 2);
}

- (void)testFoundation
{
  NSArray *items = [NSArray arrayWithObjects: @"a", @"b", nil];
  XCTAssertEqualObjects([items componentsJoinedByString: @","], @"a,b");
}

#ifdef SAMPLE_FAIL
// Built with -DSAMPLE_FAIL: `make check` must then exit nonzero.
- (void)testDeliberateFailure
{
  XCTAssertEqual(1 + 1, 3);
}
#endif

@end
