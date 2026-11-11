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
- (NSDate *)bundledAuthoritiesDateFromSource:(NSString *)sourceText;
- (NSString *)managedRootInUseForToolchainMakefiles:(NSString *)gnustepMakefiles statePath:(NSString *)statePath;
- (NSString *)versionedInstallRootForReleaseRoot:(NSString *)releaseRoot;
- (NSDictionary *)bundledAuthoritiesCheckWithMakefiles:(NSString *)gnustepMakefiles
                                             interface:(NSString *)interface
                                                 today:(NSDate *)today
                                               windows:(BOOL)windows;
@end

@interface GSCommandRunnerTests : XCTestCase
@end

static NSString *GSTestMSYS2ToolchainWithSource(NSString *source)
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *root = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *gstls = [root stringByAppendingPathComponent: @"clang64/lib/GNUstep/Libraries/gnustep-base/Versions/1.31/Resources/GSTLS"];
  NSString *makefiles = [root stringByAppendingPathComponent: @"clang64/share/GNUstep/Makefiles"];

  [manager createDirectoryAtPath: gstls withIntermediateDirectories: YES attributes: nil error: NULL];
  [manager createDirectoryAtPath: makefiles withIntermediateDirectories: YES attributes: nil error: NULL];
  [@"-----BEGIN CERTIFICATE-----\n" writeToFile: [gstls stringByAppendingPathComponent: @"ca-certificates.crt"]
                                      atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  if (source != nil)
    {
      [source writeToFile: [gstls stringByAppendingPathComponent: @"ca-certificates.source"]
               atomically: YES encoding: NSUTF8StringEncoding error: NULL];
    }
  return makefiles;
}

static NSDate *GSTestUTCDate(NSInteger year, NSInteger month, NSInteger day)
{
  NSCalendar *calendar = [[[NSCalendar alloc] initWithCalendarIdentifier: NSGregorianCalendar] autorelease];
  NSDateComponents *components = [[[NSDateComponents alloc] init] autorelease];

  [calendar setTimeZone: [NSTimeZone timeZoneForSecondsFromGMT: 0]];
  [components setYear: year];
  [components setMonth: month];
  [components setDay: day];
  [components setHour: 12];
  return [calendar dateFromComponents: components];
}

static void GSTestRemoveToolchain(NSString *makefiles)
{
  NSString *root = [[[[makefiles stringByDeletingLastPathComponent] stringByDeletingLastPathComponent]
                       stringByDeletingLastPathComponent] stringByDeletingLastPathComponent];
  [[NSFileManager defaultManager] removeItemAtPath: root error: NULL];
}


static NSString *GSTestManagedRoot(NSString *base, NSString *name, NSString *status)
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *root = [base stringByAppendingPathComponent: name];
  NSString *stateDir = [root stringByAppendingPathComponent: @"state"];

  [manager createDirectoryAtPath: stateDir withIntermediateDirectories: YES attributes: nil error: NULL];
  [manager createDirectoryAtPath: [root stringByAppendingPathComponent: @"System/Library/Makefiles"]
     withIntermediateDirectories: YES attributes: nil error: NULL];
  [[NSString stringWithFormat: @"{\"schema_version\": 1, \"status\": \"%@\"}", status]
    writeToFile: [stateDir stringByAppendingPathComponent: @"cli-state.json"] atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  return root;
}

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
                                  @"list",
                                  @"search",
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

  context = [GSCommandContext contextWithArguments: [NSArray arrayWithObjects: @"run", @"--no-build", root, nil]];
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

  NSDictionary *artifact2604 = [NSDictionary dictionaryWithObjectsAndKeys:
                                               @"linux", @"os",
                                               @"amd64", @"arch",
                                               [NSArray arrayWithObject: @"ubuntu"], @"supported_distributions",
                                               [NSArray arrayWithObject: @"ubuntu-26.04"], @"supported_os_versions",
                                               nil];

  XCTAssertTrue([runner artifact: artifact matchesDistributionForEnvironment: ubuntu2404]);
  XCTAssertFalse([runner artifact: artifact matchesDistributionForEnvironment: ubuntu2604]);
  XCTAssertTrue([runner artifact: artifact2604 matchesDistributionForEnvironment: ubuntu2604]);
  XCTAssertFalse([runner artifact: artifact2604 matchesDistributionForEnvironment: ubuntu2404]);
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

