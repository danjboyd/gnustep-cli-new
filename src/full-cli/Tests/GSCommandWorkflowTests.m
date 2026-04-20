#import <XCTest/XCTest.h>
#import <sys/stat.h>
#import <unistd.h>

#import "../GSCommandContext.h"
#import "../GSCommandRunner.h"

@interface GSCommandRunner (WorkflowTesting)
- (NSString *)resolvedArtifactPathFromURLString:(NSString *)urlString;
- (NSDictionary *)buildDoctorPayloadWithInterface:(NSString *)interface manifestPath:(NSString *)manifestPath;
- (NSDictionary *)buildSetupPayloadForScope:(NSString *)scope
                                   manifest:(NSString *)manifestPath
                                installRoot:(NSString *)installRoot
                                    execute:(BOOL)execute
                                   exitCode:(int *)exitCode;
- (NSDictionary *)executeSetupForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeUpdateForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)buildUpdatePlanForScope:(NSString *)scope manifest:(NSString *)manifestPath installRoot:(NSString *)installRoot exitCode:(int *)exitCode;
- (NSDictionary *)installedLifecycleStateForInstallRoot:(NSString *)installRoot;
- (NSDictionary *)executeInstallForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeRemoveForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSString *)resolvedExecutablePathForCommand:(NSString *)command;
- (NSDictionary *)currentEnvironmentForInterface:(NSString *)interface;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory;
- (NSString *)sha256ForFile:(NSString *)path;
- (NSString *)setupTransactionStatePathForInstallRoot:(NSString *)installRoot;
- (void)recoverSetupTransactionForInstallRoot:(NSString *)installRoot;
- (BOOL)writeJSONStringObject:(id)object toPath:(NSString *)path error:(NSString **)errorMessage;
- (NSString *)renderHumanForPayload:(NSDictionary *)payload;
- (BOOL)installManagedLauncherForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage;
- (NSString *)materializeVersionedReleaseForInstallRoot:(NSString *)installRoot version:(NSString *)version error:(NSString **)errorMessage;
@end

@interface StubbedGSCommandRunner : GSCommandRunner
{
  NSDictionary *_stubDoctorPayload;
}
- (void)setStubDoctorPayload:(NSDictionary *)payload;
@end

@implementation StubbedGSCommandRunner

- (void)dealloc
{
  [_stubDoctorPayload release];
  [super dealloc];
}

- (void)setStubDoctorPayload:(NSDictionary *)payload
{
  [_stubDoctorPayload release];
  _stubDoctorPayload = [payload copy];
}

- (NSDictionary *)buildDoctorPayloadWithInterface:(NSString *)interface manifestPath:(NSString *)manifestPath
{
  if (_stubDoctorPayload != nil)
    {
      return _stubDoctorPayload;
    }
  return [super buildDoctorPayloadWithInterface: interface manifestPath: manifestPath];
}

- (NSDictionary *)currentEnvironmentForInterface:(NSString *)interface
{
  if (_stubDoctorPayload != nil)
    {
      return [_stubDoctorPayload objectForKey: @"environment"];
    }
  return [super currentEnvironmentForInterface: interface];
}

@end

@interface GSCommandWorkflowTests : XCTestCase
@end

@implementation GSCommandWorkflowTests

- (NSString *)temporaryPathComponent:(NSString *)name
{
  NSString *identifier = [[NSProcessInfo processInfo] globallyUniqueString];
  NSString *path = [[NSTemporaryDirectory() stringByAppendingPathComponent: @"gnustep-cli-xctest"] stringByAppendingPathComponent: identifier];
  return [path stringByAppendingPathComponent: name];
}

- (void)ensureDirectory:(NSString *)path
{
  [[NSFileManager defaultManager] createDirectoryAtPath: path
                            withIntermediateDirectories: YES
                                             attributes: nil
                                                  error: NULL];
}

- (void)writeJSONStringObject:(id)object toPath:(NSString *)path
{
  NSData *data = [NSJSONSerialization dataWithJSONObject: object options: NSJSONWritingPrettyPrinted error: NULL];
  [self ensureDirectory: [path stringByDeletingLastPathComponent]];
  [data writeToFile: path atomically: YES];
}

- (NSString *)archiveDirectory:(NSString *)directory toTarball:(NSString *)archivePath withRunner:(GSCommandRunner *)runner
{
  NSDictionary *result = [runner runCommand: [NSArray arrayWithObjects:
                                                        @"tar",
                                                        @"-czf",
                                                        archivePath,
                                                        @"-C",
                                                        directory,
                                                        @".",
                                                        nil]
                           currentDirectory: nil];
  XCTAssertTrue([[result objectForKey: @"launched"] boolValue]);
  XCTAssertEqual([[result objectForKey: @"exit_status"] intValue], 0);
  return archivePath;
}

- (NSDictionary *)stubDoctorPayload
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"doctor", @"command",
                        @"0.1.0-dev", @"cli_version",
                        @"full", @"interface",
                        @"full", @"diagnostic_depth",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"toolchain_compatible", @"environment_classification",
                        @"supported", @"native_toolchain_assessment",
                        @"Detected a compatible Clang toolchain.", @"summary",
                        [NSDictionary dictionaryWithObjectsAndKeys:
                                        @"linux", @"os",
                                        @"amd64", @"arch",
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                      [NSNumber numberWithBool: YES], @"curl",
                                                      [NSNumber numberWithBool: NO], @"wget",
                                                      nil], @"bootstrap_prerequisites",
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                      [NSNumber numberWithBool: YES], @"present",
                                                      @"clang", @"compiler_family",
                                                      @"clang", @"toolchain_flavor",
                                                      @"libobjc2", @"objc_runtime",
                                                      @"modern", @"objc_abi",
                                                      [NSNumber numberWithBool: YES], @"can_compile",
                                                      [NSNumber numberWithBool: YES], @"can_link",
                                                      [NSNumber numberWithBool: YES], @"can_run",
                                                      [NSDictionary dictionaryWithObjectsAndKeys:
                                                                    [NSNumber numberWithBool: YES], @"blocks",
                                                                    [NSNumber numberWithBool: YES], @"arc",
                                                                    nil], @"feature_flags",
                                                      @"full", @"detection_depth",
                                                      nil], @"toolchain",
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                      @"supported", @"assessment",
                                                      @"native", @"preference",
                                                      @"The detected native GNUstep environment satisfies the managed runtime expectations.", @"message",
                                                      [NSArray array], @"reasons",
                                                      nil], @"native_toolchain",
                                        nil], @"environment",
                        [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSNumber numberWithBool: YES], @"compatible",
                                        [NSNull null], @"target_kind",
                                        [NSNull null], @"target_id",
                                        [NSArray array], @"reasons",
                                        [NSArray array], @"warnings",
                                        nil], @"compatibility",
                        [NSArray array], @"checks",
                        [NSArray array], @"actions",
                        nil];
}

- (NSDictionary *)stubManagedDoctorPayload
{
  NSMutableDictionary *payload = [[self stubDoctorPayload] mutableCopy];
  NSMutableDictionary *environment = [[[payload objectForKey: @"environment"] mutableCopy] autorelease];

  [environment setObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"unavailable", @"assessment",
                                         @"managed", @"preference",
                                         @"No supported native GNUstep environment was selected for this test.", @"message",
                                         [NSArray array], @"reasons",
                                         nil]
                  forKey: @"native_toolchain"];
  [payload setObject: @"unavailable" forKey: @"native_toolchain_assessment"];
  [payload setObject: environment forKey: @"environment"];
  return [payload autorelease];
}

