#import <XCTest/XCTest.h>
#import <stdlib.h>

#import "../GSCommandRunner.h"
#import "../GSCommandContext.h"

@interface GSCommandRunner (Testing)
- (NSString *)commandSummary:(NSString *)command;
- (BOOL)artifact:(NSDictionary *)artifact matchesToolchain:(NSDictionary *)toolchain;
- (BOOL)artifact:(NSDictionary *)artifact matchesDistributionForEnvironment:(NSDictionary *)environment;
- (BOOL)packageRequirements:(NSDictionary *)requirements
           matchEnvironment:(NSDictionary *)environment
                     reason:(NSString **)reason;
- (NSDictionary *)selectedPackageArtifactForPackage:(NSDictionary *)packageRecord
                                        environment:(NSDictionary *)environment
                                     selectionError:(NSString **)selectionError;
- (NSDictionary *)nativeToolchainAssessmentForEnvironment:(NSDictionary *)environment compatibility:(NSDictionary *)compatibility;
- (NSDictionary *)evaluateCompatibilityForEnvironment:(NSDictionary *)environment artifact:(NSDictionary *)artifact;
- (NSString *)classifyEnvironment:(NSDictionary *)environment compatibility:(NSDictionary *)compatibility;
- (NSDictionary *)compilerInfoForExecutable:(NSString *)compilerExecutable;
- (BOOL)hasWindowsManagedToolchainHintWithMakefiles:(NSString *)gnustepMakefiles;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory;
- (NSDictionary *)detectProjectAtPath:(NSString *)projectPath;
- (NSArray *)toolRunInvocationForProject:(NSDictionary *)project;
- (NSDictionary *)executeRunForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSComparisonResult)compareVersionString:(NSString *)left toVersionString:(NSString *)right;
@end

@interface GSCommandRunnerTests : XCTestCase
@end

@implementation GSCommandRunnerTests

- (NSDictionary *)clangEnvironment
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        @"linux", @"os",
                        @"amd64", @"arch",
                        [NSDictionary dictionaryWithObjectsAndKeys:
                                      [NSNumber numberWithBool: YES], @"present",
                                      @"clang", @"compiler_family",
                                      @"clang", @"toolchain_flavor",
                                      @"libobjc2", @"objc_runtime",
                                      @"modern", @"objc_abi",
                                      [NSDictionary dictionaryWithObjectsAndKeys:
                                                    [NSNumber numberWithBool: YES], @"blocks",
                                                    [NSNumber numberWithBool: YES], @"arc",
                                                    nil], @"feature_flags",
                                      nil], @"toolchain",
                        nil];
}

- (NSDictionary *)gccEnvironment
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        @"linux", @"os",
                        @"amd64", @"arch",
                        [NSDictionary dictionaryWithObjectsAndKeys:
                                      [NSNumber numberWithBool: YES], @"present",
                                      @"gcc", @"compiler_family",
                                      @"gcc", @"toolchain_flavor",
                                      @"gcc_libobjc", @"objc_runtime",
                                      @"legacy", @"objc_abi",
                                      [NSNumber numberWithBool: YES], @"can_compile",
                                      [NSNumber numberWithBool: YES], @"can_link",
                                      [NSNumber numberWithBool: YES], @"can_run",
                                      [NSDictionary dictionaryWithObjectsAndKeys:
                                                    [NSNumber numberWithBool: NO], @"blocks",
                                                    [NSNumber numberWithBool: NO], @"arc",
                                                    nil], @"feature_flags",
                                      nil], @"toolchain",
                        nil];
}

- (NSDictionary *)gccEnvironmentForDistribution:(NSString *)distributionID
{
  NSMutableDictionary *environment = [[self gccEnvironment] mutableCopy];
  [environment setObject: distributionID forKey: @"distribution_id"];
  return [environment autorelease];
}