- (void)testArtifactSelectionRejectsMismatchedICUMajor
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *artifact = [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"linux", @"os",
                                           @"amd64", @"arch",
                                           [NSArray arrayWithObject: @"debian"], @"supported_distributions",
                                           [NSDictionary dictionaryWithObjectsAndKeys:
                                                         [NSNumber numberWithInt: 76], @"icu_major",
                                                         @"2.41", @"glibc_min", nil], @"runtime_requirements",
                                           nil];
  NSDictionary *trixie = [NSDictionary dictionaryWithObjectsAndKeys:
                                        @"linux", @"os", @"amd64", @"arch",
                                        @"debian", @"distribution_id", @"debian-13", @"os_version",
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                      [NSNumber numberWithInt: 76], @"icu_major",
                                                      @"2.41", @"glibc_version", nil], @"runtime_libraries",
                                        nil];
  NSDictionary *bookworm = [NSDictionary dictionaryWithObjectsAndKeys:
                                          @"linux", @"os", @"amd64", @"arch",
                                          @"debian", @"distribution_id", @"debian-12", @"os_version",
                                          [NSDictionary dictionaryWithObjectsAndKeys:
                                                        [NSNumber numberWithInt: 72], @"icu_major",
                                                        @"2.36", @"glibc_version", nil], @"runtime_libraries",
                                          nil];
  NSDictionary *undetected = [NSDictionary dictionaryWithObjectsAndKeys:
                                            @"linux", @"os", @"amd64", @"arch",
                                            @"debian", @"distribution_id", @"debian-13", @"os_version",
                                            [NSDictionary dictionaryWithObjectsAndKeys:
                                                          [NSNull null], @"icu_major",
                                                          [NSNull null], @"glibc_version", nil], @"runtime_libraries",
                                            nil];

  XCTAssertTrue([runner artifact: artifact matchesDistributionForEnvironment: trixie]);
  XCTAssertFalse([runner artifact: artifact matchesDistributionForEnvironment: bookworm]);
  // Undetectable host ICU must not falsely exclude (the gate warns instead).
  XCTAssertTrue([runner artifact: artifact matchesDistributionForEnvironment: undetected]);
}

- (void)testCompatibilityReasonsFlagICUMismatch
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *artifact = [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"toolchain-linux-amd64-clang", @"id",
                                           @"toolchain", @"kind",
                                           @"linux", @"os", @"amd64", @"arch",
                                           [NSArray arrayWithObject: @"debian"], @"supported_distributions",
                                           [NSDictionary dictionaryWithObjectsAndKeys:
                                                         [NSNumber numberWithInt: 76], @"icu_major",
                                                         @"2.41", @"glibc_min", nil], @"runtime_requirements",
                                           nil];
  NSDictionary *bookworm = [NSDictionary dictionaryWithObjectsAndKeys:
                                          @"linux", @"os", @"amd64", @"arch",
                                          @"debian", @"distribution_id", @"debian-12", @"os_version",
                                          [NSDictionary dictionaryWithObjectsAndKeys:
                                                        [NSNumber numberWithInt: 72], @"icu_major",
                                                        @"2.36", @"glibc_version", nil], @"runtime_libraries",
                                          [NSDictionary dictionaryWithObjectsAndKeys:
                                                        [NSNumber numberWithBool: NO], @"present", nil], @"toolchain",
                                          nil];
  NSDictionary *undetected = [NSDictionary dictionaryWithObjectsAndKeys:
                                            @"linux", @"os", @"amd64", @"arch",
                                            @"debian", @"distribution_id", @"debian-13", @"os_version",
                                            [NSDictionary dictionaryWithObjectsAndKeys:
                                                          [NSNull null], @"icu_major",
                                                          [NSNull null], @"glibc_version", nil], @"runtime_libraries",
                                            [NSDictionary dictionaryWithObjectsAndKeys:
                                                          [NSNumber numberWithBool: NO], @"present", nil], @"toolchain",
                                            nil];
  NSDictionary *bookwormResult = [runner evaluateCompatibilityForEnvironment: bookworm artifact: artifact];
  NSDictionary *undetectedResult = [runner evaluateCompatibilityForEnvironment: undetected artifact: artifact];
  NSMutableArray *bookwormCodes = [NSMutableArray array];
  NSMutableArray *undetectedWarnings = [NSMutableArray array];
  NSArray *reasons = [bookwormResult objectForKey: @"reasons"];
  NSArray *warnings = [undetectedResult objectForKey: @"warnings"];
  NSUInteger index = 0;

  for (index = 0; index < [reasons count]; index++)
    {
      [bookwormCodes addObject: [[reasons objectAtIndex: index] objectForKey: @"code"]];
    }
  for (index = 0; index < [warnings count]; index++)
    {
      [undetectedWarnings addObject: [[warnings objectAtIndex: index] objectForKey: @"code"]];
    }

  XCTAssertTrue([bookwormCodes containsObject: @"icu_major_mismatch"]);
  XCTAssertFalse([[bookwormResult objectForKey: @"compatible"] boolValue]);
  XCTAssertTrue([undetectedWarnings containsObject: @"icu_major_undetected"]);
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