- (NSString *)releaseManifestPathInDirectory:(NSString *)root
                                  cliSHA256:(NSString *)cliSHA256
                            toolchainSHA256:(NSString *)toolchainSHA256
                                     cliURL:(NSString *)cliURL
                               toolchainURL:(NSString *)toolchainURL
{
  NSString *manifestPath = [root stringByAppendingPathComponent: @"release-manifest.json"];
  NSDictionary *manifest = [NSDictionary dictionaryWithObjectsAndKeys:
                                           [NSNumber numberWithInt: 1], @"schema_version",
                                           [NSNumber numberWithInt: 1], @"metadata_version",
                                           @"2026-04-20T00:00:00Z", @"generated_at",
                                           @"2099-01-01T00:00:00Z", @"expires_at",
                                           [NSArray arrayWithObject:
                                                      [NSDictionary dictionaryWithObjectsAndKeys:
                                                                     @"0.1.0-test", @"version",
                                                                     @"active", @"status",
                                                                     [NSArray arrayWithObjects:
                                                                                [NSDictionary dictionaryWithObjectsAndKeys:
                                                                                               @"cli-linux-amd64-clang", @"id",
                                                                                               @"cli", @"kind",
                                                                                               @"linux", @"os",
                                                                                               @"amd64", @"arch",
                                                                                               @"clang", @"compiler_family",
                                                                                               @"clang", @"toolchain_flavor",
                                                                                               @"libobjc2", @"objc_runtime",
                                                                                               @"modern", @"objc_abi",
                                                                                               [NSArray array], @"required_features",
                                                                                               cliURL, @"url",
                                                                                               cliSHA256, @"sha256",
                                                                                               nil],
                                                                                [NSDictionary dictionaryWithObjectsAndKeys:
                                                                                               @"toolchain-linux-amd64-clang", @"id",
                                                                                               @"toolchain", @"kind",
                                                                                               @"linux", @"os",
                                                                                               @"amd64", @"arch",
                                                                                               @"clang", @"compiler_family",
                                                                                               @"clang", @"toolchain_flavor",
                                                                                               @"libobjc2", @"objc_runtime",
                                                                                               @"modern", @"objc_abi",
                                                                                               [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                                               toolchainURL, @"url",
                                                                                               toolchainSHA256, @"sha256",
                                                                                               nil],
                                                                                nil], @"artifacts",
                                                                     nil]], @"releases",
                                           nil];
  [self writeJSONStringObject: manifest toPath: manifestPath];
  return manifestPath;
}


- (void)testFullDoctorProbeCheckCarriesStructuredEvidence
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *payload = [runner buildDoctorPayloadWithInterface: @"full" manifestPath: nil];
  NSArray *checks = [payload objectForKey: @"checks"];
  NSDictionary *probeCheck = nil;
  NSUInteger i = 0;

  for (i = 0; i < [checks count]; i++)
    {
      NSDictionary *check = [checks objectAtIndex: i];
      if ([[check objectForKey: @"id"] isEqualToString: @"toolchain.probe"])
        {
          probeCheck = check;
          break;
        }
    }
  XCTAssertNotNil(probeCheck);
  XCTAssertNotNil([[payload objectForKey: @"environment"] objectForKey: @"toolchain"]);
  XCTAssertNotNil([probeCheck objectForKey: @"details"]);
  XCTAssertNotNil([[probeCheck objectForKey: @"details"] objectForKey: @"can_compile"]);
  XCTAssertNotNil([[probeCheck objectForKey: @"details"] objectForKey: @"can_link"]);
  XCTAssertNotNil([[probeCheck objectForKey: @"details"] objectForKey: @"can_run"]);
}

- (void)testFullDoctorPayloadExposesDetectionDepthAndNativeAssessment
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSDictionary *payload = nil;
  NSDictionary *environment = nil;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  payload = [runner buildDoctorPayloadWithInterface: @"full" manifestPath: nil];
  environment = [payload objectForKey: @"environment"];

  XCTAssertEqualObjects([payload objectForKey: @"interface"], @"full");
  XCTAssertEqualObjects([payload objectForKey: @"diagnostic_depth"], @"full");
  XCTAssertEqualObjects([payload objectForKey: @"native_toolchain_assessment"], @"supported");
  XCTAssertEqualObjects([[environment objectForKey: @"toolchain"] objectForKey: @"detection_depth"], @"full");
  XCTAssertNotNil([environment objectForKey: @"native_toolchain"]);
}

- (void)testDoctorPayloadKeepsBootstrapCheckVocabularyVisible
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *payload = [runner buildDoctorPayloadWithInterface: @"bootstrap" manifestPath: nil];
  NSMutableDictionary *checks = [NSMutableDictionary dictionary];
  NSUInteger i = 0;

  for (i = 0; i < [[payload objectForKey: @"checks"] count]; i++)
    {
      NSDictionary *check = [[payload objectForKey: @"checks"] objectAtIndex: i];
      [checks setObject: check forKey: [check objectForKey: @"id"]];
    }

  XCTAssertEqualObjects([payload objectForKey: @"command"], @"doctor");
  XCTAssertEqualObjects([payload objectForKey: @"interface"], @"bootstrap");
  XCTAssertEqualObjects([payload objectForKey: @"diagnostic_depth"], @"installer");
  XCTAssertEqualObjects([[checks objectForKey: @"toolchain.probe"] objectForKey: @"status"], @"not_run");
  XCTAssertEqualObjects([[checks objectForKey: @"managed.install.integrity"] objectForKey: @"status"], @"not_run");
  XCTAssertNotNil([checks objectForKey: @"native-toolchain.assess"]);
}


- (void)testDoctorBootstrapAndFullShareCoreCheckIdentifiers
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *bootstrapPayload = [runner buildDoctorPayloadWithInterface: @"bootstrap" manifestPath: nil];
  NSDictionary *fullPayload = [runner buildDoctorPayloadWithInterface: @"full" manifestPath: nil];
  NSMutableSet *bootstrapIDs = [NSMutableSet set];
  NSMutableSet *fullIDs = [NSMutableSet set];
  NSArray *requiredIDs = [NSArray arrayWithObjects:
                                  @"host.identity",
                                  @"bootstrap.downloader",
                                  @"toolchain.detect",
                                  @"native-toolchain.assess",
                                  @"toolchain.probe",
                                  @"managed.install.integrity",
                                  @"toolchain.compatibility",
                                  nil];
  NSUInteger i = 0;

  for (i = 0; i < [[bootstrapPayload objectForKey: @"checks"] count]; i++)
    {
      [bootstrapIDs addObject: [[[bootstrapPayload objectForKey: @"checks"] objectAtIndex: i] objectForKey: @"id"]];
    }
  for (i = 0; i < [[fullPayload objectForKey: @"checks"] count]; i++)
    {
      [fullIDs addObject: [[[fullPayload objectForKey: @"checks"] objectAtIndex: i] objectForKey: @"id"]];
    }
  for (i = 0; i < [requiredIDs count]; i++)
    {
      XCTAssertTrue([bootstrapIDs containsObject: [requiredIDs objectAtIndex: i]]);
      XCTAssertTrue([fullIDs containsObject: [requiredIDs objectAtIndex: i]]);
    }
  XCTAssertEqualObjects([bootstrapPayload objectForKey: @"diagnostic_depth"], @"installer");
  XCTAssertEqualObjects([fullPayload objectForKey: @"diagnostic_depth"], @"full");
}

