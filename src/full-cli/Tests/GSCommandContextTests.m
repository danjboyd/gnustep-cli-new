#import <XCTest/XCTest.h>

#import "../GSCommandContext.h"

@interface GSCommandContextTests : XCTestCase
@end

@implementation GSCommandContextTests

- (void)testParsesGlobalOptionsAndCommandArguments
{
  NSArray *expectedArguments = [NSArray arrayWithObjects: @"--manifest", @"fixture.json", nil];
  GSCommandContext *context = [GSCommandContext contextWithArguments:
                                                  [NSArray arrayWithObjects:
                                                             @"--json",
                                                             @"--verbose",
                                                             @"doctor",
                                                             @"--manifest",
                                                             @"fixture.json",
                                                             nil]];

  XCTAssertTrue([context jsonOutput]);
  XCTAssertTrue([context verbose]);
  XCTAssertFalse([context quiet]);
  XCTAssertEqualObjects([context command], @"doctor");
  XCTAssertEqualObjects([context commandArguments], expectedArguments);
  XCTAssertNil([context usageError]);
}

- (void)testRejectsUnknownGlobalOptionBeforeCommand
{
  GSCommandContext *context = [GSCommandContext contextWithArguments:
                                                  [NSArray arrayWithObjects:
                                                             @"--bogus",
                                                             @"doctor",
                                                             nil]];

  XCTAssertEqualObjects([context usageError], @"Unknown global option: --bogus");
}

- (void)testAllowsCommandSpecificOptionsAfterCommand
{
  NSArray *expectedArguments = [NSArray arrayWithObjects: @"--root", @"/tmp/managed", nil];
  GSCommandContext *context = [GSCommandContext contextWithArguments:
                                                  [NSArray arrayWithObjects:
                                                             @"setup",
                                                             @"--root",
                                                             @"/tmp/managed",
                                                             nil]];

  XCTAssertEqualObjects([context command], @"setup");
  XCTAssertEqualObjects([context commandArguments], expectedArguments);
  XCTAssertNil([context usageError]);
}

- (void)testTracksHelpAndVersionWithoutACommand
{
  GSCommandContext *context = [GSCommandContext contextWithArguments:
                                                  [NSArray arrayWithObjects:
                                                             @"--help",
                                                             @"--version",
                                                             nil]];

  XCTAssertTrue([context showHelp]);
  XCTAssertTrue([context showVersion]);
  XCTAssertNil([context command]);
  XCTAssertEqual([[context commandArguments] count], (NSUInteger)0);
}

@end