- (NSDictionary *)windowsManagedDeferredProbeEnvironment
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        @"windows", @"os",
                        @"amd64", @"arch",
                        [NSDictionary dictionaryWithObjectsAndKeys:
                                      [NSNumber numberWithBool: YES], @"present",
                                      @"clang", @"compiler_family",
                                      @"msys2-clang64", @"toolchain_flavor",
                                      @"libobjc2", @"objc_runtime",
                                      @"modern", @"objc_abi",
                                      [NSNumber numberWithBool: NO], @"can_compile",
                                      [NSNumber numberWithBool: NO], @"can_link",
                                      [NSNumber numberWithBool: NO], @"can_run",
                                      [NSDictionary dictionaryWithObjectsAndKeys:
                                                    @"not_run", @"status",
                                                    @"windows_subprocess_probe_deferred", @"reason",
                                                    nil], @"probe",
                                      [NSDictionary dictionaryWithObjectsAndKeys:
                                                    [NSNumber numberWithBool: YES], @"blocks",
                                                    [NSNumber numberWithBool: YES], @"arc",
                                                    nil], @"feature_flags",
                                      nil], @"toolchain",
                        nil];
}

- (NSDictionary *)compatibleResult
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: YES], @"compatible",
                        [NSArray array], @"reasons",
                        [NSArray array], @"warnings",
                        nil];
}

- (void)testRunCommandTimesOutHungProbe
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  NSString *shell = @"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe";
  NSArray *arguments = [NSArray arrayWithObjects: shell, @"-NoProfile", @"-Command", @"Start-Sleep -Seconds 5", nil];
#else
  NSArray *arguments = [NSArray arrayWithObjects: @"/bin/sh", @"-c", @"sleep 5", nil];
#endif
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *result = nil;

  setenv("GNUSTEP_CLI_COMMAND_TIMEOUT_SECONDS", "1", 1);
  result = [runner runCommand: arguments currentDirectory: nil];
  unsetenv("GNUSTEP_CLI_COMMAND_TIMEOUT_SECONDS");

  XCTAssertTrue([[result objectForKey: @"launched"] boolValue]);
  XCTAssertTrue([[result objectForKey: @"timed_out"] boolValue]);
  XCTAssertEqual([[result objectForKey: @"exit_status"] intValue], 124);
}

- (void)testKnownCommandsStayInContractOrder
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSArray *expected = [NSArray arrayWithObjects:
                                  @"setup",
                                  @"doctor",
                                  @"build",
                                  @"clean",
                                  @"run",
                                  @"shell",
                                  @"new",
                                  @"install",
                                  @"remove",
                                  @"update",
                                  nil];

  XCTAssertEqualObjects([runner knownCommands], expected);
}

- (void)testCommandSummariesRemainNonEmptyForShippedCommands
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSArray *commands = [runner knownCommands];
  NSUInteger i = 0;

  for (i = 0; i < [commands count]; i++)
    {
      NSString *command = [commands objectAtIndex: i];
      XCTAssertTrue([[runner commandSummary: command] length] > 0);
    }
}


- (void)testDetectsAggregateGNUmakefileAsBuildable
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *gnumakefile = [root stringByAppendingPathComponent: @"GNUmakefile"];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDictionary *project = nil;

  XCTAssertTrue([manager createDirectoryAtPath: root withIntermediateDirectories: YES attributes: nil error: NULL]);
  XCTAssertTrue([@"SUBPROJECTS = InterfaceBuilder GormCore Tools\ninclude $(GNUSTEP_MAKEFILES)/aggregate.make\n"
    writeToFile: gnumakefile
      atomically: YES
        encoding: NSUTF8StringEncoding
           error: NULL]);

  project = [runner detectProjectAtPath: root];
  XCTAssertTrue([[project objectForKey: @"supported"] boolValue]);
  XCTAssertEqualObjects([project objectForKey: @"project_type"], @"aggregate");
  XCTAssertEqualObjects([project objectForKey: @"build_system"], @"gnustep-make");
  XCTAssertEqualObjects([project objectForKey: @"detection_reason"], @"gnumakefile_marker");
  XCTAssertEqualObjects([project objectForKey: @"target_name"], [NSNull null]);
  [manager removeItemAtPath: root error: NULL];
}