- (void)testSetupPlanUsesNativeToolchainEvenWhenRootIsProvided
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *root = [self temporaryPathComponent: @"setup-native-root"];
  NSString *installRoot = [root stringByAppendingPathComponent: @"explicit-root"];
  NSString *manifestPath = [self releaseManifestPathInDirectory: root
                                                     cliSHA256: @"deadbeef"
                                               toolchainSHA256: @"deadbeef"
                                                        cliURL: @"https://example.invalid/cli.tar.gz"
                                                  toolchainURL: @"https://example.invalid/toolchain.tar.gz"];
  int exitCode = 0;
  NSDictionary *payload = nil;

  [self ensureDirectory: root];
  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  payload = [runner buildSetupPayloadForScope: @"user"
                                     manifest: manifestPath
                                  installRoot: installRoot
                                      execute: NO
                                     exitCode: &exitCode];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([[payload objectForKey: @"plan"] objectForKey: @"install_mode"], @"native");
  XCTAssertEqualObjects([[payload objectForKey: @"plan"] objectForKey: @"disposition"], @"use_existing_toolchain");
}

- (void)testSetupPlanUsesExistingNativeToolchainWhenSupported
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *root = [self temporaryPathComponent: @"setup-native"];
  NSString *manifestPath = [self releaseManifestPathInDirectory: root
                                                     cliSHA256: @"deadbeef"
                                               toolchainSHA256: @"deadbeef"
                                                        cliURL: @"https://example.invalid/cli.tar.gz"
                                                  toolchainURL: @"https://example.invalid/toolchain.tar.gz"];
  int exitCode = 0;
  NSDictionary *payload = nil;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  payload = [runner buildSetupPayloadForScope: @"user"
                                     manifest: manifestPath
                                  installRoot: nil
                                      execute: NO
                                     exitCode: &exitCode];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([[payload objectForKey: @"plan"] objectForKey: @"install_mode"], @"native");
  XCTAssertEqualObjects([[payload objectForKey: @"plan"] objectForKey: @"disposition"], @"use_existing_toolchain");
}

- (void)testResolvedArtifactPathKeepsWindowsFileURLUsable
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *resolved = [runner resolvedArtifactPathFromURLString: @"file:///C:/Users/test/payload.zip"];

  XCTAssertNotNil(resolved);
#if defined(_WIN32)
  XCTAssertEqualObjects(resolved, @"C:\\Users\\test\\payload.zip");
#else
  XCTAssertTrue([resolved length] > 0);
#endif
}

- (void)testRunCommandReportsMissingExecutableCleanly
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSDictionary *result = [runner runCommand: [NSArray arrayWithObjects: @"definitely-not-a-real-command-gnustep-cli", nil]
                           currentDirectory: nil];

  XCTAssertFalse([[result objectForKey: @"launched"] boolValue]);
  XCTAssertEqual([[result objectForKey: @"exit_status"] intValue], 1);
  XCTAssertTrue([[[result objectForKey: @"stderr"] lowercaseString] rangeOfString: @"executable not found"].location != NSNotFound);
}

- (void)testResolvedExecutablePathFindsTarOnCurrentPath
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *resolved = [runner resolvedExecutablePathForCommand: @"tar"];

  XCTAssertNotNil(resolved);
  XCTAssertTrue([[resolved lastPathComponent] rangeOfString: @"tar"].location != NSNotFound);
}

- (void)testInstallFailsGracefullyWhenArtifactURLCannotResolve
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"install-invalid-url"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         @"stable", @"channel",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.example.invalid", @"id",
                                                   @"Invalid URL", @"name",
                                                   @"1.0.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"Broken package fixture.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray array], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray array], @"dependencies",
                                                   [NSArray arrayWithObject:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"invalid-linux-clang", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray array], @"required_features",
                                                                             @"file://", @"url",
                                                                             nil]], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"install",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         @"org.example.invalid",
                                         nil]];
  payload = [runner executeInstallForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Selected package artifact URL could not be resolved to a local path.");
}



- (void)testSetupCheckUpdatesReportsAvailableReleaseWithoutMutation
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-check-updates"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *plan = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"0.0.9", @"toolchain_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--check-updates",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];
  plan = [payload objectForKey: @"update_plan"];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"operation"], @"check_updates");
  XCTAssertTrue([[plan objectForKey: @"update_available"] boolValue]);
  XCTAssertEqualObjects([plan objectForKey: @"installed_version"], @"0.0.9");
  XCTAssertEqualObjects([plan objectForKey: @"latest_compatible_version"], @"0.1.0-test");
}

- (void)testUpdateCliCheckUsesCanonicalUpdateCommand
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"update-cli-check"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *plan = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"0.0.9", @"toolchain_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"cli",
                                         @"--check",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];
  plan = [[payload objectForKey: @"plan"] objectForKey: @"cli"];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"command"], @"update");
  XCTAssertEqualObjects([payload objectForKey: @"scope"], @"cli");
  XCTAssertEqualObjects([payload objectForKey: @"mode"], @"check");
  XCTAssertTrue([[plan objectForKey: @"update_available"] boolValue]);
}


- (NSMutableDictionary *)mutableJSONDictionaryAtPath:(NSString *)path
{
  NSData *data = [NSData dataWithContentsOfFile: path];
  NSDictionary *payload = [NSJSONSerialization JSONObjectWithData: data options: 0 error: NULL];
  return [[payload mutableCopy] autorelease];
}

- (void)testSetupCheckUpdatesRejectsDowngradeManifest
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-check-updates-downgrade"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *plan = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"9.0.0", @"cli_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];
  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--check-updates",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];
  plan = [payload objectForKey: @"update_plan"];

  XCTAssertEqual(exitCode, 3);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"The selected release manifest is older than the installed CLI.");
  XCTAssertTrue([[plan objectForKey: @"downgrade_detected"] boolValue]);
  XCTAssertFalse([[plan objectForKey: @"update_available"] boolValue]);
}

- (void)testSetupCheckUpdatesRejectsExpiredReleaseMetadata
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-check-updates-expired"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  NSMutableDictionary *manifest = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];
  manifest = [self mutableJSONDictionaryAtPath: manifestPath];
  [manifest setObject: [NSNumber numberWithInt: 1] forKey: @"metadata_version"];
  [manifest setObject: @"2000-01-01T00:00:00Z" forKey: @"expires_at"];
  [self writeJSONStringObject: manifest toPath: manifestPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--check-updates",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 3);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([[[payload objectForKey: @"update_plan"] objectForKey: @"selection_errors"] objectAtIndex: 0], @"Release manifest metadata is expired.");
}


- (void)testSetupCheckUpdatesRejectsFrozenManifestMetadata
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-check-updates-freeze"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  NSMutableDictionary *manifest = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSArray *errors = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"healthy", @"status",
                                               [NSNumber numberWithInt: 2], @"last_manifest_metadata_version",
                                               @"2026-04-20T00:00:00Z", @"last_manifest_generated_at",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];
  manifest = [self mutableJSONDictionaryAtPath: manifestPath];
  [manifest setObject: [NSNumber numberWithInt: 2] forKey: @"metadata_version"];
  [manifest setObject: @"2026-04-19T00:00:00Z" forKey: @"generated_at"];
  [self writeJSONStringObject: manifest toPath: manifestPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--check-updates",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];
  errors = [[payload objectForKey: @"update_plan"] objectForKey: @"selection_errors"];

  XCTAssertEqual(exitCode, 3);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertTrue([[errors objectAtIndex: 0] rangeOfString: @"older than the last accepted manifest"].location != NSNotFound);
}

- (void)testSetupCheckUpdatesRejectsRevokedSelectedArtifact
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-check-updates-revoked"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  NSMutableDictionary *manifest = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSArray *errors = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];
  manifest = [self mutableJSONDictionaryAtPath: manifestPath];
  [manifest setObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                      [NSArray arrayWithObject: @"cli-linux-amd64-clang"], @"revoked_artifacts",
                                      nil]
                 forKey: @"trust"];
  [self writeJSONStringObject: manifest toPath: manifestPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--check-updates",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];
  errors = [[payload objectForKey: @"update_plan"] objectForKey: @"selection_errors"];

  XCTAssertEqual(exitCode, 3);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertTrue([[errors objectAtIndex: 0] rangeOfString: @"revoked artifact"].location != NSNotFound);
}