- (void)testBundledAuthoritiesDateIsReadFromTheRecordedPackageVersion
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];

  XCTAssertEqualObjects([runner bundledAuthoritiesDateFromSource: @"mingw-w64-clang-x86_64-ca-certificates 20260816-1"],
                        [GSTestUTCDate(2026, 8, 16) dateByAddingTimeInterval: -12 * 3600]);
  XCTAssertNil([runner bundledAuthoritiesDateFromSource: @"mingw-w64-clang-x86_64-ca-certificates unknown"]);
  XCTAssertNil([runner bundledAuthoritiesDateFromSource: @"mingw-w64-clang-x86_64-ca-certificates 20260231-1"]);
  XCTAssertNil([runner bundledAuthoritiesDateFromSource: @"something else"]);
}

- (void)testBundledAuthoritiesCheckGradesTheRecordedAge
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDate *today = GSTestUTCDate(2026, 11, 9);
  NSString *makefiles = GSTestMSYS2ToolchainWithSource(@"mingw-w64-clang-x86_64-ca-certificates 20260816-1\n");
  NSDictionary *check = [runner bundledAuthoritiesCheckWithMakefiles: makefiles interface: @"full" today: today windows: YES];

  XCTAssertEqualObjects([check objectForKey: @"id"], @"tls.bundled-authorities");
  XCTAssertEqualObjects([check objectForKey: @"status"], @"ok");
  XCTAssertEqualObjects([[check objectForKey: @"details"] objectForKey: @"age_days"], [NSNumber numberWithInteger: 85]);
  GSTestRemoveToolchain(makefiles);

  makefiles = GSTestMSYS2ToolchainWithSource(@"mingw-w64-clang-x86_64-ca-certificates 20251108-1\n");
  check = [runner bundledAuthoritiesCheckWithMakefiles: makefiles interface: @"full" today: today windows: YES];
  XCTAssertEqualObjects([check objectForKey: @"status"], @"warning");
  XCTAssertEqualObjects([[check objectForKey: @"details"] objectForKey: @"age_days"], [NSNumber numberWithInteger: 366]);
  GSTestRemoveToolchain(makefiles);

  makefiles = GSTestMSYS2ToolchainWithSource(@"mingw-w64-clang-x86_64-ca-certificates 20251109-1\n");
  check = [runner bundledAuthoritiesCheckWithMakefiles: makefiles interface: @"full" today: today windows: YES];
  XCTAssertEqualObjects([check objectForKey: @"status"], @"ok");
  GSTestRemoveToolchain(makefiles);
}

- (void)testBundledAuthoritiesWithoutASourceRecordWarnOnlyOnWindows
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *makefiles = GSTestMSYS2ToolchainWithSource(nil);
  NSDictionary *windows = [runner bundledAuthoritiesCheckWithMakefiles: makefiles interface: @"full" today: nil windows: YES];
  NSDictionary *other = [runner bundledAuthoritiesCheckWithMakefiles: makefiles interface: @"full" today: nil windows: NO];

  XCTAssertEqualObjects([windows objectForKey: @"status"], @"warning");
  XCTAssertEqualObjects([other objectForKey: @"status"], @"not_run");
  XCTAssertEqualObjects([[other objectForKey: @"details"] objectForKey: @"found"], [NSNumber numberWithBool: YES]);
  GSTestRemoveToolchain(makefiles);
}