- (void)testDetectsUnknownGNUmakefileAsBuildable
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *gnumakefile = [root stringByAppendingPathComponent: @"GNUmakefile"];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDictionary *project = nil;

  XCTAssertTrue([manager createDirectoryAtPath: root withIntermediateDirectories: YES attributes: nil error: NULL]);
  XCTAssertTrue([@"include $(GNUSTEP_MAKEFILES)/common.make\n"
    writeToFile: gnumakefile
      atomically: YES
        encoding: NSUTF8StringEncoding
           error: NULL]);

  project = [runner detectProjectAtPath: root];
  XCTAssertTrue([[project objectForKey: @"supported"] boolValue]);
  XCTAssertEqualObjects([project objectForKey: @"project_type"], @"unknown");
  XCTAssertEqualObjects([project objectForKey: @"target_name"], [NSNull null]);
  [manager removeItemAtPath: root error: NULL];
}

- (void)testToolRunInvocationUsesWindowsExecutableWhenPresent
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *obj = [root stringByAppendingPathComponent: @"obj"];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDictionary *project = nil;
  NSArray *invocation = nil;
  NSArray *expected = [NSArray arrayWithObjects: @"./obj/hello.exe", nil];

  XCTAssertTrue([manager createDirectoryAtPath: obj withIntermediateDirectories: YES attributes: nil error: NULL]);
  XCTAssertTrue([@"" writeToFile: [obj stringByAppendingPathComponent: @"hello.exe"]
                       atomically: YES
                         encoding: NSUTF8StringEncoding
                            error: NULL]);

  project = [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: YES], @"supported",
                            @"gnustep-make", @"build_system",
                            @"tool", @"project_type",
                            @"hello", @"target_name",
                            root, @"project_dir",
                            nil];
  invocation = [runner toolRunInvocationForProject: project];

  XCTAssertEqualObjects(invocation, expected);
  [manager removeItemAtPath: root error: NULL];
}

- (void)testRunReportsMissingAppBundleBeforeLaunching
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *gnumakefile = [root stringByAppendingPathComponent: @"GNUmakefile"];
  NSFileManager *manager = [NSFileManager defaultManager];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  XCTAssertTrue([manager createDirectoryAtPath: root withIntermediateDirectories: YES attributes: nil error: NULL]);
  XCTAssertTrue([@"APP_NAME = Gorm\ninclude $(GNUSTEP_MAKEFILES)/application.make\n"
    writeToFile: gnumakefile
      atomically: YES
        encoding: NSUTF8StringEncoding
           error: NULL]);

  context = [GSCommandContext contextWithArguments: [NSArray arrayWithObjects: @"run", root, nil]];
  payload = [runner executeRunForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"backend"], @"openapp");
  XCTAssertEqualObjects([payload objectForKey: @"invocation"], [NSNull null]);
  XCTAssertTrue([[payload objectForKey: @"summary"] rangeOfString: @"Gorm.app was not found"].location != NSNotFound);

  [manager removeItemAtPath: root error: NULL];
}

- (void)testDogfoodVersionComparisonUsesTimestampBeforeHash
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *older = @"0.1.0-dev-dogfood.20260422T183802Z.ge6e7341.5";
  NSString *newer = @"0.1.0-dev-dogfood.20260422T184223Z.gb8979cb.7";

  XCTAssertEqual([runner compareVersionString: newer toVersionString: older], NSOrderedDescending);
  XCTAssertEqual([runner compareVersionString: older toVersionString: newer], NSOrderedAscending);
}