- (void)testSetupUpgradeRejectsNeedsRepairState
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-upgrade-needs-repair"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"needs_repair", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];
  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--upgrade",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 3);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Managed install state requires repair before upgrade.");
}

- (void)testSetupUpgradePreservesPreviousReleaseState
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-upgrade-preserve"];
  NSString *payloadRoot = [tempRoot stringByAppendingPathComponent: @"payloads"];
  NSString *cliDir = [payloadRoot stringByAppendingPathComponent: @"cli"];
  NSString *toolchainDir = [payloadRoot stringByAppendingPathComponent: @"toolchain"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *cliArchive = [payloadRoot stringByAppendingPathComponent: @"cli.tar.gz"];
  NSString *toolchainArchive = [payloadRoot stringByAppendingPathComponent: @"toolchain.tar.gz"];
  NSString *oldSentinel = [installRoot stringByAppendingPathComponent: @"old.txt"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *state = nil;
  NSString *previous = nil;
  NSString *active = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self ensureDirectory: [cliDir stringByAppendingPathComponent: @"bin"]];
  [self ensureDirectory: [toolchainDir stringByAppendingPathComponent: @"System/Tools"]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [@"old" writeToFile: oldSentinel atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  [@"#!/bin/sh\nexit 0\n" writeToFile: [cliDir stringByAppendingPathComponent: @"bin/gnustep"] atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [self archiveDirectory: cliDir toTarball: cliArchive withRunner: runner];
  [self archiveDirectory: toolchainDir toTarball: toolchainArchive withRunner: runner];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: [runner sha256ForFile: cliArchive]
                                     toolchainSHA256: [runner sha256ForFile: toolchainArchive]
                                              cliURL: cliArchive
                                        toolchainURL: toolchainArchive];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--upgrade",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];
  state = [runner installedLifecycleStateForInstallRoot: installRoot];
  previous = [state objectForKey: @"previous_release_path"];
  active = [state objectForKey: @"active_release_path"];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"operation"], @"upgrade");
  XCTAssertEqualObjects([state objectForKey: @"last_action"], @"upgrade");
  XCTAssertEqualObjects([state objectForKey: @"cli_version"], @"0.1.0-test");
  XCTAssertTrue([previous isKindOfClass: [NSString class]]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [previous stringByAppendingPathComponent: @"old.txt"]]);
  XCTAssertEqualObjects(active, [[installRoot stringByAppendingPathComponent: @"releases"] stringByAppendingPathComponent: @"0.1.0-test"]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [active stringByAppendingPathComponent: @"bin/gnustep"]]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [installRoot stringByAppendingPathComponent: @"current"]]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [installRoot stringByAppendingPathComponent: @"bin/gnustep"]]);
  XCTAssertTrue([[NSString stringWithContentsOfFile: [installRoot stringByAppendingPathComponent: @"bin/gnustep"] encoding: NSUTF8StringEncoding error: NULL] rangeOfString: @"$ROOT/current/bin/gnustep"].location != NSNotFound);
}





- (void)testUpdateCliYesUsesCanonicalCommandAndPreservesPreviousReleaseState
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"update-cli-apply"];
  NSString *payloadRoot = [tempRoot stringByAppendingPathComponent: @"payloads"];
  NSString *cliDir = [payloadRoot stringByAppendingPathComponent: @"cli"];
  NSString *toolchainDir = [payloadRoot stringByAppendingPathComponent: @"toolchain"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *cliArchive = [payloadRoot stringByAppendingPathComponent: @"cli.tar.gz"];
  NSString *toolchainArchive = [payloadRoot stringByAppendingPathComponent: @"toolchain.tar.gz"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *state = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self ensureDirectory: [cliDir stringByAppendingPathComponent: @"bin"]];
  [self ensureDirectory: [toolchainDir stringByAppendingPathComponent: @"System/Tools"]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  [@"#!/bin/sh\nexit 0\n" writeToFile: [cliDir stringByAppendingPathComponent: @"bin/gnustep"] atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [@"toolchain" writeToFile: [toolchainDir stringByAppendingPathComponent: @"System/Tools/make"] atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [self archiveDirectory: cliDir toTarball: cliArchive withRunner: runner];
  [self archiveDirectory: toolchainDir toTarball: toolchainArchive withRunner: runner];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: [runner sha256ForFile: cliArchive]
                                     toolchainSHA256: [runner sha256ForFile: toolchainArchive]
                                              cliURL: cliArchive
                                        toolchainURL: toolchainArchive];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"cli",
                                         @"--yes",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];
  state = [runner installedLifecycleStateForInstallRoot: installRoot];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"command"], @"update");
  XCTAssertEqualObjects([payload objectForKey: @"scope"], @"cli");
  XCTAssertEqualObjects([payload objectForKey: @"mode"], @"apply");
  XCTAssertEqualObjects([payload objectForKey: @"operation"], @"update_cli");
  XCTAssertEqualObjects([state objectForKey: @"last_action"], @"upgrade");
  XCTAssertTrue([[[payload objectForKey: @"install"] objectForKey: @"path_hint"] rangeOfString: @"export PATH"].location != NSNotFound);
  XCTAssertEqualObjects([state objectForKey: @"active_release"], @"0.1.0-test");
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [state objectForKey: @"active_release_path"]]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [state objectForKey: @"previous_release_path"]]);
}

- (void)testSetupVersionedActivationRejectsFailedSmokeValidation
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [self temporaryPathComponent: @"setup-smoke-failure"];
  NSString *launcher = [root stringByAppendingPathComponent: @"bin/gnustep"];
  NSString *error = nil;
  NSString *releaseRoot = nil;

  [self ensureDirectory: [launcher stringByDeletingLastPathComponent]];
  [@"#!/bin/sh\nexit 42\n" writeToFile: launcher atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  chmod([launcher fileSystemRepresentation], 0755);

  releaseRoot = [runner materializeVersionedReleaseForInstallRoot: root version: @"0.1.2" error: &error];

  XCTAssertNil(releaseRoot);
  XCTAssertEqualObjects(error, @"Candidate release failed post-upgrade smoke validation.");
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: [root stringByAppendingPathComponent: @"current"]]);
}

- (void)testInstallManagedLauncherDoesNotDoubleWrapRuntimeBundle
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [self temporaryPathComponent: @"setup-launcher-runtime-bundle"];
  NSString *binLauncher = [root stringByAppendingPathComponent: @"bin/gnustep"];
  NSString *runtimeBinary = [root stringByAppendingPathComponent: @"libexec/gnustep-cli/bin/gnustep"];
  NSString *realPath = [root stringByAppendingPathComponent: @"libexec/gnustep-cli/bin/gnustep-real"];
  NSString *error = nil;

  [self ensureDirectory: [binLauncher stringByDeletingLastPathComponent]];
  [self ensureDirectory: [runtimeBinary stringByDeletingLastPathComponent]];
  [@"#!/bin/sh\nexec \"$(dirname \"$0\")/../libexec/gnustep-cli/bin/gnustep\" \"$@\"\n" writeToFile: binLauncher atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [@"runtime" writeToFile: runtimeBinary atomically: YES encoding: NSUTF8StringEncoding error: NULL];

  XCTAssertTrue([runner installManagedLauncherForInstallRoot: root error: &error]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: binLauncher]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: runtimeBinary]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: realPath]);
}