- (void)testBundledAuthoritiesCheckIsFullOnlyAndToleratesNoToolchain
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *bootstrap = [runner bundledAuthoritiesCheckWithMakefiles: nil interface: @"bootstrap" today: nil windows: YES];
  NSDictionary *none = [runner bundledAuthoritiesCheckWithMakefiles: nil interface: @"full" today: nil windows: YES];

  XCTAssertEqualObjects([bootstrap objectForKey: @"status"], @"not_run");
  XCTAssertEqualObjects([bootstrap objectForKey: @"execution_tier"], @"full_only");
  XCTAssertEqualObjects([none objectForKey: @"status"], @"not_run");
  XCTAssertEqualObjects([[none objectForKey: @"details"] objectForKey: @"found"], [NSNumber numberWithBool: NO]);
}

- (void)testManagedRootInUseNeedsHealthyStateAndWholeComponentContainment
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *base = [[NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]] stringByResolvingSymlinksInPath];
  NSString *root = nil;
  NSString *state = nil;
  NSString *sibling = nil;
  NSString *repair = nil;

  [manager createDirectoryAtPath: base withIntermediateDirectories: YES attributes: nil error: NULL];
  base = [base stringByResolvingSymlinksInPath];
  root = GSTestManagedRoot(base, @"managed", @"healthy");
  state = [root stringByAppendingPathComponent: @"state/cli-state.json"];

  XCTAssertEqualObjects([runner managedRootInUseForToolchainMakefiles: [root stringByAppendingPathComponent: @"System/Library/Makefiles"] statePath: state], root);

  sibling = [base stringByAppendingPathComponent: @"managed-other/System/Library/Makefiles"];
  [manager createDirectoryAtPath: sibling withIntermediateDirectories: YES attributes: nil error: NULL];
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: sibling statePath: state]);
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: @"/usr/share/GNUstep/Makefiles" statePath: state]);
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: root statePath: state]);
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: nil statePath: state]);

#if !defined(_WIN32) && !defined(__MINGW32__) && !defined(__MINGW64__)
  [manager createSymbolicLinkAtPath: [base stringByAppendingPathComponent: @"link-in"]
                withDestinationPath: [root stringByAppendingPathComponent: @"System"] error: NULL];
  XCTAssertEqualObjects([runner managedRootInUseForToolchainMakefiles: [base stringByAppendingPathComponent: @"link-in/Library/Makefiles"] statePath: state], root);
  [manager createSymbolicLinkAtPath: [root stringByAppendingPathComponent: @"System/Library/LinkedMakefiles"]
                withDestinationPath: [base stringByAppendingPathComponent: @"managed-other/System/Library/Makefiles"] error: NULL];
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: [root stringByAppendingPathComponent: @"System/Library/LinkedMakefiles"] statePath: state]);
#endif

  repair = GSTestManagedRoot(base, @"repair", @"needs_repair");
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: [repair stringByAppendingPathComponent: @"System/Library/Makefiles"]
                                                   statePath: [repair stringByAppendingPathComponent: @"state/cli-state.json"]]);
  [@"{not json" writeToFile: state atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: [root stringByAppendingPathComponent: @"System/Library/Makefiles"] statePath: state]);
  XCTAssertNil([runner managedRootInUseForToolchainMakefiles: [root stringByAppendingPathComponent: @"System/Library/Makefiles"]
                                                   statePath: [base stringByAppendingPathComponent: @"absent.json"]]);
  [manager removeItemAtPath: base error: NULL];
}


// Real installs run <root>/current -> <root>/releases/<version>; the state lives at
// <root>/state, so doctor must map a release directory back to its install root.
- (void)testVersionedInstallRootMapsReleaseDirectoryToInstallRoot
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];

  XCTAssertEqualObjects([runner versionedInstallRootForReleaseRoot: @"/home/u/.local/share/gnustep-cli/releases/0.1.7"],
                        @"/home/u/.local/share/gnustep-cli");
  XCTAssertNil([runner versionedInstallRootForReleaseRoot: @"/home/u/.local/share/gnustep-cli"]);
  XCTAssertNil([runner versionedInstallRootForReleaseRoot: @"/opt/other/0.1.7"]);
  XCTAssertNil([runner versionedInstallRootForReleaseRoot: @""]);
  XCTAssertNil([runner versionedInstallRootForReleaseRoot: nil]);
}

@end