- (void)testWindowsManagedToolchainHintRecognizesInstalledReleaseLayout
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *makefiles = [[[root stringByAppendingPathComponent: @"share"]
                                  stringByAppendingPathComponent: @"GNUstep"]
                                  stringByAppendingPathComponent: @"Makefiles"];
  NSString *bin = [[root stringByAppendingPathComponent: @"usr"] stringByAppendingPathComponent: @"bin"];
  NSFileManager *manager = [NSFileManager defaultManager];

  XCTAssertTrue([manager createDirectoryAtPath: makefiles withIntermediateDirectories: YES attributes: nil error: NULL]);
  XCTAssertTrue([manager createDirectoryAtPath: bin withIntermediateDirectories: YES attributes: nil error: NULL]);
  NSString *compilerBin = [root stringByAppendingPathComponent: @"bin"];

  XCTAssertTrue([manager createDirectoryAtPath: compilerBin withIntermediateDirectories: YES attributes: nil error: NULL]);
  XCTAssertTrue([@"" writeToFile: [compilerBin stringByAppendingPathComponent: @"clang.exe"]
                       atomically: YES
                         encoding: NSUTF8StringEncoding
                            error: NULL]);
  XCTAssertTrue([@"" writeToFile: [bin stringByAppendingPathComponent: @"bash.exe"]
                       atomically: YES
                         encoding: NSUTF8StringEncoding
                            error: NULL]);
  XCTAssertTrue([runner hasWindowsManagedToolchainHintWithMakefiles: makefiles]);
  [manager removeItemAtPath: root error: NULL];
#else
  XCTAssertTrue(YES);
#endif
}

- (void)testArtifactDistributionMatchingHonorsUbuntuOSVersion
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *artifact = [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"linux", @"os",
                                           @"amd64", @"arch",
                                           [NSArray arrayWithObject: @"ubuntu"], @"supported_distributions",
                                           [NSArray arrayWithObject: @"ubuntu-24.04"], @"supported_os_versions",
                                           nil];
  NSDictionary *ubuntu2404 = [NSDictionary dictionaryWithObjectsAndKeys:
                                             @"linux", @"os",
                                             @"amd64", @"arch",
                                             @"ubuntu", @"distribution_id",
                                             @"ubuntu-24.04", @"os_version",
                                             nil];
  NSDictionary *ubuntu2604 = [NSDictionary dictionaryWithObjectsAndKeys:
                                             @"linux", @"os",
                                             @"amd64", @"arch",
                                             @"ubuntu", @"distribution_id",
                                             @"ubuntu-26.04", @"os_version",
                                             nil];

  XCTAssertTrue([runner artifact: artifact matchesDistributionForEnvironment: ubuntu2404]);
  XCTAssertFalse([runner artifact: artifact matchesDistributionForEnvironment: ubuntu2604]);
}

- (void)testCompatibilityReasonsSeparateDistributionAndOSVersion
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *artifact = [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"cli-linux-ubuntu2404-amd64-clang", @"id",
                                           @"cli", @"kind",
                                           @"linux", @"os",
                                           @"amd64", @"arch",
                                           @"clang", @"compiler_family",
                                           [NSArray arrayWithObject: @"ubuntu"], @"supported_distributions",
                                           [NSArray arrayWithObject: @"ubuntu-24.04"], @"supported_os_versions",
                                           nil];
  NSDictionary *fedora = [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"linux", @"os",
                                         @"amd64", @"arch",
                                         @"fedora", @"distribution_id",
                                         @"fedora-41", @"os_version",
                                         [NSDictionary dictionaryWithObjectsAndKeys:
                                                       [NSNumber numberWithBool: NO], @"present",
                                                       nil], @"toolchain",
                                         nil];
  NSDictionary *ubuntu2604 = [NSDictionary dictionaryWithObjectsAndKeys:
                                             @"linux", @"os",
                                             @"amd64", @"arch",
                                             @"ubuntu", @"distribution_id",
                                             @"ubuntu-26.04", @"os_version",
                                             [NSDictionary dictionaryWithObjectsAndKeys:
                                                           [NSNumber numberWithBool: NO], @"present",
                                                           nil], @"toolchain",
                                             nil];

  NSArray *fedoraReasons = [[runner evaluateCompatibilityForEnvironment: fedora artifact: artifact] objectForKey: @"reasons"];
  NSArray *ubuntuReasons = [[runner evaluateCompatibilityForEnvironment: ubuntu2604 artifact: artifact] objectForKey: @"reasons"];
  NSMutableArray *fedoraCodes = [NSMutableArray array];
  NSMutableArray *ubuntuCodes = [NSMutableArray array];
  NSUInteger index = 0;

  for (index = 0; index < [fedoraReasons count]; index++)
    {
      [fedoraCodes addObject: [[fedoraReasons objectAtIndex: index] objectForKey: @"code"]];
    }
  for (index = 0; index < [ubuntuReasons count]; index++)
    {
      [ubuntuCodes addObject: [[ubuntuReasons objectAtIndex: index] objectForKey: @"code"]];
    }

  XCTAssertTrue([fedoraCodes containsObject: @"unsupported_distribution"]);
  XCTAssertTrue([ubuntuCodes containsObject: @"unsupported_os_version"]);
  XCTAssertFalse([ubuntuCodes containsObject: @"unsupported_distribution"]);
}