- (void)testSetupRollbackRestoresPreviousManagedRoot
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-rollback-command"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *backupRoot = [tempRoot stringByAppendingPathComponent: @"managed-backup"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *backupStatePath = [[backupRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *state = nil;
  int exitCode = 0;

  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self ensureDirectory: [backupStatePath stringByDeletingLastPathComponent]];
  [@"new" writeToFile: [installRoot stringByAppendingPathComponent: @"new.txt"] atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [@"old" writeToFile: [backupRoot stringByAppendingPathComponent: @"old.txt"] atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.1.2", @"cli_version",
                                               backupRoot, @"previous_release_path",
                                               @"upgrade", @"last_action",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.1.1", @"cli_version",
                                               @"setup", @"last_action",
                                               @"healthy", @"status",
                                               nil]
                       toPath: backupStatePath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--rollback",
                                         @"--root",
                                         installRoot,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];
  state = [runner installedLifecycleStateForInstallRoot: installRoot];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"operation"], @"rollback");
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: [installRoot stringByAppendingPathComponent: @"old.txt"]]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: [installRoot stringByAppendingPathComponent: @"new.txt"]]);
  XCTAssertEqualObjects([state objectForKey: @"last_action"], @"rollback");
  XCTAssertEqualObjects([state objectForKey: @"status"], @"healthy");
}

- (void)testSetupRepairClearsStaleStateAndMarksInterruptedLifecycle
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *root = [self temporaryPathComponent: @"setup-repair-root"];
  NSString *stateDir = [root stringByAppendingPathComponent: @"state"];
  NSString *statePath = [stateDir stringByAppendingPathComponent: @"cli-state.json"];
  NSString *staging = [root stringByAppendingPathComponent: @".staging/payload"];
  NSString *transactions = [root stringByAppendingPathComponent: @".transactions/upgrade"];
  NSString *setupTransaction = [stateDir stringByAppendingPathComponent: @"setup-transaction.json"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSMutableSet *repairKinds = [NSMutableSet set];
  NSUInteger i = 0;
  int exitCode = 0;

  [self ensureDirectory: staging];
  [self ensureDirectory: transactions];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"upgrading", @"status",
                                               nil]
                       toPath: statePath];
  [self writeJSONStringObject: [NSDictionary dictionary] toPath: setupTransaction];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects: @"setup", @"--repair", @"--root", root, nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  for (i = 0; i < [[payload objectForKey: @"repairs"] count]; i++)
    {
      [repairKinds addObject: [[[payload objectForKey: @"repairs"] objectAtIndex: i] objectForKey: @"kind"]];
    }
  XCTAssertTrue([repairKinds containsObject: @"clear_staging"]);
  XCTAssertTrue([repairKinds containsObject: @"clear_transactions"]);
  XCTAssertTrue([repairKinds containsObject: @"clear_setup_transaction"]);
  XCTAssertTrue([repairKinds containsObject: @"mark_needs_repair"]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: [root stringByAppendingPathComponent: @".staging"]]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: [root stringByAppendingPathComponent: @".transactions"]]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: setupTransaction]);
}


- (void)testRecoverSetupTransactionRestoresBackupAndRemovesTransactionState
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-recover"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *backupRoot = [tempRoot stringByAppendingPathComponent: @"managed-backup"];
  NSString *statePath = [runner setupTransactionStatePathForInstallRoot: installRoot];
  NSString *transactionRoot = [[statePath stringByDeletingLastPathComponent] stringByDeletingLastPathComponent];
  NSString *restoredSentinel = [installRoot stringByAppendingPathComponent: @"restored.txt"];
  NSString *partialSentinel = [installRoot stringByAppendingPathComponent: @"partial.txt"];
  NSDictionary *transaction = nil;

  [self ensureDirectory: installRoot];
  [self ensureDirectory: backupRoot];
  [@"partial" writeToFile: partialSentinel atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [@"restored" writeToFile: [backupRoot stringByAppendingPathComponent: @"restored.txt"]
               atomically: YES
                 encoding: NSUTF8StringEncoding
                    error: NULL];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  transaction = [NSDictionary dictionaryWithObjectsAndKeys:
                                  [NSNumber numberWithInt: 1], @"schema_version",
                                  @"in_progress", @"status",
                                  installRoot, @"install_root",
                                  backupRoot, @"backup_root",
                                  nil];
  [runner writeJSONStringObject: transaction toPath: statePath error: NULL];

  [runner recoverSetupTransactionForInstallRoot: installRoot];

  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: restoredSentinel]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: partialSentinel]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: backupRoot]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: transactionRoot]);
}

- (void)testExecuteSetupRollsBackExistingInstallOnChecksumMismatch
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"setup-rollback"];
  NSString *payloadRoot = [tempRoot stringByAppendingPathComponent: @"payloads"];
  NSString *cliDir = [payloadRoot stringByAppendingPathComponent: @"cli"];
  NSString *toolchainDir = [payloadRoot stringByAppendingPathComponent: @"toolchain"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *cliArchive = [payloadRoot stringByAppendingPathComponent: @"cli.tar.gz"];
  NSString *toolchainArchive = [payloadRoot stringByAppendingPathComponent: @"toolchain.tar.gz"];
  NSString *sentinel = [installRoot stringByAppendingPathComponent: @"existing.txt"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [cliDir stringByAppendingPathComponent: @"bin"]];
  [self ensureDirectory: [toolchainDir stringByAppendingPathComponent: @"System/Tools"]];
  [self ensureDirectory: installRoot];
  [@"old-install" writeToFile: sentinel atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [@"#!/bin/sh\nexit 0\n" writeToFile: [cliDir stringByAppendingPathComponent: @"bin/gnustep"]
                         atomically: YES
                           encoding: NSUTF8StringEncoding
                              error: NULL];
  [@"toolchain" writeToFile: [toolchainDir stringByAppendingPathComponent: @"System/Tools/make"]
                 atomically: YES
                   encoding: NSUTF8StringEncoding
                      error: NULL];

  [self archiveDirectory: cliDir toTarball: cliArchive withRunner: runner];
  [self archiveDirectory: toolchainDir toTarball: toolchainArchive withRunner: runner];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: [runner sha256ForFile: cliArchive]
                                     toolchainSHA256: @"bad-checksum"
                                              cliURL: cliArchive
                                        toolchainURL: toolchainArchive];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"setup",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeSetupForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: sentinel]);
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: [installRoot stringByAppendingPathComponent: @"bin/gnustep"]]);
}

- (void)testInstallFromIndexSelectsCompatibleArtifactAndRecordsState
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"install-index"];
  NSString *payloadDir = [tempRoot stringByAppendingPathComponent: @"artifact-root"];
  NSString *archivePath = [tempRoot stringByAppendingPathComponent: @"tools-xctest.tar.gz"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *manifestFile = [payloadDir stringByAppendingPathComponent: @"bin/xctest"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *state = nil;
  NSArray *recordedFiles = nil;
  NSString *installedFile = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self ensureDirectory: [payloadDir stringByAppendingPathComponent: @"bin"]];
  [@"xctest" writeToFile: manifestFile atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [self archiveDirectory: payloadDir toTarball: archivePath withRunner: runner];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         @"stable", @"channel",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.gnustep.tools-xctest", @"id",
                                                   @"tools-xctest", @"name",
                                                   @"0.1.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"XCTest runner for GNUstep tool development.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray array], @"dependencies",
                                                   [NSArray arrayWithObjects:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"tools-xctest-linux-gcc", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"gcc", @"compiler_family",
                                                                             @"gcc", @"toolchain_flavor",
                                                                             @"gcc_libobjc", @"objc_runtime",
                                                                             @"legacy", @"objc_abi",
                                                                             [NSArray array], @"required_features",
                                                                             @"file:///tmp/missing-tools-xctest.tar.gz", @"url",
                                                                             nil],
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"tools-xctest-linux-clang", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                             [NSString stringWithFormat: @"file://%@", archivePath], @"url",
                                                                             [runner sha256ForFile: archivePath], @"sha256",
                                                                             nil],
                                                              nil], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"install",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         @"org.gnustep.tools-xctest",
                                         nil]];
  payload = [runner executeInstallForContext: context exitCode: &exitCode];
  state = [NSJSONSerialization JSONObjectWithData:
                               [NSData dataWithContentsOfFile: [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"]]
                                         options: 0
                                           error: NULL];
  recordedFiles = [[[state objectForKey: @"packages"] objectForKey: @"org.gnustep.tools-xctest"] objectForKey: @"installed_files"];
  installedFile = [managedRoot stringByAppendingPathComponent: [recordedFiles objectAtIndex: 0]];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"selected_artifact"], @"tools-xctest-linux-clang");
  XCTAssertTrue([recordedFiles count] > 0);
  XCTAssertTrue([[installedFile lastPathComponent] isEqualToString: @"xctest"]);
  XCTAssertTrue([[NSFileManager defaultManager] fileExistsAtPath: installedFile]);
  XCTAssertEqualObjects([[[state objectForKey: @"packages"] objectForKey: @"org.gnustep.tools-xctest"] objectForKey: @"selected_artifact"], @"tools-xctest-linux-clang");
}

- (void)testUpdatePackagesChecksAndAppliesCompatiblePackageUpgrade
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"update-package-upgrade"];
  NSString *payloadDir = [tempRoot stringByAppendingPathComponent: @"artifact-root"];
  NSString *archivePath = [tempRoot stringByAppendingPathComponent: @"tools-xctest-updated.tar.gz"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *installRoot = [managedRoot stringByAppendingPathComponent: @"packages/org.gnustep.tools-xctest"];
  NSString *statePath = [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *state = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self ensureDirectory: [payloadDir stringByAppendingPathComponent: @"bin"]];
  [@"xctest updated" writeToFile: [payloadDir stringByAppendingPathComponent: @"bin/xctest"]
                         atomically: YES
                           encoding: NSUTF8StringEncoding
                              error: NULL];
  [self archiveDirectory: payloadDir toTarball: archivePath withRunner: runner];
  [self ensureDirectory: [installRoot stringByAppendingPathComponent: @"bin"]];
  [@"xctest old" writeToFile: [installRoot stringByAppendingPathComponent: @"bin/xctest"]
                    atomically: YES
                      encoding: NSUTF8StringEncoding
                         error: NULL];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       installRoot, @"install_root",
                                                       @"0.1.0", @"version",
                                                       indexPath, @"index_path",
                                                       @"tools-xctest-linux-clang-old", @"selected_artifact",
                                                       [NSArray array], @"dependencies",
                                                       [NSArray array], @"conflicts",
                                                       [NSArray arrayWithObject: @"packages/org.gnustep.tools-xctest/bin/xctest"], @"installed_files",
                                                       nil], @"org.gnustep.tools-xctest",
                                        nil], @"packages",
                         nil]
                 toPath: statePath];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         @"stable", @"channel",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.gnustep.tools-xctest", @"id",
                                                   @"tools-xctest", @"name",
                                                   @"0.2.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"XCTest runner update.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray array], @"dependencies",
                                                   [NSArray array], @"conflicts",
                                                   [NSArray arrayWithObject:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"tools-xctest-linux-clang-new", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                             [NSString stringWithFormat: @"file://%@", archivePath], @"url",
                                                                             [runner sha256ForFile: archivePath], @"sha256",
                                                                             nil]], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"packages",
                                         @"--check",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];
  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertTrue([[[[payload objectForKey: @"package_updates"] objectAtIndex: 0] objectForKey: @"update_available"] boolValue]);

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"packages",
                                         @"--yes",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];
  state = [NSJSONSerialization JSONObjectWithData:
                               [NSData dataWithContentsOfFile: statePath]
                                         options: 0
                                           error: NULL];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([[[state objectForKey: @"packages"] objectForKey: @"org.gnustep.tools-xctest"] objectForKey: @"version"], @"0.2.0");
  XCTAssertEqualObjects([NSString stringWithContentsOfFile: [installRoot stringByAppendingPathComponent: @"bin/xctest"]
                                                  encoding: NSUTF8StringEncoding
                                                     error: NULL], @"xctest updated");
}


- (void)testUpdateDefaultAllCreatesConfirmationRequiredPlan
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"update-all-plan"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"0.0.9", @"toolchain_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"command"], @"update");
  XCTAssertEqualObjects([payload objectForKey: @"scope"], @"all");
  XCTAssertEqualObjects([payload objectForKey: @"mode"], @"plan");
  XCTAssertNotNil([[payload objectForKey: @"plan"] objectForKey: @"cli"]);
  XCTAssertNotNil([[payload objectForKey: @"plan"] objectForKey: @"packages"]);
  XCTAssertTrue([[payload objectForKey: @"update_available"] boolValue]);
}

- (void)testUpdateAllCheckCombinesCliAndPackagePlans
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"update-all-check"];
  NSString *installRoot = [tempRoot stringByAppendingPathComponent: @"managed-root"];
  NSString *manifestRoot = [tempRoot stringByAppendingPathComponent: @"manifest"];
  NSString *statePath = [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSString *packageStatePath = [installRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *manifestPath = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubManagedDoctorPayload]];
  [self ensureDirectory: [statePath stringByDeletingLastPathComponent]];
  [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               [NSNumber numberWithInt: 1], @"schema_version",
                                               @"0.0.9", @"cli_version",
                                               @"0.0.9", @"toolchain_version",
                                               @"healthy", @"status",
                                               nil]
                       toPath: statePath];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       [installRoot stringByAppendingPathComponent: @"packages/org.example.tool"], @"install_root",
                                                       @"0.1.0", @"version",
                                                       indexPath, @"index_path",
                                                       [NSArray array], @"dependencies",
                                                       [NSArray array], @"conflicts",
                                                       [NSArray array], @"installed_files",
                                                       nil], @"org.example.tool",
                                        nil], @"packages",
                         nil]
                 toPath: packageStatePath];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.example.tool", @"id",
                                                   @"tool", @"name",
                                                   @"0.2.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"Tool.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray array], @"dependencies",
                                                   [NSArray array], @"conflicts",
                                                   [NSArray arrayWithObject:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"tool-linux-clang", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                             @"file:///tmp/missing-tool.tar.gz", @"url",
                                                                             nil]], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];
  manifestPath = [self releaseManifestPathInDirectory: manifestRoot
                                           cliSHA256: @"unused-cli"
                                     toolchainSHA256: @"unused-toolchain"
                                              cliURL: @"file:///unused-cli"
                                        toolchainURL: @"file:///unused-toolchain"];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"all",
                                         @"--check",
                                         @"--root",
                                         installRoot,
                                         @"--manifest",
                                         manifestPath,
                                         @"--index",
                                         indexPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"scope"], @"all");
  XCTAssertEqualObjects([payload objectForKey: @"mode"], @"check");
  XCTAssertTrue([[[[payload objectForKey: @"plan"] objectForKey: @"cli"] objectForKey: @"update_available"] boolValue]);
  XCTAssertEqual((NSUInteger)1, [[[[payload objectForKey: @"plan"] objectForKey: @"packages"] objectAtIndex: 0] count] > 0 ? (NSUInteger)1 : (NSUInteger)0);
}

- (void)testUpdateRejectsUsageErrorsWithStableJsonFields
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  GSCommandContext *context = [GSCommandContext contextWithArguments: [NSArray arrayWithObjects: @"update", @"bogus", nil]];
  NSDictionary *payload = nil;
  int exitCode = 0;

  payload = [runner executeUpdateForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 2);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"command"], @"update");
  XCTAssertEqualObjects([payload objectForKey: @"status"], @"error");
  XCTAssertTrue([[payload objectForKey: @"summary"] rangeOfString: @"Unknown update scope"].location != NSNotFound);

  context = [GSCommandContext contextWithArguments: [NSArray arrayWithObjects: @"update", @"--root", nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 2);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"--root requires a value.");
}