- (void)testArtifactMatchesToolchainWhenRuntimeAndFeaturesAlign
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *artifact = [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"clang", @"compiler_family",
                                           @"clang", @"toolchain_flavor",
                                           @"libobjc2", @"objc_runtime",
                                           @"modern", @"objc_abi",
                                           [NSArray arrayWithObjects: @"blocks", @"arc", nil], @"required_features",
                                           nil];
  BOOL matches = [runner artifact: artifact
                 matchesToolchain: [[self clangEnvironment] objectForKey: @"toolchain"]];

  XCTAssertTrue(matches);
}

- (void)testArtifactRejectsMismatchedToolchainFlavor
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *artifact = [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"clang", @"compiler_family",
                                           @"msys2-clang64", @"toolchain_flavor",
                                           @"libobjc2", @"objc_runtime",
                                           @"modern", @"objc_abi",
                                           [NSArray array], @"required_features",
                                           nil];
  BOOL matches = [runner artifact: artifact
                 matchesToolchain: [[self clangEnvironment] objectForKey: @"toolchain"]];

  XCTAssertFalse(matches);
}

- (void)testPackageRequirementsExplainMissingFeature
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSMutableDictionary *environment = [[self clangEnvironment] mutableCopy];
  NSMutableDictionary *toolchain = [[[environment objectForKey: @"toolchain"] mutableCopy] autorelease];
  NSMutableDictionary *featureFlags = [[[toolchain objectForKey: @"feature_flags"] mutableCopy] autorelease];
  NSString *reason = nil;
  NSDictionary *requirements = [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSArray arrayWithObject: @"linux"], @"supported_os",
                                               [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                               [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                               [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                               [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                               [NSArray arrayWithObject: @"arc"], @"required_features",
                                               [NSArray array], @"forbidden_features",
                                               nil];
  BOOL matches = NO;

  [featureFlags setObject: [NSNumber numberWithBool: NO] forKey: @"arc"];
  [toolchain setObject: featureFlags forKey: @"feature_flags"];
  [environment setObject: toolchain forKey: @"toolchain"];

  matches = [runner packageRequirements: requirements
                       matchEnvironment: environment
                                 reason: &reason];
  XCTAssertFalse(matches);
  XCTAssertEqualObjects(reason, @"Package requires Objective-C feature 'arc'.");
  [environment release];
}


- (void)testPackageRequirementsRejectMalformedFeatureLists
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *reason = nil;
  NSDictionary *requirements = [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSArray arrayWithObject: @"linux"], @"supported_os",
                                               @"blocks", @"required_features",
                                               nil];
  BOOL matches = [runner packageRequirements: requirements
                            matchEnvironment: [self clangEnvironment]
                                      reason: &reason];

  XCTAssertFalse(matches);
  XCTAssertEqualObjects(reason, @"Package required_features must be an array.");
}

- (void)testPackageRequirementsRejectMalformedRequirementsObject
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *reason = nil;
  BOOL matches = [runner packageRequirements: (NSDictionary *)@"not-a-requirements-object"
                            matchEnvironment: [self clangEnvironment]
                                      reason: &reason];

  XCTAssertFalse(matches);
  XCTAssertEqualObjects(reason, @"Package requirements are malformed.");
}