- (void)testUpdatePackagesRollbackRestoresPreviousPackageOnFailedUpgrade
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"update-package-rollback"];
  NSString *badArchivePath = [tempRoot stringByAppendingPathComponent: @"bad-tools-xctest.tar.gz"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *installRoot = [managedRoot stringByAppendingPathComponent: @"packages/org.gnustep.tools-xctest"];
  NSString *statePath = [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  NSDictionary *state = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self ensureDirectory: [installRoot stringByAppendingPathComponent: @"bin"]];
  [@"xctest old" writeToFile: [installRoot stringByAppendingPathComponent: @"bin/xctest"]
                    atomically: YES
                      encoding: NSUTF8StringEncoding
                         error: NULL];
  [self ensureDirectory: [badArchivePath stringByDeletingLastPathComponent]];
  [@"not an archive" writeToFile: badArchivePath atomically: YES encoding: NSUTF8StringEncoding error: NULL];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       installRoot, @"install_root",
                                                       @"0.1.0", @"version",
                                                       indexPath, @"index_path",
                                                       @"tools-xctest-linux-clang-old", @"selected_artifact",
                                                       [NSArray array], @"dependencies",
                                                       [NSArray array], @"conflicts",
                                                       [NSArray arrayWithObject: @"packages/org.gnustep.tools-xctest/bin/xctest"], @"installed_files",
                                                       nil], @"org.gnustep.tools-xctest",
                                        nil], @"packages",
                         nil]
                 toPath: statePath];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.gnustep.tools-xctest", @"id",
                                                   @"tools-xctest", @"name",
                                                   @"0.2.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"XCTest runner update.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray array], @"dependencies",
                                                   [NSArray array], @"conflicts",
                                                   [NSArray arrayWithObject:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"tools-xctest-linux-clang-new", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                             [NSString stringWithFormat: @"file://%@", badArchivePath], @"url",
                                                                             @"bad-sha", @"sha256",
                                                                             nil]], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"update",
                                         @"packages",
                                         @"--yes",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         nil]];
  payload = [runner executeUpdateForContext: context exitCode: &exitCode];
  state = [NSJSONSerialization JSONObjectWithData: [NSData dataWithContentsOfFile: statePath]
                                         options: 0
                                           error: NULL];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([[[state objectForKey: @"packages"] objectForKey: @"org.gnustep.tools-xctest"] objectForKey: @"version"], @"0.1.0");
  XCTAssertEqualObjects([NSString stringWithContentsOfFile: [installRoot stringByAppendingPathComponent: @"bin/xctest"]
                                                  encoding: NSUTF8StringEncoding
                                                     error: NULL], @"xctest old");
}


- (void)testUpdateHumanOutputIncludesPackageActions
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *human = [runner renderHumanForPayload:
                              [NSDictionary dictionaryWithObjectsAndKeys:
                                             [NSNumber numberWithInt: 1], @"schema_version",
                                             @"update", @"command",
                                             [NSNumber numberWithBool: YES], @"ok",
                                             @"ok", @"status",
                                             @"Package updates are available.", @"summary",
                                             @"packages", @"scope",
                                             @"check", @"mode",
                                             [NSNumber numberWithBool: YES], @"update_available",
                                             [NSArray arrayWithObject:
                                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                                       @"org.gnustep.tools-xctest", @"id",
                                                                       @"0.1.0", @"current_version",
                                                                       @"0.2.0", @"available_version",
                                                                       @"upgrade", @"action",
                                                                       nil]], @"package_updates",
                                             nil]];

  XCTAssertTrue([human rangeOfString: @"update: scope=packages mode=check"].location != NSNotFound);
  XCTAssertTrue([human rangeOfString: @"update: available=yes"].location != NSNotFound);
  XCTAssertTrue([human rangeOfString: @"update: package=org.gnustep.tools-xctest action=upgrade current=0.1.0 available=0.2.0"].location != NSNotFound);
}

- (void)testRemoveRejectsInstalledDependentPackages
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"remove-dependents"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *statePath = [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       [managedRoot stringByAppendingPathComponent: @"packages/org.gnustep.tools-xctest"], @"install_root",
                                                       [NSArray array], @"dependencies",
                                                       [NSArray array], @"installed_files",
                                                       nil], @"org.gnustep.tools-xctest",
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       [managedRoot stringByAppendingPathComponent: @"packages/org.example.consumer"], @"install_root",
                                                       [NSArray arrayWithObject: @"org.gnustep.tools-xctest"], @"dependencies",
                                                       [NSArray array], @"installed_files",
                                                       nil], @"org.example.consumer",
                                        nil], @"packages",
                         nil]
                 toPath: statePath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"remove",
                                         @"--root",
                                         managedRoot,
                                         @"org.gnustep.tools-xctest",
                                         nil]];
  payload = [runner executeRemoveForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Package is required by installed dependencies.");
  XCTAssertEqualObjects([[payload objectForKey: @"dependents"] objectAtIndex: 0], @"org.example.consumer");
}


- (void)testInstallRejectsDeclaredPackageConflict
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"install-conflict"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *statePath = [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       [managedRoot stringByAppendingPathComponent: @"packages/org.example.old"], @"install_root",
                                                       [NSArray array], @"dependencies",
                                                       [NSArray array], @"conflicts",
                                                       [NSArray array], @"installed_files",
                                                       nil], @"org.example.old",
                                        nil], @"packages",
                         nil]
                 toPath: statePath];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         @"stable", @"channel",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.example.new", @"id",
                                                   @"new", @"name",
                                                   @"0.1.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"Conflicting package.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray array], @"dependencies",
                                                   [NSArray arrayWithObject: @"org.example.old"], @"conflicts",
                                                   [NSArray arrayWithObject:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"new-linux-clang", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                             @"file:///tmp/new.tar.gz", @"url",
                                                                             nil]], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"install",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         @"org.example.new",
                                         nil]];
  payload = [runner executeInstallForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Package conflicts with installed package 'org.example.old'.");
}