- (void)testPackageArtifactSelectionUsesDetectedToolchain
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *packageRecord = [NSDictionary dictionaryWithObjectsAndKeys:
                                                [NSArray arrayWithObjects:
                                                           [NSDictionary dictionaryWithObjectsAndKeys:
                                                                          @"pkg-linux-gcc", @"id",
                                                                          @"linux", @"os",
                                                                          @"amd64", @"arch",
                                                                          @"gcc", @"compiler_family",
                                                                          @"gcc", @"toolchain_flavor",
                                                                          @"gcc_libobjc", @"objc_runtime",
                                                                          @"legacy", @"objc_abi",
                                                                          [NSArray array], @"required_features",
                                                                          nil],
                                                           [NSDictionary dictionaryWithObjectsAndKeys:
                                                                          @"pkg-linux-clang", @"id",
                                                                          @"linux", @"os",
                                                                          @"amd64", @"arch",
                                                                          @"clang", @"compiler_family",
                                                                          @"clang", @"toolchain_flavor",
                                                                          @"libobjc2", @"objc_runtime",
                                                                          @"modern", @"objc_abi",
                                                                          [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                          nil],
                                                           nil], @"artifacts",
                                                nil];
  NSString *selectionError = nil;
  NSDictionary *selected = [runner selectedPackageArtifactForPackage: packageRecord
                                                         environment: [self clangEnvironment]
                                                      selectionError: &selectionError];

  XCTAssertNil(selectionError);
  XCTAssertEqualObjects([selected objectForKey: @"id"], @"pkg-linux-clang");
}

- (void)testFedoraAndArchGCCPackagedToolchainsAreInteropOnly
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *fedora = [runner nativeToolchainAssessmentForEnvironment: [self gccEnvironmentForDistribution: @"fedora"]
                                                           compatibility: [self compatibleResult]];
  NSDictionary *arch = [runner nativeToolchainAssessmentForEnvironment: [self gccEnvironmentForDistribution: @"arch"]
                                                         compatibility: [self compatibleResult]];

  XCTAssertEqualObjects([fedora objectForKey: @"assessment"], @"interoperability_only");
  XCTAssertEqualObjects([fedora objectForKey: @"preference"], @"managed");
  XCTAssertEqualObjects([arch objectForKey: @"assessment"], @"interoperability_only");
  XCTAssertEqualObjects([arch objectForKey: @"preference"], @"managed");
}

- (void)testWindowsManagedDeferredProbeIsNotClassifiedAsBroken
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *environment = [self windowsManagedDeferredProbeEnvironment];
  NSDictionary *assessment = [runner nativeToolchainAssessmentForEnvironment: environment
                                                               compatibility: [self compatibleResult]];
  NSString *classification = [runner classifyEnvironment: environment compatibility: [self compatibleResult]];

  XCTAssertEqualObjects([assessment objectForKey: @"assessment"], @"supported");
  XCTAssertEqualObjects(classification, @"toolchain_compatible");
}

- (void)testPackageArtifactSelectionUsesGNUstepMakeGCCRuntimeWhenDetected
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *packageRecord = [NSDictionary dictionaryWithObjectsAndKeys:
                                                [NSArray arrayWithObjects:
                                                           [NSDictionary dictionaryWithObjectsAndKeys:
                                                                          @"pkg-linux-clang", @"id",
                                                                          @"linux", @"os",
                                                                          @"amd64", @"arch",
                                                                          @"clang", @"compiler_family",
                                                                          @"clang", @"toolchain_flavor",
                                                                          @"libobjc2", @"objc_runtime",
                                                                          @"modern", @"objc_abi",
                                                                          [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                          nil],
                                                           [NSDictionary dictionaryWithObjectsAndKeys:
                                                                          @"pkg-linux-gcc", @"id",
                                                                          @"linux", @"os",
                                                                          @"amd64", @"arch",
                                                                          @"gcc", @"compiler_family",
                                                                          @"gcc", @"toolchain_flavor",
                                                                          @"gcc_libobjc", @"objc_runtime",
                                                                          @"legacy", @"objc_abi",
                                                                          [NSArray array], @"required_features",
                                                                          nil],
                                                           nil], @"artifacts",
                                                nil];
  NSString *selectionError = nil;
  NSDictionary *selected = [runner selectedPackageArtifactForPackage: packageRecord
                                                         environment: [self gccEnvironment]
                                                      selectionError: &selectionError];

  XCTAssertNil(selectionError);
  XCTAssertEqualObjects([selected objectForKey: @"id"], @"pkg-linux-gcc");
}

@end