- (void)testInstallRejectsMissingDeclaredDependency
{
  StubbedGSCommandRunner *runner = [[[StubbedGSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"install-missing-dependency"];
  NSString *payloadDir = [tempRoot stringByAppendingPathComponent: @"artifact-root"];
  NSString *archivePath = [tempRoot stringByAppendingPathComponent: @"dep-test.tar.gz"];
  NSString *indexPath = [tempRoot stringByAppendingPathComponent: @"package-index.json"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [runner setStubDoctorPayload: [self stubDoctorPayload]];
  [self ensureDirectory: [payloadDir stringByAppendingPathComponent: @"bin"]];
  [@"consumer" writeToFile: [payloadDir stringByAppendingPathComponent: @"bin/consumer"]
                      atomically: YES
                        encoding: NSUTF8StringEncoding
                           error: NULL];
  [self archiveDirectory: payloadDir toTarball: archivePath withRunner: runner];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         @"stable", @"channel",
                         [NSArray arrayWithObject:
                                    [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"org.example.consumer", @"id",
                                                   @"consumer", @"name",
                                                   @"0.1.0", @"version",
                                                   @"cli-tool", @"kind",
                                                   @"Consumer package.", @"summary",
                                                   [NSDictionary dictionaryWithObjectsAndKeys:
                                                                  [NSArray arrayWithObject: @"linux"], @"supported_os",
                                                                  [NSArray arrayWithObject: @"amd64"], @"supported_arch",
                                                                  [NSArray arrayWithObject: @"clang"], @"supported_compiler_families",
                                                                  [NSArray arrayWithObject: @"libobjc2"], @"supported_objc_runtimes",
                                                                  [NSArray arrayWithObject: @"modern"], @"supported_objc_abi",
                                                                  [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                  [NSArray array], @"forbidden_features",
                                                                  nil], @"requirements",
                                                   [NSArray arrayWithObject: @"org.example.missing"], @"dependencies",
                                                   [NSArray arrayWithObject:
                                                              [NSDictionary dictionaryWithObjectsAndKeys:
                                                                             @"consumer-linux-clang", @"id",
                                                                             @"linux", @"os",
                                                                             @"amd64", @"arch",
                                                                             @"clang", @"compiler_family",
                                                                             @"clang", @"toolchain_flavor",
                                                                             @"libobjc2", @"objc_runtime",
                                                                             @"modern", @"objc_abi",
                                                                             [NSArray arrayWithObject: @"blocks"], @"required_features",
                                                                             [NSString stringWithFormat: @"file://%@", archivePath], @"url",
                                                                             [runner sha256ForFile: archivePath], @"sha256",
                                                                             nil]], @"artifacts",
                                                   nil]], @"packages",
                         nil]
                 toPath: indexPath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"install",
                                         @"--root",
                                         managedRoot,
                                         @"--index",
                                         indexPath,
                                         @"org.example.consumer",
                                         nil]];
  payload = [runner executeInstallForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Package dependency 'org.example.missing' is not installed.");
}

- (void)testRemoveReportsMissingPackage
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"remove-missing"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  GSCommandContext *context = [GSCommandContext contextWithArguments:
                                                [NSArray arrayWithObjects:
                                                           @"remove",
                                                           @"--root",
                                                           managedRoot,
                                                           @"org.example.missing",
                                                           nil]];
  NSDictionary *payload = nil;
  int exitCode = 0;

  payload = [runner executeRemoveForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 1);
  XCTAssertFalse([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Package is not installed.");
}

- (void)testInstallAlreadyInstalledPackageReturnsExistingState
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"install-already-installed"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *statePath = [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  NSString *manifestPath = [tempRoot stringByAppendingPathComponent: @"ignored-package.json"];
  GSCommandContext *context = [GSCommandContext contextWithArguments:
                                                [NSArray arrayWithObjects:
                                                           @"install",
                                                           @"--root",
                                                           managedRoot,
                                                           manifestPath,
                                                           nil]];
  NSDictionary *payload = nil;
  int exitCode = 0;

  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       [managedRoot stringByAppendingPathComponent: @"packages/org.gnustep.tools-xctest"], @"install_root",
                                                       [NSArray arrayWithObject: @"packages/org.gnustep.tools-xctest/bin/xctest"], @"installed_files",
                                                       nil], @"org.gnustep.tools-xctest",
                                        nil], @"packages",
                         nil]
                 toPath: statePath];

  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         @"org.gnustep.tools-xctest", @"id",
                         [NSArray array], @"artifacts",
                         nil]
                 toPath: manifestPath];

  payload = [runner executeInstallForContext: context exitCode: &exitCode];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Package is already installed.");
  XCTAssertEqual([[payload objectForKey: @"installed_files"] count], (NSUInteger)1);
}

- (void)testRemoveDeletesInstalledRootAndUpdatesState
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *tempRoot = [self temporaryPathComponent: @"remove-installed-root"];
  NSString *managedRoot = [tempRoot stringByAppendingPathComponent: @"managed"];
  NSString *installRoot = [managedRoot stringByAppendingPathComponent: @"packages/org.gnustep.tools-xctest"];
  NSString *statePath = [managedRoot stringByAppendingPathComponent: @"state/installed-packages.json"];
  NSDictionary *state = nil;
  GSCommandContext *context = nil;
  NSDictionary *payload = nil;
  int exitCode = 0;

  [self ensureDirectory: [installRoot stringByAppendingPathComponent: @"bin"]];
  [@"xctest" writeToFile: [installRoot stringByAppendingPathComponent: @"bin/xctest"]
                  atomically: YES
                    encoding: NSUTF8StringEncoding
                       error: NULL];
  [self writeJSONStringObject:
          [NSDictionary dictionaryWithObjectsAndKeys:
                         [NSNumber numberWithInt: 1], @"schema_version",
                         [NSDictionary dictionaryWithObjectsAndKeys:
                                        [NSDictionary dictionaryWithObjectsAndKeys:
                                                       installRoot, @"install_root",
                                                       [NSArray array], @"dependencies",
                                                       [NSArray arrayWithObject: @"packages/org.gnustep.tools-xctest/bin/xctest"], @"installed_files",
                                                       nil], @"org.gnustep.tools-xctest",
                                        nil], @"packages",
                         nil]
                 toPath: statePath];

  context = [GSCommandContext contextWithArguments:
                              [NSArray arrayWithObjects:
                                         @"remove",
                                         @"--root",
                                         managedRoot,
                                         @"org.gnustep.tools-xctest",
                                         nil]];
  payload = [runner executeRemoveForContext: context exitCode: &exitCode];
  state = [NSJSONSerialization JSONObjectWithData:
                               [NSData dataWithContentsOfFile: statePath]
                                         options: 0
                                           error: NULL];

  XCTAssertEqual(exitCode, 0);
  XCTAssertTrue([[payload objectForKey: @"ok"] boolValue]);
  XCTAssertEqualObjects([payload objectForKey: @"summary"], @"Package removed.");
  XCTAssertFalse([[NSFileManager defaultManager] fileExistsAtPath: installRoot]);
  XCTAssertNil([[state objectForKey: @"packages"] objectForKey: @"org.gnustep.tools-xctest"]);
}

- (void)testInstallHumanOutputIncludesArtifactAndRoot
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *human = [runner renderHumanForPayload:
                              [NSDictionary dictionaryWithObjectsAndKeys:
                                             @"install", @"command",
                                             [NSNumber numberWithBool: YES], @"ok",
                                             @"Package installed.", @"summary",
                                             @"org.gnustep.tools-xctest", @"package_id",
                                             @"tools-xctest-linux-amd64-clang", @"selected_artifact",
                                             @"/tmp/managed/packages/org.gnustep.tools-xctest", @"install_root",
                                             @"/tmp/managed", @"managed_root",
                                             [NSArray arrayWithObject: @"org.gnustep.make"], @"dependencies",
                                             [NSArray arrayWithObjects: @"packages/org.gnustep.tools-xctest/bin/xctest", nil], @"installed_files",
                                             nil]];

  XCTAssertTrue([human rangeOfString: @"install: package=org.gnustep.tools-xctest"].location != NSNotFound);
  XCTAssertTrue([human rangeOfString: @"install: artifact=tools-xctest-linux-amd64-clang"].location != NSNotFound);
  XCTAssertTrue([human rangeOfString: @"install: root=/tmp/managed/packages/org.gnustep.tools-xctest"].location != NSNotFound);
}

- (void)testRemoveHumanOutputIncludesDependencyBlockers
{
  GSCommandRunner *runner = [[[GSCommandRunner alloc] init] autorelease];
  NSString *human = [runner renderHumanForPayload:
                              [NSDictionary dictionaryWithObjectsAndKeys:
                                             @"remove", @"command",
                                             [NSNumber numberWithBool: NO], @"ok",
                                             @"Package is required by installed dependencies.", @"summary",
                                             @"org.gnustep.tools-xctest", @"package_id",
                                             @"/tmp/managed", @"managed_root",
                                             [NSArray arrayWithObjects: @"org.example.consumer", @"org.example.gui", nil], @"dependents",
                                             nil]];

  XCTAssertTrue([human rangeOfString: @"remove: package=org.gnustep.tools-xctest"].location != NSNotFound);
  XCTAssertTrue([human rangeOfString: @"remove: blocked_by=org.example.consumer, org.example.gui"].location != NSNotFound);
}

@end
