#import "GSCommandRunner.h"
#import "GSCommandContext.h"

#import <sys/stat.h>
#import <stdio.h>
#import <stdint.h>
#import <string.h>
#import <stdlib.h>
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
#import <io.h>
#else
#import <unistd.h>
#endif

@interface GSCommandRunner ()

- (BOOL)isKnownCommand:(NSString *)command;
- (NSString *)commandSummary:(NSString *)command;
- (void)printCommandHelp:(NSString *)command;
- (void)printHelp;
- (NSDictionary *)payloadWithCommand:(NSString *)command
                                  ok:(BOOL)ok
                              status:(NSString *)status
                             summary:(NSString *)summary
                                data:(NSDictionary *)data;
- (void)emitJSONPayload:(NSDictionary *)payload;
- (NSDictionary *)versionPayload;
- (NSString *)repositoryRoot;
- (NSString *)defaultManifestPath;
- (NSString *)defaultManagedRoot;
- (BOOL)arguments:(NSArray *)arguments containOption:(NSString *)option;
- (NSDictionary *)readJSONFile:(NSString *)path error:(NSString **)errorMessage;
- (NSData *)downloadURLData:(NSString *)urlString error:(NSString **)errorMessage;
- (BOOL)writeJSONStringObject:(id)object toPath:(NSString *)path error:(NSString **)errorMessage;
- (NSString *)resolvedExecutablePathForCommand:(NSString *)command;
- (NSString *)resolvedExecutablePathForCommand:(NSString *)command environment:(NSDictionary *)environment;
- (NSDictionary *)managedChildProcessEnvironment;
- (NSString *)stringByAppendingToken:(NSString *)token toString:(NSString *)string;
- (BOOL)packageRequirements:(NSDictionary *)requirements matchEnvironment:(NSDictionary *)environment reason:(NSString **)reason;
- (NSDictionary *)selectedPackageArtifactForPackage:(NSDictionary *)packageRecord environment:(NSDictionary *)environment selectionError:(NSString **)selectionError;
- (NSDictionary *)packageRecordFromIndexPath:(NSString *)indexPath packageID:(NSString *)packageID error:(NSString **)errorMessage;
- (NSDictionary *)loadInstalledPackagesState:(NSString *)managedRoot;
- (BOOL)saveInstalledPackagesState:(NSDictionary *)state managedRoot:(NSString *)managedRoot;
- (NSString *)resolvedArtifactPathFromURLString:(NSString *)urlString;
- (void)appendInstallTrace:(NSString *)message;
- (BOOL)writeString:(NSString *)content toPath:(NSString *)path;
- (NSData *)dataFromFileAtPath:(NSString *)path offset:(unsigned long long *)offset;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory timeout:(NSTimeInterval)timeout;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory timeout:(NSTimeInterval)timeout additionalPathEntries:(NSArray *)additionalPathEntries;
- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory timeout:(NSTimeInterval)timeout additionalPathEntries:(NSArray *)additionalPathEntries streamOutput:(BOOL)streamOutput;
- (NSDictionary *)launchCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory additionalPathEntries:(NSArray *)additionalPathEntries;
- (NSDictionary *)interactiveCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory;
- (NSString *)firstAvailableExecutable:(NSArray *)names;
- (NSArray *)projectRuntimePathEntriesUnderPath:(NSString *)projectPath;
- (NSString *)windowsOpenAppLaunchCommandForProject:(NSDictionary *)runProject runtimePathEntries:(NSArray *)runtimePathEntries;
- (NSString *)singleQuotedPowerShellString:(NSString *)string;
- (NSString *)windowsStartBashCommandForBash:(NSString *)bash command:(NSString *)command;
- (NSString *)windowsStartBashScriptCommandForBash:(NSString *)bash scriptPath:(NSString *)scriptPath;
- (NSString *)writeWindowsOpenAppLaunchScriptForCommand:(NSString *)command;
- (NSString *)singleQuotedShellString:(NSString *)string;
- (NSString *)projectPathFromCommandArguments:(NSArray *)arguments;
- (NSString *)buildSystemFromCommandArguments:(NSArray *)arguments;
- (NSDictionary *)projectOperationPhaseWithName:(NSString *)name
                                        backend:(NSString *)backend
                                     invocation:(NSArray *)invocation
                                        project:(NSDictionary *)project
                                   streamOutput:(BOOL)streamOutput;
- (NSDictionary *)runnableProjectForProject:(NSDictionary *)project;
- (NSArray *)runnableProjectsUnderPath:(NSString *)projectPath;
- (NSArray *)runnableProjectsUnderPath:(NSString *)projectPath visited:(NSMutableSet *)visited;
- (NSDictionary *)checkWithID:(NSString *)checkID
                         title:(NSString *)title
                        status:(NSString *)status
                      severity:(NSString *)severity
                       message:(NSString *)message
                     interface:(NSString *)interface
                executionTier:(NSString *)executionTier
                       details:(NSDictionary *)details;
- (NSDictionary *)actionWithKind:(NSString *)kind
                         message:(NSString *)message
                        priority:(int)priority;
- (NSDictionary *)detectProjectAtPath:(NSString *)projectPath;
- (NSString *)readOSReleaseIdentifier;
- (NSDictionary *)compilerInfoForExecutable:(NSString *)compilerExecutable;
- (NSString *)gnustepMakeCompilerPathWithConfig:(NSString *)gnustepConfig;
- (NSDictionary *)toolchainFactsForInterface:(NSString *)interface;
- (NSDictionary *)toolchainFactsForInterface:(NSString *)interface quick:(BOOL)quick;
- (BOOL)isDeferredProbe:(NSDictionary *)probe;
- (BOOL)hasWindowsManagedToolchainHintWithMakefiles:(NSString *)gnustepMakefiles;
- (NSDictionary *)managedInstallIntegrityCheckForEnvironment:(NSDictionary *)environment interface:(NSString *)interface;
- (NSDictionary *)nativeToolchainAssessmentForEnvironment:(NSDictionary *)environment compatibility:(NSDictionary *)compatibility;
- (NSDictionary *)currentEnvironmentForInterface:(NSString *)interface;
- (NSDictionary *)buildDoctorPayloadWithInterface:(NSString *)interface manifestPath:(NSString *)manifestPath quick:(BOOL)quick;
- (NSString *)setupTransactionStatePathForInstallRoot:(NSString *)installRoot;
- (NSString *)setupBackupPathForInstallRoot:(NSString *)installRoot;
- (void)recoverSetupTransactionForInstallRoot:(NSString *)installRoot;
- (BOOL)beginSetupTransactionForInstallRoot:(NSString *)installRoot
                                    release:(NSString *)releaseVersion
                                  artifacts:(NSArray *)artifactIDs
                                  backupPath:(NSString **)backupPath
                                       error:(NSString **)errorMessage;
- (void)finishSetupTransactionForInstallRoot:(NSString *)installRoot
                                  backupPath:(NSString *)backupPath
                                     success:(BOOL)success;
- (void)finishSetupTransactionForInstallRoot:(NSString *)installRoot
                                  backupPath:(NSString *)backupPath
                                     success:(BOOL)success
                              preserveBackup:(BOOL)preserveBackup;
- (NSDictionary *)installedLifecycleStateForInstallRoot:(NSString *)installRoot;
- (NSDate *)dateFromManifestTimestamp:(NSString *)timestamp;
- (BOOL)manifestMetadataPolicyAllowsManifest:(NSDictionary *)manifest error:(NSString **)errorMessage;
- (BOOL)manifest:(NSDictionary *)manifest revokesArtifacts:(NSArray *)artifacts error:(NSString **)errorMessage;
- (BOOL)manifest:(NSDictionary *)manifest isOlderThanInstalledState:(NSDictionary *)installedState error:(NSString **)errorMessage;
- (NSComparisonResult)compareVersionString:(NSString *)left toVersionString:(NSString *)right;
- (NSDictionary *)buildUpdatePlanForScope:(NSString *)scope
                                  manifest:(NSString *)manifestPath
                               installRoot:(NSString *)installRoot
                                  exitCode:(int *)exitCode;
- (NSDictionary *)executeUpdateForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)buildPackageUpdatePlanForRoot:(NSString *)root
                                      indexPath:(NSString *)indexPath
                                       exitCode:(int *)exitCode;
- (NSDictionary *)applyPackageUpdatePlan:(NSDictionary *)planPayload
                                    root:(NSString *)root
                                exitCode:(int *)exitCode;
- (BOOL)installManagedLauncherForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage;
- (BOOL)relocateManagedToolchainForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage;
- (BOOL)smokeVersionedReleaseAtPath:(NSString *)releaseRoot error:(NSString **)errorMessage;
- (BOOL)installCurrentPointerLauncherForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage;
- (NSString *)materializeVersionedReleaseForInstallRoot:(NSString *)installRoot version:(NSString *)version error:(NSString **)errorMessage;
- (NSDictionary *)rollbackManagedInstallRoot:(NSString *)installRoot exitCode:(int *)exitCode;
- (NSDictionary *)repairManagedInstallRoot:(NSString *)installRoot;
- (NSDictionary *)executeBuildForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeCleanForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeRunForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeShellForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeNewForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeInstallForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (NSDictionary *)executeRemoveForContext:(GSCommandContext *)context exitCode:(int *)exitCode;
- (int)runNativeCommandForContext:(GSCommandContext *)context;

@end

typedef struct
{
  uint32_t state[8];
  uint64_t bitCount;
  unsigned char buffer[64];
} GSSHA256Context;

static const uint32_t GSSHA256K[64] = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

static uint32_t GSSHA256RotateRight(uint32_t value, uint32_t bits)
{
  return (value >> bits) | (value << (32 - bits));
}

static void GSSHA256Transform(GSSHA256Context *context, const unsigned char block[64])
{
  uint32_t w[64];
  uint32_t a, b, c, d, e, f, g, h;
  unsigned int i = 0;

  for (i = 0; i < 16; i++)
    {
      w[i] = ((uint32_t)block[i * 4] << 24) |
             ((uint32_t)block[i * 4 + 1] << 16) |
             ((uint32_t)block[i * 4 + 2] << 8) |
             ((uint32_t)block[i * 4 + 3]);
    }
  for (i = 16; i < 64; i++)
    {
      uint32_t s0 = GSSHA256RotateRight(w[i - 15], 7) ^ GSSHA256RotateRight(w[i - 15], 18) ^ (w[i - 15] >> 3);
      uint32_t s1 = GSSHA256RotateRight(w[i - 2], 17) ^ GSSHA256RotateRight(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }

  a = context->state[0]; b = context->state[1]; c = context->state[2]; d = context->state[3];
  e = context->state[4]; f = context->state[5]; g = context->state[6]; h = context->state[7];

  for (i = 0; i < 64; i++)
    {
      uint32_t s1 = GSSHA256RotateRight(e, 6) ^ GSSHA256RotateRight(e, 11) ^ GSSHA256RotateRight(e, 25);
      uint32_t ch = (e & f) ^ ((~e) & g);
      uint32_t temp1 = h + s1 + ch + GSSHA256K[i] + w[i];
      uint32_t s0 = GSSHA256RotateRight(a, 2) ^ GSSHA256RotateRight(a, 13) ^ GSSHA256RotateRight(a, 22);
      uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
      uint32_t temp2 = s0 + maj;
      h = g; g = f; f = e; e = d + temp1;
      d = c; c = b; b = a; a = temp1 + temp2;
    }

  context->state[0] += a; context->state[1] += b; context->state[2] += c; context->state[3] += d;
  context->state[4] += e; context->state[5] += f; context->state[6] += g; context->state[7] += h;
}

static void GSSHA256Init(GSSHA256Context *context)
{
  context->bitCount = 0;
  context->state[0] = 0x6a09e667; context->state[1] = 0xbb67ae85;
  context->state[2] = 0x3c6ef372; context->state[3] = 0xa54ff53a;
  context->state[4] = 0x510e527f; context->state[5] = 0x9b05688c;
  context->state[6] = 0x1f83d9ab; context->state[7] = 0x5be0cd19;
  memset(context->buffer, 0, sizeof(context->buffer));
}

static void GSSHA256Update(GSSHA256Context *context, const unsigned char *data, size_t length)
{
  size_t bufferIndex = (size_t)((context->bitCount / 8) % 64);
  size_t offset = 0;
  context->bitCount += ((uint64_t)length) * 8;
  while (offset < length)
    {
      size_t available = 64 - bufferIndex;
      size_t copyLength = length - offset < available ? length - offset : available;
      memcpy(context->buffer + bufferIndex, data + offset, copyLength);
      bufferIndex += copyLength;
      offset += copyLength;
      if (bufferIndex == 64)
        {
          GSSHA256Transform(context, context->buffer);
          bufferIndex = 0;
        }
    }
}

static void GSSHA256Final(GSSHA256Context *context, unsigned char digest[32])
{
  unsigned char padding[64];
  unsigned char lengthBytes[8];
  uint64_t bits = context->bitCount;
  size_t bufferIndex = (size_t)((context->bitCount / 8) % 64);
  size_t paddingLength = bufferIndex < 56 ? 56 - bufferIndex : 120 - bufferIndex;
  unsigned int i = 0;
  memset(padding, 0, sizeof(padding));
  padding[0] = 0x80;
  for (i = 0; i < 8; i++)
    {
      lengthBytes[7 - i] = (unsigned char)((bits >> (i * 8)) & 0xff);
    }
  GSSHA256Update(context, padding, paddingLength);
  GSSHA256Update(context, lengthBytes, 8);
  for (i = 0; i < 8; i++)
    {
      digest[i * 4] = (unsigned char)((context->state[i] >> 24) & 0xff);
      digest[i * 4 + 1] = (unsigned char)((context->state[i] >> 16) & 0xff);
      digest[i * 4 + 2] = (unsigned char)((context->state[i] >> 8) & 0xff);
      digest[i * 4 + 3] = (unsigned char)(context->state[i] & 0xff);
    }
}

static NSString *GSSHA256ForFileAtPath(NSString *path)
{
  FILE *file = NULL;
  unsigned char readBuffer[32768];
  unsigned char digest[32];
  char hex[65];
  GSSHA256Context context;
  size_t bytesRead = 0;
  unsigned int i = 0;
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  const char *filePath = [path UTF8String];
#else
  const char *filePath = [path fileSystemRepresentation];
#endif
  if (filePath == NULL)
    {
      return nil;
    }
  file = fopen(filePath, "rb");
  if (file == NULL)
    {
      return nil;
    }
  GSSHA256Init(&context);
  while ((bytesRead = fread(readBuffer, 1, sizeof(readBuffer), file)) > 0)
    {
      GSSHA256Update(&context, readBuffer, bytesRead);
    }
  if (ferror(file))
    {
      fclose(file);
      return nil;
    }
  fclose(file);
  GSSHA256Final(&context, digest);
  for (i = 0; i < 32; i++)
    {
      snprintf(hex + (i * 2), 3, "%02x", digest[i]);
    }
  hex[64] = '\0';
  return [NSString stringWithUTF8String: hex];
}

@implementation GSCommandRunner

- (NSArray *)knownCommands
{
  return [NSArray arrayWithObjects:
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
}

- (BOOL)isKnownCommand:(NSString *)command
{
  return [[self knownCommands] containsObject: command];
}

- (NSString *)commandSummary:(NSString *)command
{
  if ([command isEqualToString: @"doctor"])
    {
      return @"Inspect the local GNUstep environment and report readiness.";
    }
  if ([command isEqualToString: @"setup"])
    {
      return @"Install or repair the managed GNUstep CLI environment.";
    }
  if ([command isEqualToString: @"build"])
    {
      return @"Build the current GNUstep project.";
    }
  if ([command isEqualToString: @"clean"])
    {
      return @"Clean build outputs for the current GNUstep project.";
    }
  if ([command isEqualToString: @"run"])
    {
      return @"Run the current GNUstep project.";
    }
  if ([command isEqualToString: @"shell"])
    {
      return @"Open the managed MSYS2 CLANG64 GNUstep shell on Windows.";
    }
  if ([command isEqualToString: @"new"])
    {
      return @"Create a new GNUstep project from a curated template.";
    }
  if ([command isEqualToString: @"install"])
    {
      return @"Install a GNUstep package into the managed environment.";
    }
  if ([command isEqualToString: @"remove"])
    {
      return @"Remove a GNUstep package from the managed environment.";
    }
  if ([command isEqualToString: @"update"])
    {
      return @"Check for and apply CLI, toolchain, and package updates.";
    }
  return @"";
}

- (void)printCommandHelp:(NSString *)command
{
  printf("Usage:\n");
  if ([command isEqualToString: @"doctor"])
    {
      printf("  gnustep doctor [--json] [--quick|--full] [--manifest <path>] [--interface bootstrap|full]\n\n");
    }
  else if ([command isEqualToString: @"setup"])
    {
      printf("  gnustep setup [--json] [--user|--system] [--root <path>] [--manifest <path>] [--check-updates|--upgrade|--repair|--rollback]\n\n");
    }
  else if ([command isEqualToString: @"build"])
    {
      printf("  gnustep build [--json] [--clean] [--build-system <id>] [project-dir]\n\n");
    }
  else if ([command isEqualToString: @"clean"])
    {
      printf("  gnustep clean [--json] [--build-system <id>] [project-dir]\n\n");
    }
  else if ([command isEqualToString: @"run"])
    {
      printf("  gnustep run [--json] [--build-system <id>] [project-dir]\n\n");
    }
  else if ([command isEqualToString: @"shell"])
    {
      printf("  gnustep shell [--json] [--print-command]\n\n");
    }
  else if ([command isEqualToString: @"new"])
    {
      printf("  gnustep new [--json] [--list-templates] <template> <destination> [--name <name>]\n\n");
    }
  else if ([command isEqualToString: @"install"])
    {
      printf("  gnustep install [--json] [--root <path>] [--index <path>] <package-id|package-manifest>\n\n");
    }
  else if ([command isEqualToString: @"remove"])
    {
      printf("  gnustep remove [--json] [--root <path>] <package-id>\n\n");
    }
  else if ([command isEqualToString: @"update"])
    {
      printf("  gnustep update [all|cli|packages] [--check] [--json] [--yes] [--root <path>] [--manifest <path>] [--index <path>]\n\n");
    }
  else
    {
      printf("  gnustep %s [options]\n\n", [command UTF8String]);
    }
  printf("%s\n", [[self commandSummary: command] UTF8String]);
}

- (void)printHelp
{
  NSUInteger i = 0;
  NSArray *commands = [self knownCommands];

  printf("GNUstep CLI full interface\n\n");
  printf("Usage:\n");
  printf("  gnustep <command> [options] [args]\n\n");
  printf("Global options:\n");
  printf("  --help\n");
  printf("  --version\n");
  printf("  --json\n");
  printf("  --verbose\n");
  printf("  --quiet\n");
  printf("  --yes\n\n");
  printf("Commands:\n");
  for (i = 0; i < [commands count]; i++)
    {
      NSString *command = [commands objectAtIndex: i];
      printf("  %-7s %s\n",
             [command UTF8String],
             [[self commandSummary: command] UTF8String]);
    }
}

- (NSDictionary *)payloadWithCommand:(NSString *)command
                                  ok:(BOOL)ok
                              status:(NSString *)status
                             summary:(NSString *)summary
                                data:(NSDictionary *)data
{
  NSMutableDictionary *payload = [NSMutableDictionary dictionary];
  [payload setObject: [NSNumber numberWithInt: 1] forKey: @"schema_version"];
  [payload setObject: command forKey: @"command"];
  [payload setObject: [NSNumber numberWithBool: ok] forKey: @"ok"];
  [payload setObject: status forKey: @"status"];
  [payload setObject: summary forKey: @"summary"];
  if (data != nil)
    {
      [payload setObject: data forKey: @"data"];
    }
  return payload;
}

- (void)emitJSONPayload:(NSDictionary *)payload
{
  NSError *error = nil;
  NSData *data = [NSJSONSerialization dataWithJSONObject: payload options: 0 error: &error];
  if (data != nil)
    {
      fwrite([data bytes], 1, [data length], stdout);
      fputc('\n', stdout);
    }
}

- (NSDictionary *)versionPayload
{
  return [self payloadWithCommand: @"version"
                               ok: YES
                           status: @"ok"
                          summary: @"GNUstep CLI version"
                             data: [NSDictionary dictionaryWithObject: @"0.1.0-dev"
                                                              forKey: @"version"]];
}

- (NSString *)repositoryRoot
{
  NSString *binaryPath = [[[NSProcessInfo processInfo] arguments] objectAtIndex: 0];
  NSString *resolvedPath = [binaryPath stringByResolvingSymlinksInPath];
  NSString *binaryDir = [resolvedPath stringByDeletingLastPathComponent];
  NSString *installRoot = [binaryDir stringByDeletingLastPathComponent];
  NSString *candidate = [resolvedPath stringByDeletingLastPathComponent];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *libexecRoot = [installRoot stringByAppendingPathComponent: @"libexec/gnustep-cli"];

  if ([manager fileExistsAtPath: [libexecRoot stringByAppendingPathComponent: @"examples"]])
    {
      return libexecRoot;
    }

  while ([candidate length] > 1)
    {
      NSString *parent = nil;
      if ([manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"examples"]] &&
          [manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"src/full-cli"]])
        {
          return candidate;
        }
      parent = [candidate stringByDeletingLastPathComponent];
      if (parent == nil || [parent isEqualToString: candidate])
        {
          break;
        }
      candidate = parent;
    }

  candidate = [[manager currentDirectoryPath] stringByResolvingSymlinksInPath];
  while ([candidate length] > 1)
    {
      NSString *parent = nil;
      if ([manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"examples"]] &&
          [manager fileExistsAtPath: [candidate stringByAppendingPathComponent: @"src/full-cli"]])
        {
          return candidate;
        }
      parent = [candidate stringByDeletingLastPathComponent];
      if (parent == nil || [parent isEqualToString: candidate])
        {
          break;
        }
      candidate = parent;
    }

  return nil;
}

- (NSString *)defaultManifestPath
{
  NSString *root = [self repositoryRoot];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *staged = nil;

  if (root != nil)
    {
      staged = [[root stringByAppendingPathComponent: @"dist/stable/0.1.0-dev"] stringByAppendingPathComponent: @"release-manifest.json"];
      if ([manager fileExistsAtPath: staged])
        {
          return staged;
        }
    }
  return @"https://github.com/danjboyd/gnustep-cli-new/releases/download/v0.1.0-dev/release-manifest.json";
}

- (NSString *)defaultManagedRoot
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  return @"%LOCALAPPDATA%\\gnustep-cli";
#else
  return [NSHomeDirectory() stringByAppendingPathComponent: @".local/share/gnustep-cli"];
#endif
}

- (BOOL)arguments:(NSArray *)arguments containOption:(NSString *)option
{
  return [arguments containsObject: option];
}

- (NSDictionary *)readJSONFile:(NSString *)path error:(NSString **)errorMessage
{
  NSData *data = nil;
  NSError *error = nil;
  id object = nil;

  if ([path hasPrefix: @"http://"] || [path hasPrefix: @"https://"])
    {
      data = [self downloadURLData: path error: errorMessage];
    }
  else
    {
      data = [NSData dataWithContentsOfFile: path];
    }

  if (data == nil)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Could not read JSON document at %@", path];
        }
      return nil;
    }

  object = [NSJSONSerialization JSONObjectWithData: data options: 0 error: &error];
  if (object == nil || [object isKindOfClass: [NSDictionary class]] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Invalid JSON in %@", path];
        }
      return nil;
    }
  return (NSDictionary *)object;
}

- (NSData *)downloadURLData:(NSString *)urlString error:(NSString **)errorMessage
{
  NSString *downloader = [self firstAvailableExecutable: [NSArray arrayWithObjects: @"curl", @"wget", @"powershell.exe", @"powershell", nil]];
  NSTask *task = nil;
  NSPipe *output = nil;
  NSPipe *errors = nil;
  NSData *data = nil;
  NSString *downloaderName = nil;

  if (downloader == nil)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Could not read JSON URL because no downloader is available.";
        }
      return nil;
    }

  task = [[[NSTask alloc] init] autorelease];
  output = [NSPipe pipe];
  errors = [NSPipe pipe];
  [task setLaunchPath: downloader];
  downloaderName = [[downloader lastPathComponent] lowercaseString];
  if ([downloaderName isEqualToString: @"curl"] || [downloaderName isEqualToString: @"curl.exe"])
    {
      [task setArguments: [NSArray arrayWithObjects: @"-fsSL", urlString, nil]];
    }
  else if ([downloaderName isEqualToString: @"wget"] || [downloaderName isEqualToString: @"wget.exe"])
    {
      [task setArguments: [NSArray arrayWithObjects: @"-qO-", urlString, nil]];
    }
  else
    {
      NSString *escapedURL = [urlString stringByReplacingOccurrencesOfString: @"'" withString: @"''"];
      NSString *command = [NSString stringWithFormat:
                                      @"[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (Invoke-WebRequest -UseBasicParsing -Uri '%@').Content",
                                      escapedURL];
      [task setArguments: [NSArray arrayWithObjects: @"-NoProfile", @"-ExecutionPolicy", @"Bypass", @"-Command", command, nil]];
    }
  [task setStandardOutput: output];
  [task setStandardError: errors];

  @try
    {
      [task launch];
      data = [[output fileHandleForReading] readDataToEndOfFile];
      [task waitUntilExit];
    }
  @catch (NSException *exception)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Failed to launch downloader for %@.", urlString];
        }
      return nil;
    }

  if ([task terminationStatus] != 0 || [data length] == 0)
    {
      NSData *stderrData = [[errors fileHandleForReading] readDataToEndOfFile];
      NSString *stderrText = [[[NSString alloc] initWithData: stderrData encoding: NSUTF8StringEncoding] autorelease];
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Could not read JSON document at %@%@%@",
                            urlString,
                            ([stderrText length] > 0 ? @": " : @""),
                            ([stderrText length] > 0 ? stderrText : @"")];
        }
      return nil;
    }
  return data;
}

- (BOOL)writeJSONStringObject:(id)object toPath:(NSString *)path error:(NSString **)errorMessage
{
  NSError *error = nil;
  NSData *data = [NSJSONSerialization dataWithJSONObject: object
                                                 options: NSJSONWritingPrettyPrinted
                                                   error: &error];
  if (data == nil)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Failed to encode JSON output.";
        }
      return NO;
    }
  if ([data writeToFile: path atomically: YES] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Failed to write %@", path];
        }
      return NO;
    }
  return YES;
}

- (NSString *)resolvedExecutablePathForCommand:(NSString *)command
{
  return [self resolvedExecutablePathForCommand: command
                                    environment: [[NSProcessInfo processInfo] environment]];
}

- (NSString *)resolvedExecutablePathForCommand:(NSString *)command environment:(NSDictionary *)environment
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *pathVariable = [environment objectForKey: @"PATH"];
  NSArray *pathEntries = nil;
  NSMutableArray *candidateNames = [NSMutableArray array];
  NSUInteger i = 0;

  if (command == nil || [command length] == 0)
    {
      return nil;
    }

  if ([command rangeOfString: @"/"].location != NSNotFound ||
      [command rangeOfString: @"\\"].location != NSNotFound)
    {
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
      return [manager fileExistsAtPath: command] ? command : nil;
#else
      return [manager isExecutableFileAtPath: command] ? command : nil;
#endif
    }

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  pathEntries = pathVariable ? [pathVariable componentsSeparatedByString: @";"] : [NSArray array];
  [candidateNames addObject: command];
  if ([[command pathExtension] length] == 0)
    {
      [candidateNames addObject: [command stringByAppendingString: @".exe"]];
      [candidateNames addObject: [command stringByAppendingString: @".bat"]];
      [candidateNames addObject: [command stringByAppendingString: @".cmd"]];
    }
#else
  pathEntries = pathVariable ? [pathVariable componentsSeparatedByString: @":"] : [NSArray array];
  [candidateNames addObject: command];
#endif

  for (i = 0; i < [pathEntries count]; i++)
    {
      NSString *entry = [pathEntries objectAtIndex: i];
      NSUInteger j = 0;
      if ([entry length] == 0)
        {
          continue;
        }
      for (j = 0; j < [candidateNames count]; j++)
        {
          NSString *candidate = [entry stringByAppendingPathComponent: [candidateNames objectAtIndex: j]];
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
          if ([manager fileExistsAtPath: candidate])
            {
              return candidate;
            }
#else
          if ([manager isExecutableFileAtPath: candidate])
            {
              return candidate;
            }
#endif
        }
    }

  return nil;
}

- (NSDictionary *)managedChildProcessEnvironment
{
  NSMutableDictionary *environment = [NSMutableDictionary dictionaryWithDictionary: [[NSProcessInfo processInfo] environment]];
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  NSString *binaryPath = [[[NSProcessInfo processInfo] arguments] objectAtIndex: 0];
  NSString *resolvedPath = [binaryPath stringByResolvingSymlinksInPath];
  NSString *binDir = [resolvedPath stringByDeletingLastPathComponent];
  NSString *installRoot = [binDir stringByDeletingLastPathComponent];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *makefiles = [[[installRoot stringByAppendingPathComponent: @"clang64"] stringByAppendingPathComponent: @"share"] stringByAppendingPathComponent: @"GNUstep\\Makefiles"];
  NSString *configFile = [[[installRoot stringByAppendingPathComponent: @"clang64"] stringByAppendingPathComponent: @"etc"] stringByAppendingPathComponent: @"GNUstep\\GNUstep.conf"];
  NSString *tmpDir = [installRoot stringByAppendingPathComponent: @"tmp"];
  NSMutableArray *pathEntries = [NSMutableArray array];
  NSString *existingPath = [environment objectForKey: @"PATH"];

  if ([manager fileExistsAtPath: makefiles] == NO)
    {
      makefiles = [[installRoot stringByAppendingPathComponent: @"share"] stringByAppendingPathComponent: @"GNUstep\\Makefiles"];
      configFile = [[installRoot stringByAppendingPathComponent: @"etc"] stringByAppendingPathComponent: @"GNUstep\\GNUstep.conf"];
    }

  if ([manager fileExistsAtPath: makefiles])
    {
      [manager createDirectoryAtPath: tmpDir withIntermediateDirectories: YES attributes: nil error: NULL];
      [pathEntries addObject: [installRoot stringByAppendingPathComponent: @"clang64\\bin"]];
      [pathEntries addObject: [installRoot stringByAppendingPathComponent: @"bin"]];
      [pathEntries addObject: [installRoot stringByAppendingPathComponent: @"usr\\bin"]];
      if ([existingPath length] > 0)
        {
          [pathEntries addObject: existingPath];
        }
      [environment setObject: [pathEntries componentsJoinedByString: @";"] forKey: @"PATH"];
      [environment setObject: makefiles forKey: @"GNUSTEP_MAKEFILES"];
      [environment setObject: configFile forKey: @"GNUSTEP_CONFIG_FILE"];
      [environment setObject: @"CLANG64" forKey: @"MSYSTEM"];
      [environment setObject: @"1" forKey: @"CHERE_INVOKING"];
      [environment setObject: tmpDir forKey: @"TMPDIR"];
      [environment setObject: tmpDir forKey: @"TEMP"];
      [environment setObject: tmpDir forKey: @"TMP"];
      [environment setObject: [self stringByAppendingToken: @"-DHAVE_MODE_T"
                                                  toString: [environment objectForKey: @"ADDITIONAL_OBJCFLAGS"]]
                    forKey: @"ADDITIONAL_OBJCFLAGS"];
      [environment setObject: [self stringByAppendingToken: @"-DHAVE_MODE_T"
                                                  toString: [environment objectForKey: @"ADDITIONAL_CPPFLAGS"]]
                    forKey: @"ADDITIONAL_CPPFLAGS"];
    }
#endif
  return environment;
}

- (NSString *)stringByAppendingToken:(NSString *)token toString:(NSString *)string
{
  if ([string length] == 0)
    {
      return token;
    }
  if ([string rangeOfString: token].location != NSNotFound)
    {
      return string;
    }
  return [NSString stringWithFormat: @"%@ %@", string, token];
}

- (void)appendInstallTrace:(NSString *)message
{
  NSString *tracePath = [[[NSProcessInfo processInfo] environment] objectForKey: @"GNUSTEP_CLI_INSTALL_TRACE"];
  NSFileHandle *handle = nil;
  NSData *data = nil;

  if (tracePath == nil || [tracePath length] == 0 || message == nil)
    {
      return;
    }

  [[NSFileManager defaultManager] createDirectoryAtPath: [tracePath stringByDeletingLastPathComponent]
                            withIntermediateDirectories: YES
                                             attributes: nil
                                                  error: NULL];
  if ([[NSFileManager defaultManager] fileExistsAtPath: tracePath] == NO)
    {
      [[NSData data] writeToFile: tracePath atomically: YES];
    }
  handle = [NSFileHandle fileHandleForWritingAtPath: tracePath];
  if (handle == nil)
    {
      return;
    }
  [handle seekToEndOfFile];
  data = [[message stringByAppendingString: @"\n"] dataUsingEncoding: NSUTF8StringEncoding];
  if (data != nil)
    {
      [handle writeData: data];
    }
  [handle closeFile];

  if ([[[[NSProcessInfo processInfo] environment] objectForKey: @"GNUSTEP_CLI_INSTALL_TRACE_STDERR"] length] > 0)
    {
      fprintf(stderr, "%s\n", [message UTF8String]);
      fflush(stderr);
    }
}

- (NSData *)dataFromFileAtPath:(NSString *)path offset:(unsigned long long *)offset
{
  NSFileHandle *handle = [NSFileHandle fileHandleForReadingAtPath: path];
  NSData *data = nil;

  if (handle == nil || offset == NULL)
    {
      return nil;
    }
  [handle seekToEndOfFile];
  if ([handle offsetInFile] <= *offset)
    {
      [handle closeFile];
      return nil;
    }
  [handle seekToFileOffset: *offset];
  data = [handle readDataToEndOfFile];
  *offset = [handle offsetInFile];
  [handle closeFile];
  return data;
}

- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory
{
  return [self runCommand: arguments currentDirectory: currentDirectory timeout: 15.0];
}

- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory timeout:(NSTimeInterval)timeout
{
  return [self runCommand: arguments currentDirectory: currentDirectory timeout: timeout additionalPathEntries: nil];
}

- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory timeout:(NSTimeInterval)timeout additionalPathEntries:(NSArray *)additionalPathEntries
{
  return [self runCommand: arguments
         currentDirectory: currentDirectory
                  timeout: timeout
    additionalPathEntries: additionalPathEntries
             streamOutput: NO];
}

- (NSDictionary *)runCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory timeout:(NSTimeInterval)timeout additionalPathEntries:(NSArray *)additionalPathEntries streamOutput:(BOOL)streamOutput
{
  NSString *command = nil;
  NSString *launchPath = nil;
  NSArray *taskArguments = nil;
  NSTask *task = [[[NSTask alloc] init] autorelease];
  NSString *tempRoot = NSTemporaryDirectory();
  NSString *unique = [[NSProcessInfo processInfo] globallyUniqueString];
  NSString *stdoutPath = [tempRoot stringByAppendingPathComponent: [NSString stringWithFormat: @"gnustep-cli-run-%@.out", unique]];
  NSString *stderrPath = [tempRoot stringByAppendingPathComponent: [NSString stringWithFormat: @"gnustep-cli-run-%@.err", unique]];
  NSFileHandle *stdoutHandle = nil;
  NSFileHandle *stderrHandle = nil;
  NSData *stdoutData = nil;
  NSData *stderrData = nil;
  NSString *stdoutString = @"";
  NSString *stderrString = @"";
  unsigned long long stdoutReadOffset = 0;
  unsigned long long stderrReadOffset = 0;
  BOOL timedOut = NO;
  const char *timeoutRaw = getenv("GNUSTEP_CLI_COMMAND_TIMEOUT_SECONDS");
  NSDate *deadline = nil;
  NSDictionary *taskEnvironment = nil;

  if (timeoutRaw != NULL && atof(timeoutRaw) > 0)
    {
      timeout = atof(timeoutRaw);
    }

  if (arguments == nil || [arguments count] == 0)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            [NSNumber numberWithBool: NO], @"timed_out",
                            @"", @"stdout",
                            @"No command arguments were provided.", @"stderr",
                            nil];
    }

  command = [arguments objectAtIndex: 0];
  taskEnvironment = [self managedChildProcessEnvironment];
  if ([additionalPathEntries count] > 0)
    {
      NSMutableDictionary *mutableEnvironment = [NSMutableDictionary dictionaryWithDictionary: taskEnvironment];
      NSMutableArray *pathEntries = [NSMutableArray arrayWithArray: additionalPathEntries];
      NSString *existingPath = [mutableEnvironment objectForKey: @"PATH"];
      if ([existingPath length] > 0)
        {
          [pathEntries addObject: existingPath];
        }
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
      [mutableEnvironment setObject: [pathEntries componentsJoinedByString: @";"] forKey: @"PATH"];
#else
      [mutableEnvironment setObject: [pathEntries componentsJoinedByString: @":"] forKey: @"PATH"];
#endif
      taskEnvironment = mutableEnvironment;
    }
  if (currentDirectory != nil
      && ([command rangeOfString: @"/"].location != NSNotFound
          || [command rangeOfString: @"\\"].location != NSNotFound)
      && [command isAbsolutePath] == NO)
    {
      launchPath = [self resolvedExecutablePathForCommand: [currentDirectory stringByAppendingPathComponent: command]
                                              environment: taskEnvironment];
    }
  else
    {
      launchPath = [self resolvedExecutablePathForCommand: command environment: taskEnvironment];
    }
  taskArguments = [arguments count] > 1 ?
    [arguments subarrayWithRange: NSMakeRange(1, [arguments count] - 1)] :
    [NSArray array];

  if (launchPath == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            [NSNumber numberWithBool: NO], @"timed_out",
                            @"", @"stdout",
                            [NSString stringWithFormat: @"Executable not found: %@", command], @"stderr",
                            nil];
    }

  [[NSData data] writeToFile: stdoutPath atomically: YES];
  [[NSData data] writeToFile: stderrPath atomically: YES];
  stdoutHandle = [NSFileHandle fileHandleForWritingAtPath: stdoutPath];
  stderrHandle = [NSFileHandle fileHandleForWritingAtPath: stderrPath];
  [task setLaunchPath: launchPath];
  [task setArguments: taskArguments];
  [task setEnvironment: taskEnvironment];
  [task setStandardInput: [NSFileHandle fileHandleWithNullDevice]];
  [task setStandardOutput: [NSPipe pipe]];
  [task setStandardError: [NSPipe pipe]];
  if (currentDirectory != nil)
    {
      [task setCurrentDirectoryPath: currentDirectory];
    }
  [task setStandardOutput: stdoutHandle];
  [task setStandardError: stderrHandle];

  @try
    {
      [task launch];
      deadline = [NSDate dateWithTimeIntervalSinceNow: timeout];
      while ([task isRunning])
        {
          if (streamOutput)
            {
              NSData *chunk = nil;

              [stdoutHandle synchronizeFile];
              [stderrHandle synchronizeFile];
              chunk = [self dataFromFileAtPath: stdoutPath offset: &stdoutReadOffset];
              if (chunk != nil && [chunk length] > 0)
                {
                  [[NSFileHandle fileHandleWithStandardOutput] writeData: chunk];
                  fflush(stdout);
                }
              chunk = [self dataFromFileAtPath: stderrPath offset: &stderrReadOffset];
              if (chunk != nil && [chunk length] > 0)
                {
                  [[NSFileHandle fileHandleWithStandardError] writeData: chunk];
                  fflush(stderr);
                }
            }
          if ([[NSDate date] compare: deadline] != NSOrderedAscending)
            {
              timedOut = YES;
              [task terminate];
              break;
            }
          [NSThread sleepForTimeInterval: 0.05];
        }
      [task waitUntilExit];
      if (streamOutput)
        {
          NSData *chunk = nil;

          [stdoutHandle synchronizeFile];
          [stderrHandle synchronizeFile];
          chunk = [self dataFromFileAtPath: stdoutPath offset: &stdoutReadOffset];
          if (chunk != nil && [chunk length] > 0)
            {
              [[NSFileHandle fileHandleWithStandardOutput] writeData: chunk];
              fflush(stdout);
            }
          chunk = [self dataFromFileAtPath: stderrPath offset: &stderrReadOffset];
          if (chunk != nil && [chunk length] > 0)
            {
              [[NSFileHandle fileHandleWithStandardError] writeData: chunk];
              fflush(stderr);
            }
        }
    }
  @catch (NSException *exception)
    {
      [stdoutHandle closeFile];
      [stderrHandle closeFile];
      [[NSFileManager defaultManager] removeItemAtPath: stdoutPath error: NULL];
      [[NSFileManager defaultManager] removeItemAtPath: stderrPath error: NULL];
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            [NSNumber numberWithBool: NO], @"timed_out",
                            @"", @"stdout",
                            [exception reason], @"stderr",
                            nil];
    }

  [stdoutHandle closeFile];
  [stderrHandle closeFile];
  stdoutData = [NSData dataWithContentsOfFile: stdoutPath];
  stderrData = [NSData dataWithContentsOfFile: stderrPath];
  [[NSFileManager defaultManager] removeItemAtPath: stdoutPath error: NULL];
  [[NSFileManager defaultManager] removeItemAtPath: stderrPath error: NULL];

  if (stdoutData != nil && [stdoutData length] > 0)
    {
      stdoutString = [[[NSString alloc] initWithData: stdoutData encoding: NSUTF8StringEncoding] autorelease];
      if (stdoutString == nil)
        {
          stdoutString = @"";
        }
    }
  if (stderrData != nil && [stderrData length] > 0)
    {
      stderrString = [[[NSString alloc] initWithData: stderrData encoding: NSUTF8StringEncoding] autorelease];
      if (stderrString == nil)
        {
          stderrString = @"";
        }
    }
  if (timedOut && [stderrString length] == 0)
    {
      stderrString = [NSString stringWithFormat: @"Command timed out after %.0f seconds.", timeout];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: YES], @"launched",
                        [NSNumber numberWithInt: timedOut ? 124 : [task terminationStatus]], @"exit_status",
                        [NSNumber numberWithBool: timedOut], @"timed_out",
                        stdoutString, @"stdout",
                        stderrString, @"stderr",
                        nil];
}

- (NSDictionary *)launchCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory additionalPathEntries:(NSArray *)additionalPathEntries
{
  NSString *command = nil;
  NSString *launchPath = nil;
  NSArray *taskArguments = nil;
  NSMutableDictionary *taskEnvironment = nil;
  NSTask *task = [[[NSTask alloc] init] autorelease];
  NSMutableArray *pathEntries = [NSMutableArray array];
  NSString *existingPath = nil;

  if (arguments == nil || [arguments count] == 0)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            @"", @"stdout",
                            @"No command arguments were provided.", @"stderr",
                            nil];
    }

  taskEnvironment = [NSMutableDictionary dictionaryWithDictionary: [self managedChildProcessEnvironment]];
  existingPath = [taskEnvironment objectForKey: @"PATH"];
  if ([additionalPathEntries count] > 0)
    {
      [pathEntries addObjectsFromArray: additionalPathEntries];
      if ([existingPath length] > 0)
        {
          [pathEntries addObject: existingPath];
        }
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
      [taskEnvironment setObject: [pathEntries componentsJoinedByString: @";"] forKey: @"PATH"];
#else
      [taskEnvironment setObject: [pathEntries componentsJoinedByString: @":"] forKey: @"PATH"];
#endif
    }

  command = [arguments objectAtIndex: 0];
  launchPath = [self resolvedExecutablePathForCommand: command environment: taskEnvironment];
  taskArguments = [arguments count] > 1 ?
    [arguments subarrayWithRange: NSMakeRange(1, [arguments count] - 1)] :
    [NSArray array];

  if (launchPath == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            @"", @"stdout",
                            [NSString stringWithFormat: @"Executable not found: %@", command], @"stderr",
                            nil];
    }

  [task setLaunchPath: launchPath];
  [task setArguments: taskArguments];
  [task setEnvironment: taskEnvironment];
  [task setStandardInput: [NSFileHandle fileHandleWithStandardInput]];
  [task setStandardOutput: [NSFileHandle fileHandleWithStandardOutput]];
  [task setStandardError: [NSFileHandle fileHandleWithStandardError]];
  if (currentDirectory != nil)
    {
      [task setCurrentDirectoryPath: currentDirectory];
    }

  @try
    {
      [task launch];
    }
  @catch (NSException *exception)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            @"", @"stdout",
                            [exception reason], @"stderr",
                            nil];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: YES], @"launched",
                        [NSNumber numberWithInt: 0], @"exit_status",
                        @"", @"stdout",
                        @"", @"stderr",
                        nil];
}

- (NSDictionary *)interactiveCommand:(NSArray *)arguments currentDirectory:(NSString *)currentDirectory
{
  NSString *command = nil;
  NSString *launchPath = nil;
  NSArray *taskArguments = nil;
  NSDictionary *taskEnvironment = nil;
  NSTask *task = [[[NSTask alloc] init] autorelease];

  if (arguments == nil || [arguments count] == 0)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            @"No command arguments were provided.", @"stderr",
                            nil];
    }

  command = [arguments objectAtIndex: 0];
  taskEnvironment = [self managedChildProcessEnvironment];
  launchPath = [self resolvedExecutablePathForCommand: command environment: taskEnvironment];
  taskArguments = [arguments count] > 1 ?
    [arguments subarrayWithRange: NSMakeRange(1, [arguments count] - 1)] :
    [NSArray array];

  if (launchPath == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            [NSString stringWithFormat: @"Executable not found: %@", command], @"stderr",
                            nil];
    }

  [task setLaunchPath: launchPath];
  [task setArguments: taskArguments];
  [task setEnvironment: taskEnvironment];
  if (currentDirectory != nil)
    {
      [task setCurrentDirectoryPath: currentDirectory];
    }

  @try
    {
      [task launch];
      [task waitUntilExit];
    }
  @catch (NSException *exception)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"launched",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            [exception reason], @"stderr",
                            nil];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: YES], @"launched",
                        [NSNumber numberWithInt: [task terminationStatus]], @"exit_status",
                        @"", @"stderr",
                        nil];
}

- (NSString *)projectPathFromCommandArguments:(NSArray *)arguments
{
  NSUInteger i = 0;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--clean"])
        {
          continue;
        }
      if ([argument isEqualToString: @"--build-system"])
        {
          i++;
          continue;
        }
      if ([argument hasPrefix: @"-"])
        {
          continue;
        }
      return argument;
    }
  return [[NSFileManager defaultManager] currentDirectoryPath];
}

- (NSString *)buildSystemFromCommandArguments:(NSArray *)arguments
{
  NSUInteger i = 0;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--build-system"] && i + 1 < [arguments count])
        {
          return [arguments objectAtIndex: i + 1];
        }
    }
  return @"auto";
}

- (NSDictionary *)projectOperationPhaseWithName:(NSString *)name
                                        backend:(NSString *)backend
                                     invocation:(NSArray *)invocation
                                        project:(NSDictionary *)project
                                   streamOutput:(BOOL)streamOutput
{
  NSDictionary *result = [self runCommand: invocation
                         currentDirectory: [project objectForKey: @"project_dir"]
                                  timeout: 3600.0
                    additionalPathEntries: nil
                             streamOutput: streamOutput];
  BOOL ok = [[result objectForKey: @"exit_status"] intValue] == 0;

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        name, @"name",
                        [NSNumber numberWithBool: ok], @"ok",
                        ok ? @"ok" : @"error", @"status",
                        backend, @"backend",
                        invocation, @"invocation",
                        [result objectForKey: @"stdout"], @"stdout",
                        [result objectForKey: @"stderr"], @"stderr",
                        [result objectForKey: @"exit_status"], @"exit_status",
                        nil];
}

- (NSArray *)runnableProjectsUnderPath:(NSString *)projectPath
{
  return [self runnableProjectsUnderPath: projectPath visited: [NSMutableSet set]];
}

- (NSArray *)runnableProjectsUnderPath:(NSString *)projectPath visited:(NSMutableSet *)visited
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *resolvedProjectPath = [projectPath stringByResolvingSymlinksInPath];
  NSString *gnumakefile = [resolvedProjectPath stringByAppendingPathComponent: @"GNUmakefile"];
  NSDictionary *values = [self parseGNUmakefile: gnumakefile];
  NSString *subprojects = [values objectForKey: @"SUBPROJECTS"];
  NSMutableArray *apps = [NSMutableArray array];
  NSMutableArray *tools = [NSMutableArray array];
  NSArray *subprojectNames = [subprojects componentsSeparatedByCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
  NSUInteger i = 0;

  if ([resolvedProjectPath length] == 0)
    {
      resolvedProjectPath = projectPath;
    }
  if ([visited containsObject: resolvedProjectPath])
    {
      return [NSArray array];
    }
  [visited addObject: resolvedProjectPath];

  for (i = 0; i < [subprojectNames count]; i++)
    {
      NSString *name = [[subprojectNames objectAtIndex: i] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
      NSString *directory = [[resolvedProjectPath stringByAppendingPathComponent: name] stringByResolvingSymlinksInPath];
      NSDictionary *project = nil;
      NSString *projectType = nil;
      NSArray *nested = nil;
      NSUInteger nestedIndex = 0;

      if ([directory length] == 0)
        {
          directory = [resolvedProjectPath stringByAppendingPathComponent: name];
        }
      if ([name length] == 0 || [name hasPrefix: @"#"])
        {
          continue;
        }

      if ([manager fileExistsAtPath: [directory stringByAppendingPathComponent: @"GNUmakefile"]] == NO)
        {
          continue;
        }

      project = [self detectProjectAtPath: directory];
      if ([[project objectForKey: @"supported"] boolValue] == NO)
        {
          continue;
        }

      projectType = [project objectForKey: @"project_type"];
      if ([projectType isEqualToString: @"app"])
        {
          [apps addObject: project];
        }
      else if ([projectType isEqualToString: @"tool"])
        {
          [tools addObject: project];
        }
      nested = [self runnableProjectsUnderPath: directory visited: visited];
      for (nestedIndex = 0; nestedIndex < [nested count]; nestedIndex++)
        {
          NSDictionary *nestedProject = [nested objectAtIndex: nestedIndex];
          NSString *nestedType = [nestedProject objectForKey: @"project_type"];
          if ([nestedType isEqualToString: @"app"])
            {
              [apps addObject: nestedProject];
            }
          else if ([nestedType isEqualToString: @"tool"])
            {
              [tools addObject: nestedProject];
            }
        }
    }

  if ([apps count] > 0)
    {
      return apps;
    }
  return tools;
}

- (NSArray *)projectRuntimePathEntriesUnderPath:(NSString *)projectPath
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDirectoryEnumerator *enumerator = [manager enumeratorAtPath: projectPath];
  NSMutableArray *entries = [NSMutableArray array];
  NSMutableSet *seen = [NSMutableSet set];
  NSString *relativePath = nil;

  while ((relativePath = [enumerator nextObject]) != nil)
    {
      NSString *name = [relativePath lastPathComponent];
      NSString *directory = nil;
      if ([name isEqualToString: @"obj"] == NO
          && [name hasSuffix: @".framework"] == NO
          && [name hasSuffix: @".app"] == NO
          && [name hasSuffix: @".plugin"] == NO
          && [name hasSuffix: @".palette"] == NO
          && [[name pathExtension] isEqualToString: @"dll"] == NO)
        {
          continue;
        }
      if ([[name pathExtension] isEqualToString: @"dll"] == NO)
        {
          continue;
        }
      directory = [[projectPath stringByAppendingPathComponent: relativePath] stringByDeletingLastPathComponent];
      if ([seen containsObject: directory] == NO)
        {
          [seen addObject: directory];
          [entries addObject: directory];
        }
    }

  return entries;
}

- (NSString *)singleQuotedShellString:(NSString *)string
{
  return [NSString stringWithFormat: @"'%@'",
                   [string stringByReplacingOccurrencesOfString: @"'"
                                                     withString: @"'\"'\"'"]];
}

- (NSString *)singleQuotedPowerShellString:(NSString *)string
{
  return [NSString stringWithFormat: @"'%@'",
                   [string stringByReplacingOccurrencesOfString: @"'"
                                                     withString: @"''"]];
}

- (NSString *)windowsStartBashCommandForBash:(NSString *)bash command:(NSString *)command
{
  return [NSString stringWithFormat: @"Start-Process -WindowStyle Hidden -FilePath %@ -ArgumentList '-lc', %@",
                   [self singleQuotedPowerShellString: bash],
                   [self singleQuotedPowerShellString: command]];
}

- (NSString *)windowsStartBashScriptCommandForBash:(NSString *)bash scriptPath:(NSString *)scriptPath
{
  return [NSString stringWithFormat: @"Start-Process -WindowStyle Hidden -FilePath %@ -ArgumentList %@",
                   [self singleQuotedPowerShellString: bash],
                   [self singleQuotedPowerShellString: scriptPath]];
}

- (NSString *)writeWindowsOpenAppLaunchScriptForCommand:(NSString *)command
{
  NSString *scriptName = [NSString stringWithFormat: @"gnustep-run-%d-%u.sh",
                                   (int)[[NSProcessInfo processInfo] processIdentifier],
                                   (unsigned int)[[NSDate date] timeIntervalSince1970]];
  NSString *scriptPath = [NSTemporaryDirectory() stringByAppendingPathComponent: scriptName];
  NSString *content = [NSString stringWithFormat: @"#!/usr/bin/env bash\n%@\n", command];

  if ([content writeToFile: scriptPath atomically: YES encoding: NSUTF8StringEncoding error: NULL] == NO)
    {
      return nil;
    }
  return scriptPath;
}

- (NSString *)windowsOpenAppLaunchCommandForProject:(NSDictionary *)runProject runtimePathEntries:(NSArray *)runtimePathEntries
{
  NSString *projectDir = [self singleQuotedShellString: [runProject objectForKey: @"project_dir"]];
  NSString *targetName = [runProject objectForKey: @"target_name"];
  NSString *appPath = [self singleQuotedShellString: [NSString stringWithFormat: @"./%@.app", targetName]];
  NSMutableArray *pathEntries = [NSMutableArray arrayWithObjects: @"/clang64/bin", @"/usr/bin", nil];
  NSUInteger i = 0;

  for (i = 0; i < [runtimePathEntries count]; i++)
    {
      [pathEntries addObject: [NSString stringWithFormat: @"$(cygpath -u %@)",
                                        [self singleQuotedShellString: [runtimePathEntries objectAtIndex: i]]]];
    }
  [pathEntries addObject: @"$PATH"];

  return [NSString stringWithFormat: @"cd \"$(cygpath -u %@)\" && . /clang64/share/GNUstep/Makefiles/GNUstep.sh && export PATH=\"%@\" && /clang64/bin/openapp %@",
                   projectDir,
                   [pathEntries componentsJoinedByString: @":"],
                   appPath];
}

- (NSDictionary *)runnableProjectForProject:(NSDictionary *)project
{
  NSString *projectType = [project objectForKey: @"project_type"];
  NSArray *candidates = nil;

  if ([projectType isEqualToString: @"app"] || [projectType isEqualToString: @"tool"])
    {
      return project;
    }

  candidates = [self runnableProjectsUnderPath: [project objectForKey: @"project_dir"]];
  if ([candidates count] == 1)
    {
      return [candidates objectAtIndex: 0];
    }
  return nil;
}

- (NSDictionary *)checkWithID:(NSString *)checkID
                         title:(NSString *)title
                        status:(NSString *)status
                      severity:(NSString *)severity
                       message:(NSString *)message
                     interface:(NSString *)interface
                executionTier:(NSString *)executionTier
                       details:(NSDictionary *)details
{
  NSMutableDictionary *payload = [NSMutableDictionary dictionaryWithObjectsAndKeys:
                                                       checkID, @"id",
                                                       title, @"title",
                                                       status, @"status",
                                                       severity, @"severity",
                                                       message, @"message",
                                                       nil];
  if (interface != nil)
    {
      [payload setObject: interface forKey: @"interface"];
    }
  if (executionTier != nil)
    {
      [payload setObject: executionTier forKey: @"execution_tier"];
    }
  if (details != nil && [details count] > 0)
    {
      [payload setObject: details forKey: @"details"];
    }
  return payload;
}

- (NSDictionary *)actionWithKind:(NSString *)kind
                         message:(NSString *)message
                        priority:(int)priority
{
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        kind, @"kind",
                        [NSNumber numberWithInt: priority], @"priority",
                        message, @"message",
                        nil];
}

- (NSString *)firstAvailableExecutable:(NSArray *)names
{
  NSUInteger i = 0;
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *pathVariable = [[[NSProcessInfo processInfo] environment] objectForKey: @"PATH"];
  NSArray *pathEntries = pathVariable ?
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
    [pathVariable componentsSeparatedByString: @";"] :
#else
    [pathVariable componentsSeparatedByString: @":"] :
#endif
    [NSArray array];

  for (i = 0; i < [names count]; i++)
    {
      NSString *name = [names objectAtIndex: i];
      NSUInteger j = 0;
      for (j = 0; j < [pathEntries count]; j++)
        {
          NSString *candidate = [[pathEntries objectAtIndex: j] stringByAppendingPathComponent: name];
          if ([manager isExecutableFileAtPath: candidate])
            {
              return candidate;
            }
        }
    }
  return nil;
}

- (NSDictionary *)parseGNUmakefile:(NSString *)path
{
  NSString *content = [NSString stringWithContentsOfFile: path
                                                encoding: NSUTF8StringEncoding
                                                   error: NULL];
  NSMutableDictionary *values = [NSMutableDictionary dictionary];
  NSArray *lines = nil;
  NSUInteger i = 0;

  if (content == nil)
    {
      return values;
    }
  if ([content rangeOfString: @"aggregate.make"].location != NSNotFound)
    {
      [values setObject: @"true" forKey: @"__contains_aggregate_make"];
    }
  lines = [content componentsSeparatedByString: @"\n"];
  for (i = 0; i < [lines count]; i++)
    {
      NSString *line = [[lines objectAtIndex: i] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
      NSRange range = NSMakeRange(NSNotFound, 0);
      NSString *key = nil;
      NSString *value = nil;

      if ([line length] == 0 || [line hasPrefix: @"#"])
        {
          continue;
        }
      range = [line rangeOfString: @"="];
      if (range.location == NSNotFound)
        {
          continue;
        }
      key = [[line substringToIndex: range.location] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
      value = [[line substringFromIndex: range.location + 1] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
      while ([value hasSuffix: @"\\"] && i + 1 < [lines count])
        {
          NSString *next = [[lines objectAtIndex: ++i] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
          BOOL continues = [next hasSuffix: @"\\"];
          value = [[value substringToIndex: [value length] - 1] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
          next = [next stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
          if (continues)
            {
              next = [[next substringToIndex: [next length] - 1] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
            }
          value = [[NSString stringWithFormat: @"%@ %@%@", value, next, continues ? @" \\" : @""]
            stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
          if (continues == NO)
            {
              break;
            }
        }
      if (key != nil && value != nil)
        {
          [values setObject: value forKey: key];
        }
    }
  return values;
}

- (NSDictionary *)detectProjectAtPath:(NSString *)projectPath
{
  NSString *root = [projectPath stringByResolvingSymlinksInPath];
  NSString *gnumakefile = [root stringByAppendingPathComponent: @"GNUmakefile"];
  NSDictionary *values = nil;
  NSString *projectType = nil;
  NSString *targetName = nil;

  if ([[NSFileManager defaultManager] fileExistsAtPath: gnumakefile] == NO)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"supported",
                            @"missing_gnumakefile", @"reason",
                            root, @"project_dir",
                            nil];
    }

  values = [self parseGNUmakefile: gnumakefile];
  targetName = [values objectForKey: @"TOOL_NAME"];
  if (targetName != nil)
    {
      projectType = @"tool";
    }
  else
    {
      targetName = [values objectForKey: @"APP_NAME"];
      if (targetName != nil)
        {
          projectType = @"app";
        }
      else
        {
          targetName = [values objectForKey: @"LIBRARY_NAME"];
          if (targetName != nil)
            {
              projectType = @"library";
            }
        }
    }

  if (projectType == nil)
    {
      if ([values objectForKey: @"SUBPROJECTS"] != nil || [[values objectForKey: @"__contains_aggregate_make"] isEqualToString: @"true"])
        {
          projectType = @"aggregate";
        }
      else
        {
          projectType = @"unknown";
        }
    }

  {
    NSMutableDictionary *project = [NSMutableDictionary dictionaryWithObjectsAndKeys:
      [NSNumber numberWithBool: YES], @"supported",
      root, @"project_dir",
      gnumakefile, @"gnumakefile",
      projectType, @"project_type",
      @"gnustep-make", @"build_system",
      @"gnumakefile_marker", @"detection_reason",
      nil];
    if (targetName != nil)
      {
        [project setObject: targetName forKey: @"target_name"];
      }
    else
      {
        [project setObject: [NSNull null] forKey: @"target_name"];
      }
    return project;
  }
}

- (NSString *)sha256ForFile:(NSString *)path
{
  NSString *nativeHash = GSSHA256ForFileAtPath(path);
  NSString *powershellCommand = [NSString stringWithFormat: @"powershell -NoProfile -Command \"(Get-FileHash -Algorithm SHA256 -LiteralPath '%@').Hash.ToLowerInvariant()\"", path];
  NSString *certutilCommand = [NSString stringWithFormat: @"certutil -hashfile \"%@\" SHA256", path];
  NSArray *commands = [NSArray arrayWithObjects:
                                 [NSArray arrayWithObjects: @"cmd.exe", @"/c", powershellCommand, nil],
                                 [NSArray arrayWithObjects: @"cmd.exe", @"/c", certutilCommand, nil],
                                 [NSArray arrayWithObjects: @"sha256sum.exe", path, nil],
                                 [NSArray arrayWithObjects: @"sha256sum", path, nil],
                                 [NSArray arrayWithObjects: @"shasum", @"-a", @"256", path, nil],
                                 [NSArray arrayWithObjects: @"openssl", @"dgst", @"-sha256", path, nil],
                                 nil];
  NSUInteger i = 0;

  if (nativeHash != nil)
    {
      return nativeHash;
    }

  for (i = 0; i < [commands count]; i++)
    {
      NSDictionary *result = [self runCommand: [commands objectAtIndex: i] currentDirectory: nil];
      if ([[result objectForKey: @"launched"] boolValue] &&
          [[result objectForKey: @"exit_status"] intValue] == 0)
        {
          NSString *output = [[result objectForKey: @"stdout"] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
          NSArray *parts = [output componentsSeparatedByCharactersInSet: [NSCharacterSet whitespaceCharacterSet]];
          NSUInteger j = 0;
          for (j = 0; j < [parts count]; j++)
            {
              NSString *part = [parts objectAtIndex: j];
              if ([part length] == 64)
                {
                  return part;
                }
            }
        }
    }
  return nil;
}

- (BOOL)extractArchive:(NSString *)archivePath toDirectory:(NSString *)destination error:(NSString **)errorMessage
{
  NSDictionary *result = nil;
  NSFileManager *manager = [NSFileManager defaultManager];

  [manager createDirectoryAtPath: destination withIntermediateDirectories: YES attributes: nil error: NULL];
  if ([[archivePath lowercaseString] hasSuffix: @".zip"])
    {
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
      NSArray *windowsExtractors = [NSArray arrayWithObjects:
        [NSArray arrayWithObjects: @"C:/Windows/System32/tar.exe", @"-xf", archivePath, @"-C", destination, nil],
        [NSArray arrayWithObjects:
                   @"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                   @"-NoProfile",
                   @"-ExecutionPolicy",
                   @"Bypass",
                   @"-Command",
                   @"Expand-Archive -LiteralPath $args[0] -DestinationPath $args[1] -Force",
                   archivePath,
                   destination,
                   nil],
        [NSArray arrayWithObjects:
                   @"powershell.exe",
                   @"-NoProfile",
                   @"-ExecutionPolicy",
                   @"Bypass",
                   @"-Command",
                   @"Expand-Archive -LiteralPath $args[0] -DestinationPath $args[1] -Force",
                   archivePath,
                   destination,
                   nil],
        [NSArray arrayWithObjects: @"unzip", @"-q", archivePath, @"-d", destination, nil],
        nil];
      NSUInteger extractorIndex = 0;
      for (extractorIndex = 0; extractorIndex < [windowsExtractors count]; extractorIndex++)
        {
          result = [self runCommand: [windowsExtractors objectAtIndex: extractorIndex] currentDirectory: nil];
          if ([[result objectForKey: @"launched"] boolValue] &&
              [[result objectForKey: @"exit_status"] intValue] == 0)
            {
              break;
            }
        }
#else
      result = [self runCommand: [NSArray arrayWithObjects: @"unzip", @"-q", archivePath, @"-d", destination, nil]
               currentDirectory: nil];
#endif
    }
  else
    {
      result = [self runCommand: [NSArray arrayWithObjects: @"tar", @"-xzf", archivePath, @"-C", destination, nil]
               currentDirectory: nil];
    }

  if ([[result objectForKey: @"launched"] boolValue] == NO ||
      [[result objectForKey: @"exit_status"] intValue] != 0)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [result objectForKey: @"stderr"];
        }
      return NO;
    }
  return YES;
}

- (NSString *)singleChildDirectoryOrSelf:(NSString *)path
{
  NSArray *children = [[NSFileManager defaultManager] contentsOfDirectoryAtPath: path error: NULL];
  if ([children count] == 1)
    {
      NSString *childName = [children objectAtIndex: 0];
      NSString *child = [path stringByAppendingPathComponent: childName];
      BOOL isDir = NO;
      NSArray *layoutDirectories = [NSArray arrayWithObjects:
                                             @"bin",
                                             @"Tools",
                                             @"System",
                                             @"Local",
                                             @"Library",
                                             @"lib",
                                             @"lib64",
                                             @"share",
                                             nil];
      if ([layoutDirectories containsObject: childName])
        {
          return path;
        }
      if ([[NSFileManager defaultManager] fileExistsAtPath: child isDirectory: &isDir] && isDir)
        {
          return child;
        }
    }
  return path;
}

- (BOOL)copyTreeContentsFrom:(NSString *)source to:(NSString *)destination error:(NSString **)errorMessage
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDirectoryEnumerator *enumerator = nil;
  NSString *relative = nil;

  [manager createDirectoryAtPath: destination withIntermediateDirectories: YES attributes: nil error: NULL];
  enumerator = [manager enumeratorAtPath: source];
  while ((relative = [enumerator nextObject]) != nil)
    {
      NSString *sourcePath = [source stringByAppendingPathComponent: relative];
      NSString *targetPath = [destination stringByAppendingPathComponent: relative];
      BOOL isDir = NO;

      [manager fileExistsAtPath: sourcePath isDirectory: &isDir];
      if (isDir)
        {
          [manager createDirectoryAtPath: targetPath withIntermediateDirectories: YES attributes: nil error: NULL];
        }
      else
        {
          [manager createDirectoryAtPath: [targetPath stringByDeletingLastPathComponent]
             withIntermediateDirectories: YES
                              attributes: nil
                                   error: NULL];
          [manager removeItemAtPath: targetPath error: NULL];
          if ([manager copyItemAtPath: sourcePath toPath: targetPath error: NULL] == NO)
            {
              if (errorMessage != NULL)
                {
                  *errorMessage = [NSString stringWithFormat: @"Failed to copy %@", relative];
                }
              return NO;
            }
        }
    }
  return YES;
}


- (NSDate *)dateFromManifestTimestamp:(NSString *)timestamp
{
  NSString *normalized = nil;
  NSDateFormatter *formatter = nil;
  NSRange dotRange;

  if ([timestamp isKindOfClass: [NSString class]] == NO || [timestamp length] == 0 || [timestamp isEqualToString: @"TBD"])
    {
      return nil;
    }

  normalized = timestamp;
  dotRange = [normalized rangeOfString: @"."];
  if (dotRange.location != NSNotFound)
    {
      NSRange zRange = [normalized rangeOfString: @"Z" options: NSBackwardsSearch];
      if (zRange.location != NSNotFound && zRange.location > dotRange.location)
        {
          normalized = [[normalized substringToIndex: dotRange.location] stringByAppendingString: @"Z"];
        }
    }

  formatter = [[[NSDateFormatter alloc] init] autorelease];
  [formatter setLocale: [[[NSLocale alloc] initWithLocaleIdentifier: @"en_US_POSIX"] autorelease]];
  [formatter setTimeZone: [NSTimeZone timeZoneForSecondsFromGMT: 0]];
  [formatter setDateFormat: @"yyyy-MM-dd'T'HH:mm:ss'Z'"];
  return [formatter dateFromString: normalized];
}

- (BOOL)manifestMetadataPolicyAllowsManifest:(NSDictionary *)manifest error:(NSString **)errorMessage
{
  id metadataVersion = [manifest objectForKey: @"metadata_version"];
  NSString *expiresAt = [manifest objectForKey: @"expires_at"];
  NSDate *expiry = nil;

  if (metadataVersion != nil && [metadataVersion intValue] < 1)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Unsupported release metadata version.";
        }
      return NO;
    }

  expiry = [self dateFromManifestTimestamp: expiresAt];
  if (expiry != nil && [expiry compare: [NSDate date]] != NSOrderedDescending)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Release manifest metadata is expired.";
        }
      return NO;
    }

  return YES;
}

- (BOOL)manifest:(NSDictionary *)manifest revokesArtifacts:(NSArray *)artifacts error:(NSString **)errorMessage
{
  NSDictionary *trust = [manifest objectForKey: @"trust"];
  NSArray *revoked = [trust objectForKey: @"revoked_artifacts"];
  NSUInteger i = 0;

  if ([revoked isKindOfClass: [NSArray class]] == NO)
    {
      return NO;
    }

  for (i = 0; i < [artifacts count]; i++)
    {
      NSString *artifactID = [[artifacts objectAtIndex: i] objectForKey: @"id"];
      if (artifactID != nil && [revoked containsObject: artifactID])
        {
          if (errorMessage != NULL)
            {
              *errorMessage = [NSString stringWithFormat: @"Release manifest references revoked artifact %@.", artifactID];
            }
          return YES;
        }
    }
  return NO;
}

- (BOOL)manifest:(NSDictionary *)manifest isOlderThanInstalledState:(NSDictionary *)installedState error:(NSString **)errorMessage
{
  id metadataVersion = [manifest objectForKey: @"metadata_version"];
  id lastMetadataVersion = [installedState objectForKey: @"last_manifest_metadata_version"];
  NSDate *generatedAt = [self dateFromManifestTimestamp: [manifest objectForKey: @"generated_at"]];
  NSDate *lastGeneratedAt = [self dateFromManifestTimestamp: [installedState objectForKey: @"last_manifest_generated_at"]];

  if ([metadataVersion respondsToSelector: @selector(intValue)] &&
      [lastMetadataVersion respondsToSelector: @selector(intValue)] &&
      [metadataVersion intValue] < [lastMetadataVersion intValue])
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Release manifest metadata version is older than the last accepted metadata.";
        }
      return YES;
    }

  if (generatedAt != nil && lastGeneratedAt != nil && [generatedAt compare: lastGeneratedAt] == NSOrderedAscending)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Release manifest metadata is older than the last accepted manifest.";
        }
      return YES;
    }

  return NO;
}

- (NSComparisonResult)compareVersionString:(NSString *)left toVersionString:(NSString *)right
{
  NSArray *leftParts = [left componentsSeparatedByString: @"."];
  NSArray *rightParts = [right componentsSeparatedByString: @"."];
  NSUInteger maxCount = [leftParts count] > [rightParts count] ? [leftParts count] : [rightParts count];
  NSUInteger i = 0;

  if (left == nil && right == nil)
    {
      return NSOrderedSame;
    }
  if (left == nil)
    {
      return NSOrderedAscending;
    }
  if (right == nil)
    {
      return NSOrderedDescending;
    }

  for (i = 0; i < maxCount; i++)
    {
      NSString *leftPart = i < [leftParts count] ? [leftParts objectAtIndex: i] : @"0";
      NSString *rightPart = i < [rightParts count] ? [rightParts objectAtIndex: i] : @"0";
      NSInteger leftValue = [leftPart integerValue];
      NSInteger rightValue = [rightPart integerValue];
      if (leftValue < rightValue)
        {
          return NSOrderedAscending;
        }
      if (leftValue > rightValue)
        {
          return NSOrderedDescending;
        }
      if ([leftPart integerValue] == 0 && [rightPart integerValue] == 0 && [leftPart isEqualToString: rightPart] == NO)
        {
          NSComparisonResult lexical = [leftPart compare: rightPart];
          if (lexical != NSOrderedSame)
            {
              return lexical;
            }
        }
    }
  return NSOrderedSame;
}

- (NSDictionary *)validateAndLoadManifest:(NSString *)manifestPath error:(NSString **)errorMessage
{
  NSDictionary *manifest = [self readJSONFile: manifestPath error: errorMessage];
  NSArray *releases = nil;

  if (manifest == nil)
    {
      return nil;
    }
  if ([[manifest objectForKey: @"schema_version"] intValue] != 1)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Unsupported release manifest schema version.";
        }
      return nil;
    }
  releases = [manifest objectForKey: @"releases"];
  if ([releases isKindOfClass: [NSArray class]] == NO || [releases count] == 0)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Release manifest does not define any releases.";
        }
      return nil;
    }
  if ([self manifestMetadataPolicyAllowsManifest: manifest error: errorMessage] == NO)
    {
      return nil;
    }

  return manifest;
}

- (NSDictionary *)selectReleaseFromManifest:(NSDictionary *)manifest
{
  NSArray *releases = [manifest objectForKey: @"releases"];
  NSUInteger i = 0;
  for (i = 0; i < [releases count]; i++)
    {
      NSDictionary *release = [releases objectAtIndex: i];
      if ([[release objectForKey: @"status"] isEqualToString: @"active"])
        {
          return release;
        }
    }
  return [releases objectAtIndex: 0];
}

- (BOOL)artifact:(NSDictionary *)artifact matchesHostOS:(NSString *)osName arch:(NSString *)arch
{
  return [[artifact objectForKey: @"os"] isEqualToString: osName] &&
         [[artifact objectForKey: @"arch"] isEqualToString: arch];
}

- (BOOL)artifact:(NSDictionary *)artifact matchesDistributionForEnvironment:(NSDictionary *)environment
{
  id supportedDistributions = [artifact objectForKey: @"supported_distributions"];
  id supportedOSVersions = [artifact objectForKey: @"supported_os_versions"];
  id osName = [environment objectForKey: @"os"];
  id distributionID = [environment objectForKey: @"distribution_id"];
  id osVersion = [environment objectForKey: @"os_version"];

  if ([osName isEqual: @"linux"] == NO)
    {
      return YES;
    }
  if (supportedDistributions != nil &&
      supportedDistributions != [NSNull null] &&
      [supportedDistributions isKindOfClass: [NSArray class]] &&
      [supportedDistributions count] > 0)
    {
      if (distributionID == nil || distributionID == [NSNull null] ||
          [supportedDistributions containsObject: distributionID] == NO)
        {
          return NO;
        }
    }
  if (supportedOSVersions != nil &&
      supportedOSVersions != [NSNull null] &&
      [supportedOSVersions isKindOfClass: [NSArray class]] &&
      [supportedOSVersions count] > 0)
    {
      if (osVersion == nil || osVersion == [NSNull null] ||
          [supportedOSVersions containsObject: osVersion] == NO)
        {
          return NO;
        }
    }
  return YES;
}

- (BOOL)artifact:(NSDictionary *)artifact matchesToolchain:(NSDictionary *)toolchain
{
  NSArray *fields = [NSArray arrayWithObjects:
                               @"compiler_family",
                               @"toolchain_flavor",
                               @"objc_runtime",
                               @"objc_abi",
                               nil];
  NSDictionary *featureFlags = [toolchain objectForKey: @"feature_flags"];
  NSArray *requiredFeatures = [artifact objectForKey: @"required_features"];
  NSUInteger i = 0;

  if (requiredFeatures != nil && (id)requiredFeatures != (id)[NSNull null] &&
      [requiredFeatures isKindOfClass: [NSArray class]] == NO)
    {
      return NO;
    }

  if ([[toolchain objectForKey: @"present"] boolValue] == NO)
    {
      return NO;
    }

  for (i = 0; i < [fields count]; i++)
    {
      NSString *field = [fields objectAtIndex: i];
      id expected = [artifact objectForKey: field];
      id detected = [toolchain objectForKey: field];
      if (expected == nil || expected == [NSNull null] || [expected isEqual: @"unknown"])
        {
          continue;
        }
      if (detected == nil || detected == [NSNull null] || [detected isEqual: @"unknown"])
        {
          return NO;
        }
      if ([expected isEqual: detected] == NO)
        {
          return NO;
        }
    }

  [self appendInstallTrace: @"requirements feature lists ok"];
  for (i = 0; i < [requiredFeatures count]; i++)
    {
      NSString *feature = [requiredFeatures objectAtIndex: i];
      if ([[featureFlags objectForKey: feature] boolValue] == NO)
        {
          return NO;
        }
    }
  return YES;
}

- (NSDictionary *)selectedArtifactOfKind:(NSString *)kind
                              fromRelease:(NSDictionary *)release
                              environment:(NSDictionary *)environment
                           selectionError:(NSString **)selectionError
{
  NSArray *artifacts = [release objectForKey: @"artifacts"];
  NSMutableArray *candidates = [NSMutableArray array];
  NSMutableArray *matching = [NSMutableArray array];
  NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
  NSUInteger i = 0;

  for (i = 0; i < [artifacts count]; i++)
    {
      NSDictionary *artifact = [artifacts objectAtIndex: i];
      if ([[artifact objectForKey: @"kind"] isEqualToString: kind] &&
          [self artifact: artifact
            matchesHostOS: [environment objectForKey: @"os"]
                    arch: [environment objectForKey: @"arch"]] &&
          [self artifact: artifact matchesDistributionForEnvironment: environment])
        {
          [candidates addObject: artifact];
        }
    }

  if ([candidates count] == 0)
    {
      return nil;
    }
  if ([candidates count] == 1)
    {
      return [candidates objectAtIndex: 0];
    }

  for (i = 0; i < [candidates count]; i++)
    {
      NSDictionary *artifact = [candidates objectAtIndex: i];
      if ([self artifact: artifact matchesToolchain: toolchain])
        {
          [matching addObject: artifact];
        }
    }

  if ([matching count] == 1)
    {
      return [matching objectAtIndex: 0];
    }

  if (selectionError != NULL)
    {
      if ([matching count] > 1)
        {
          *selectionError = [NSString stringWithFormat:
                                       @"Multiple %@ artifacts match the detected host and toolchain; selection is ambiguous.",
                                       kind];
        }
      else
        {
          *selectionError = [NSString stringWithFormat:
                                       @"Multiple %@ artifacts match the detected host, but the current environment does not identify a unique target.",
                                       kind];
        }
    }
  return nil;
}

- (NSArray *)selectedArtifactsForRelease:(NSDictionary *)release
                             environment:(NSDictionary *)environment
                         selectionErrors:(NSArray **)selectionErrors
{
  NSArray *order = [NSArray arrayWithObjects: @"cli", @"toolchain", nil];
  NSMutableArray *ordered = [NSMutableArray array];
  NSMutableArray *errors = [NSMutableArray array];
  NSUInteger i = 0;

  for (i = 0; i < [order count]; i++)
    {
      NSString *kind = [order objectAtIndex: i];
      NSString *selectionError = nil;
      NSDictionary *artifact = [self selectedArtifactOfKind: kind
                                                fromRelease: release
                                                environment: environment
                                             selectionError: &selectionError];
      if (artifact != nil)
        {
          [ordered addObject: artifact];
        }
      else if (selectionError != nil)
        {
          [errors addObject: selectionError];
        }
    }

  if (selectionErrors != NULL)
    {
      *selectionErrors = errors;
    }
  return ordered;
}

- (NSString *)normalizeOSName
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  return @"windows";
#else
  NSString *osName = [[NSProcessInfo processInfo] operatingSystemVersionString];
  NSDictionary *env = [[NSProcessInfo processInfo] environment];
  NSString *ostype = [[env objectForKey: @"OSTYPE"] lowercaseString];
  NSDictionary *unameResult = [self runCommand: [NSArray arrayWithObjects: @"uname", @"-s", nil] currentDirectory: nil];
  NSString *unameName = [[[[unameResult objectForKey: @"stdout"] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]] lowercaseString] copy];
  [unameName autorelease];
  if ((ostype != nil && [ostype rangeOfString: @"openbsd"].location != NSNotFound) ||
      [unameName rangeOfString: @"openbsd"].location != NSNotFound)
    {
      return @"openbsd";
    }
  if ([osName rangeOfString: @"Linux"].location != NSNotFound ||
      [unameName rangeOfString: @"linux"].location != NSNotFound ||
      [[NSFileManager defaultManager] fileExistsAtPath: @"/etc/os-release"])
    {
      return @"linux";
    }
  return @"unknown";
#endif
}

- (NSString *)normalizeArchName
{
  NSString *arch = nil;
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  arch = [[[[NSProcessInfo processInfo] environment] objectForKey: @"PROCESSOR_ARCHITECTURE"] lowercaseString];
  if ([arch length] == 0)
    {
      arch = [[[[NSProcessInfo processInfo] environment] objectForKey: @"PROCESSOR_ARCHITEW6432"] lowercaseString];
    }
#else
  NSDictionary *result = [self runCommand: [NSArray arrayWithObjects: @"uname", @"-m", nil] currentDirectory: nil];
  arch = [[[result objectForKey: @"stdout"] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]] lowercaseString];
#endif
  if ([arch isEqualToString: @"x86_64"] || [arch isEqualToString: @"amd64"])
    {
      return @"amd64";
    }
  if ([arch isEqualToString: @"aarch64"] || [arch isEqualToString: @"arm64"])
    {
      return @"arm64";
    }
  return [arch length] > 0 ? arch : @"unknown";
}

- (NSString *)readOSReleaseIdentifier
{
  NSString *path = @"/etc/os-release";
  NSString *content = nil;
  NSArray *lines = nil;
  NSMutableDictionary *values = [NSMutableDictionary dictionary];
  NSUInteger i = 0;

  if ([[NSFileManager defaultManager] fileExistsAtPath: path] == NO)
    {
      return nil;
    }
  content = [NSString stringWithContentsOfFile: path encoding: NSUTF8StringEncoding error: NULL];
  if (content == nil)
    {
      return nil;
    }
  lines = [content componentsSeparatedByString: @"\n"];
  for (i = 0; i < [lines count]; i++)
    {
      NSString *line = [lines objectAtIndex: i];
      NSRange equalsRange = [line rangeOfString: @"="];
      if ([line hasPrefix: @"#"] || equalsRange.location == NSNotFound)
        {
          continue;
        }
      [values setObject: [[[line substringFromIndex: equalsRange.location + 1]
                            stringByTrimmingCharactersInSet: [NSCharacterSet characterSetWithCharactersInString: @"\""]]
                           stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceCharacterSet]]
                  forKey: [line substringToIndex: equalsRange.location]];
    }
  if ([values objectForKey: @"VERSION_ID"] != nil)
    {
      return [NSString stringWithFormat: @"%@-%@",
                        [values objectForKey: @"ID"] ? [values objectForKey: @"ID"] : @"linux",
                        [values objectForKey: @"VERSION_ID"]];
    }
  if ([values objectForKey: @"VERSION_CODENAME"] != nil)
    {
      return [NSString stringWithFormat: @"%@-%@",
                        [values objectForKey: @"ID"] ? [values objectForKey: @"ID"] : @"linux",
                        [values objectForKey: @"VERSION_CODENAME"]];
    }
  return [values objectForKey: @"ID"];
}

- (NSDictionary *)compilerInfoForExecutable:(NSString *)compilerExecutable
{
  NSString *compilerPath = compilerExecutable ? [self resolvedExecutablePathForCommand: compilerExecutable] : nil;
  if (compilerPath == nil && compilerExecutable != nil && [compilerExecutable rangeOfString: @"/"].location != NSNotFound)
    {
      compilerPath = compilerExecutable;
    }
  if (compilerPath == nil)
    {
      compilerPath = [self firstAvailableExecutable: [NSArray arrayWithObjects: @"clang", @"gcc", @"cc", nil]];
    }
  NSString *compilerFamily = nil;
  NSString *compilerVersion = nil;
  NSString *firstLine = @"";
  NSDictionary *result = nil;
  NSArray *parts = nil;
  NSUInteger i = 0;

  if (compilerPath == nil)
    {
      return [NSDictionary dictionary];
    }

  result = [self runCommand: [NSArray arrayWithObjects: compilerPath, @"--version", nil] currentDirectory: nil];
  if ([[result objectForKey: @"launched"] boolValue])
    {
      NSArray *lines = [[result objectForKey: @"stdout"] length] > 0 ?
        [[result objectForKey: @"stdout"] componentsSeparatedByString: @"\n"] :
        [[result objectForKey: @"stderr"] componentsSeparatedByString: @"\n"];
      if ([lines count] > 0)
        {
          firstLine = [lines objectAtIndex: 0];
        }
    }

  if ([[firstLine lowercaseString] rangeOfString: @"clang"].location != NSNotFound ||
      [[compilerPath lastPathComponent] rangeOfString: @"clang"].location != NSNotFound)
    {
      compilerFamily = @"clang";
    }
  else
    {
      compilerFamily = @"gcc";
    }

  parts = [[firstLine stringByReplacingOccurrencesOfString: @"(" withString: @" "]
              componentsSeparatedByString: @" "];
  for (i = 0; i < [parts count]; i++)
    {
      NSString *part = [parts objectAtIndex: i];
      if ([part length] > 0 && [[NSCharacterSet decimalDigitCharacterSet] characterIsMember: [part characterAtIndex: 0]])
        {
          compilerVersion = part;
          break;
        }
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        compilerPath, @"path",
                        compilerFamily, @"family",
                        compilerVersion ? compilerVersion : @"unknown", @"version",
                        nil];
}

- (NSDictionary *)compilerInfo
{
  return [self compilerInfoForExecutable: nil];
}

- (NSString *)gnustepMakeCompilerPathWithConfig:(NSString *)gnustepConfig
{
  NSDictionary *result = nil;
  NSString *compiler = nil;
  NSArray *parts = nil;

  if (gnustepConfig == nil)
    {
      return nil;
    }

  result = [self runCommand: [NSArray arrayWithObjects: gnustepConfig, @"--variable=CC", nil] currentDirectory: nil];
  if ([[result objectForKey: @"exit_status"] intValue] != 0)
    {
      return nil;
    }

  compiler = [[result objectForKey: @"stdout"] stringByTrimmingCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
  if ([compiler length] == 0)
    {
      return nil;
    }

  parts = [compiler componentsSeparatedByCharactersInSet: [NSCharacterSet whitespaceAndNewlineCharacterSet]];
  if ([parts count] > 0 && [[parts objectAtIndex: 0] length] > 0)
    {
      compiler = [parts objectAtIndex: 0];
    }

  return [self resolvedExecutablePathForCommand: compiler] ? [self resolvedExecutablePathForCommand: compiler] : compiler;
}

- (BOOL)hasWindowsManagedToolchainHintWithMakefiles:(NSString *)gnustepMakefiles
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  NSDictionary *environment = [[NSProcessInfo processInfo] environment];
  NSString *pathVariable = [environment objectForKey: @"PATH"];
  NSString *msystem = [environment objectForKey: @"MSYSTEM"];
  NSString *combined = [NSString stringWithFormat: @"%@ %@ %@",
                                 gnustepMakefiles ? gnustepMakefiles : @"",
                                 pathVariable ? pathVariable : @"",
                                 msystem ? msystem : @""];
  NSString *lowercase = [combined lowercaseString];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *normalizedMakefiles = nil;
  NSString *installRoot = nil;
  NSMutableArray *candidateRoots = [NSMutableArray array];
  NSUInteger candidateIndex = 0;

  if ([gnustepMakefiles length] == 0)
    {
      return NO;
    }

  normalizedMakefiles = [gnustepMakefiles stringByReplacingOccurrencesOfString: @"\\" withString: @"/"];
  installRoot = [normalizedMakefiles stringByDeletingLastPathComponent];
  installRoot = [installRoot stringByDeletingLastPathComponent];
  installRoot = [installRoot stringByDeletingLastPathComponent];
  if (installRoot != nil && [installRoot length] > 0)
    {
      [candidateRoots addObject: installRoot];
      if ([installRoot length] > 3 && [installRoot characterAtIndex: 0] == '/' && [installRoot characterAtIndex: 2] == '/')
        {
          unichar drive = [installRoot characterAtIndex: 1];
          if ((drive >= 'a' && drive <= 'z') || (drive >= 'A' && drive <= 'Z'))
            {
              NSString *tail = [installRoot substringFromIndex: 3];
              NSString *driveRoot = [NSString stringWithFormat: @"%C:/%@", drive, tail];
              [candidateRoots addObject: driveRoot];
            }
        }
    }

  for (candidateIndex = 0; candidateIndex < [candidateRoots count]; candidateIndex++)
    {
      NSString *root = [candidateRoots objectAtIndex: candidateIndex];
      NSString *binRoot = [root stringByAppendingPathComponent: @"bin"];
      NSString *usrBinRoot = [[root stringByAppendingPathComponent: @"usr"] stringByAppendingPathComponent: @"bin"];
      NSString *clang64BinRoot = [[root stringByAppendingPathComponent: @"clang64"] stringByAppendingPathComponent: @"bin"];
      BOOL hasCompiler = [manager fileExistsAtPath: [binRoot stringByAppendingPathComponent: @"clang.exe"]] ||
                         [manager fileExistsAtPath: [usrBinRoot stringByAppendingPathComponent: @"clang.exe"]] ||
                         [manager fileExistsAtPath: [clang64BinRoot stringByAppendingPathComponent: @"clang.exe"]];
      BOOL hasShell = [manager fileExistsAtPath: [usrBinRoot stringByAppendingPathComponent: @"bash.exe"]] ||
                      [manager fileExistsAtPath: [binRoot stringByAppendingPathComponent: @"bash.exe"]];
      if (hasCompiler && hasShell)
        {
          return YES;
        }
    }

  return ([lowercase rangeOfString: @"managed-probe"].location != NSNotFound ||
          [lowercase rangeOfString: @"msys2"].location != NSNotFound ||
          [lowercase rangeOfString: @"clang64"].location != NSNotFound);
#else
  return NO;
#endif
}

- (NSDictionary *)probeCompiler:(NSString *)compilerPath
{
  NSString *tempDir = [NSTemporaryDirectory() stringByAppendingPathComponent: [[NSUUID UUID] UUIDString]];
  NSString *source = [tempDir stringByAppendingPathComponent: @"probe.m"];
  NSString *object = [tempDir stringByAppendingPathComponent: @"probe.o"];
  NSString *binary = [tempDir stringByAppendingPathComponent: @"probe"];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDictionary *compileResult = nil;
  NSDictionary *linkResult = nil;
  NSDictionary *runResult = nil;
  BOOL canCompile = NO;
  BOOL canLink = NO;
  BOOL canRun = NO;

  if (compilerPath == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"can_compile",
                            [NSNumber numberWithBool: NO], @"can_link",
                            [NSNumber numberWithBool: NO], @"can_run",
                            @"missing_compiler", @"status",
                            nil];
    }

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: NO], @"can_compile",
                        [NSNumber numberWithBool: NO], @"can_link",
                        [NSNumber numberWithBool: NO], @"can_run",
                        @"not_run", @"status",
                        @"windows_active_probe_deferred", @"reason",
                        nil];
#endif

  [manager createDirectoryAtPath: tempDir withIntermediateDirectories: YES attributes: nil error: NULL];
  [@"int main(void) { return 0; }\n" writeToFile: source atomically: YES encoding: NSUTF8StringEncoding error: NULL];

  compileResult = [self runCommand: [NSArray arrayWithObjects: compilerPath, @"-x", @"objective-c", @"-c", source, @"-o", object, nil]
                  currentDirectory: nil];
  canCompile = [[compileResult objectForKey: @"exit_status"] intValue] == 0 && [manager fileExistsAtPath: object];
  if (canCompile)
    {
      linkResult = [self runCommand: [NSArray arrayWithObjects: compilerPath, object, @"-o", binary, nil] currentDirectory: nil];
      canLink = [[linkResult objectForKey: @"exit_status"] intValue] == 0 && [manager fileExistsAtPath: binary];
    }
  if (canLink)
    {
      runResult = [self runCommand: [NSArray arrayWithObjects: binary, nil] currentDirectory: nil];
      canRun = [[runResult objectForKey: @"exit_status"] intValue] == 0;
    }

  [manager removeItemAtPath: tempDir error: NULL];
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: canCompile], @"can_compile",
                        [NSNumber numberWithBool: canLink], @"can_link",
                        [NSNumber numberWithBool: canRun], @"can_run",
                        nil];
}

- (NSDictionary *)toolchainFactsForInterface:(NSString *)interface
{
  return [self toolchainFactsForInterface: interface quick: NO];
}

- (NSDictionary *)toolchainFactsForInterface:(NSString *)interface quick:(BOOL)quick
{
  NSString *gnustepConfig = [self firstAvailableExecutable: [NSArray arrayWithObjects: @"gnustep-config", nil]];
  NSString *gnustepMakefiles = [[[NSProcessInfo processInfo] environment] objectForKey: @"GNUSTEP_MAKEFILES"];
  BOOL windowsManagedHint = [self hasWindowsManagedToolchainHintWithMakefiles: gnustepMakefiles];
  NSString *gnustepMakeCompiler = nil;
  NSDictionary *compiler = nil;
  NSDictionary *probe = nil;
  NSString *compilerFamily = nil;
  BOOL present = (gnustepConfig != nil || gnustepMakefiles != nil);

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  if (windowsManagedHint)
    {
      compiler = [NSDictionary dictionaryWithObjectsAndKeys:
                                @"clang", @"path",
                                @"clang", @"family",
                                @"unknown", @"version",
                                nil];
      probe = [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"can_compile",
                            [NSNumber numberWithBool: NO], @"can_link",
                            [NSNumber numberWithBool: NO], @"can_run",
                            @"not_run", @"status",
                            @"windows_subprocess_probe_deferred", @"reason",
                            nil];
    }
  else
#endif
    {
      gnustepMakeCompiler = quick ? nil : [self gnustepMakeCompilerPathWithConfig: gnustepConfig];
      compiler = [self compilerInfoForExecutable: gnustepMakeCompiler];
      if (quick)
        {
          probe = [NSDictionary dictionaryWithObjectsAndKeys:
                                [NSNumber numberWithBool: NO], @"can_compile",
                                [NSNumber numberWithBool: NO], @"can_link",
                                [NSNumber numberWithBool: NO], @"can_run",
                                @"not_run", @"status",
                                @"doctor_quick_mode", @"reason",
                                nil];
        }
      else
        {
          probe = [self probeCompiler: [compiler objectForKey: @"path"]];
        }
    }
  compilerFamily = [compiler objectForKey: @"family"];
  NSString *toolchainFlavor = compilerFamily ? compilerFamily : @"unknown";
  NSMutableDictionary *featureFlags = [NSMutableDictionary dictionaryWithObjectsAndKeys:
                                                              [NSNumber numberWithBool: NO], @"objc2_syntax",
                                                              [NSNumber numberWithBool: NO], @"blocks",
                                                              [NSNumber numberWithBool: NO], @"arc",
                                                              [NSNumber numberWithBool: NO], @"nonfragile_abi",
                                                              [NSNumber numberWithBool: NO], @"associated_objects",
                                                              [NSNumber numberWithBool: YES], @"exceptions",
                                                              nil];
  NSString *objcRuntime = @"unknown";
  NSString *objcABI = @"unknown";
  BOOL gnustepBase = NO;
  BOOL gnustepGUI = NO;

  if ((compilerFamily == nil || [compilerFamily isEqualToString: @"unknown"]) && windowsManagedHint)
    {
      compilerFamily = @"clang";
    }

  if (windowsManagedHint)
    {
      toolchainFlavor = @"msys2-clang64";
    }
  else if (compilerFamily != nil)
    {
      toolchainFlavor = compilerFamily;
    }

  if ([compilerFamily isEqualToString: @"clang"])
    {
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"objc2_syntax"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"blocks"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"arc"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"nonfragile_abi"];
      [featureFlags setObject: [NSNumber numberWithBool: YES] forKey: @"associated_objects"];
      objcRuntime = present ? @"libobjc2" : @"unknown";
      objcABI = present ? @"modern" : @"unknown";
    }
  else if ([compilerFamily isEqualToString: @"gcc"])
    {
      objcRuntime = present ? @"gcc_libobjc" : @"unknown";
      objcABI = present ? @"legacy" : @"unknown";
    }

  if (windowsManagedHint)
    {
      gnustepBase = YES;
      gnustepGUI = YES;
    }
  else if ([interface isEqualToString: @"full"] && quick == NO && gnustepConfig != nil)
    {
      NSDictionary *baseLibs = [self runCommand: [NSArray arrayWithObjects: gnustepConfig, @"--base-libs", nil] currentDirectory: nil];
      NSDictionary *guiLibs = [self runCommand: [NSArray arrayWithObjects: gnustepConfig, @"--gui-libs", nil] currentDirectory: nil];
      gnustepBase = ([[baseLibs objectForKey: @"exit_status"] intValue] == 0 &&
                     [[baseLibs objectForKey: @"stdout"] rangeOfString: @"-lgnustep-base"].location != NSNotFound);
      gnustepGUI = ([[guiLibs objectForKey: @"exit_status"] intValue] == 0 &&
                    [[guiLibs objectForKey: @"stdout"] rangeOfString: @"-lgnustep-gui"].location != NSNotFound);
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: present], @"present",
                        compilerFamily ? compilerFamily : @"unknown", @"compiler_family",
                        [compiler objectForKey: @"version"] ? [compiler objectForKey: @"version"] : @"unknown", @"compiler_version",
                        toolchainFlavor ? toolchainFlavor : @"unknown", @"toolchain_flavor",
                        objcRuntime, @"objc_runtime",
                        objcABI, @"objc_abi",
                        [NSNumber numberWithBool: (gnustepConfig != nil || gnustepMakefiles != nil)], @"gnustep_make",
                        [NSNumber numberWithBool: gnustepBase], @"gnustep_base",
                        [NSNumber numberWithBool: gnustepGUI], @"gnustep_gui",
                        [probe objectForKey: @"can_compile"], @"can_compile",
                        [probe objectForKey: @"can_link"], @"can_link",
                        [probe objectForKey: @"can_run"], @"can_run",
                        probe, @"probe",
                        featureFlags, @"feature_flags",
                        gnustepConfig ? gnustepConfig : [NSNull null], @"gnustep_config_path",
                        gnustepMakefiles ? gnustepMakefiles : [NSNull null], @"gnustep_makefiles",
                        gnustepMakeCompiler ? gnustepMakeCompiler : [NSNull null], @"gnustep_make_compiler",
                        quick ? @"quick" : ([interface isEqualToString: @"bootstrap"] ? @"installer" : @"full"), @"detection_depth",
                        nil];
}

- (BOOL)isDeferredProbe:(NSDictionary *)probe
{
  NSString *reason = nil;
  if ([probe isKindOfClass: [NSDictionary class]] == NO)
    {
      return NO;
    }
  reason = [probe objectForKey: @"reason"];
  return [[probe objectForKey: @"status"] isEqualToString: @"not_run"] &&
         ([reason isEqualToString: @"windows_subprocess_probe_deferred"] ||
          [reason isEqualToString: @"doctor_quick_mode"]);
}

- (NSDictionary *)managedInstallIntegrityCheckForEnvironment:(NSDictionary *)environment interface:(NSString *)interface
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSMutableArray *candidateStatePaths = [NSMutableArray array];
  NSString *binaryPath = [[[NSProcessInfo processInfo] arguments] count] > 0 ? [[[NSProcessInfo processInfo] arguments] objectAtIndex: 0] : nil;
  NSString *resolvedPath = binaryPath != nil ? [binaryPath stringByResolvingSymlinksInPath] : nil;
  NSString *binaryDir = nil;
  NSString *installRoot = nil;
  NSUInteger i = 0;

  if ([interface isEqualToString: @"bootstrap"])
    {
      return [self checkWithID: @"managed.install.integrity"
                         title: @"Inspect managed install integrity"
                        status: @"not_run"
                      severity: @"warning"
                       message: @"This check is available in the full CLI only."
                     interface: @"full"
                executionTier: @"full_only"
                       details: [NSDictionary dictionaryWithObject: [NSNumber numberWithBool: YES]
                                                            forKey: @"unavailable_in_bootstrap"]];
    }

  if (resolvedPath == nil || [resolvedPath length] == 0)
    {
      resolvedPath = binaryPath;
    }
  if (resolvedPath != nil && [resolvedPath length] > 0)
    {
      binaryDir = [resolvedPath stringByDeletingLastPathComponent];
      installRoot = [binaryDir stringByDeletingLastPathComponent];
      if (installRoot != nil && [installRoot length] > 0)
        {
          [candidateStatePaths addObject: [[installRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"]];
        }
      if ([binaryDir hasSuffix: @"/libexec/gnustep-cli/bin"] || [binaryDir hasSuffix: @"\\libexec\\gnustep-cli\\bin"])
        {
          NSString *runtimeRoot = [[[binaryDir stringByDeletingLastPathComponent]
                                            stringByDeletingLastPathComponent]
                                            stringByDeletingLastPathComponent];
          if (runtimeRoot != nil && [runtimeRoot length] > 0)
            {
              NSString *runtimeStatePath = [[runtimeRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
              if (![candidateStatePaths containsObject: runtimeStatePath])
                {
                  [candidateStatePaths insertObject: runtimeStatePath atIndex: 0];
                }
            }
        }
    }
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  {
    NSString *localAppData = [[[NSProcessInfo processInfo] environment] objectForKey: @"LOCALAPPDATA"];
    if (localAppData != nil && [localAppData length] > 0)
      {
        [candidateStatePaths addObject: [[[localAppData stringByAppendingPathComponent: @"gnustep-cli"]
                                                    stringByAppendingPathComponent: @"state"]
                                                    stringByAppendingPathComponent: @"cli-state.json"]];
      }
  }
#else
  {
    NSString *root = [self repositoryRoot];
    if (root != nil)
      {
        [candidateStatePaths addObject: [[root stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"]];
      }
  }
#endif

  for (i = 0; i < [candidateStatePaths count]; i++)
    {
      NSString *statePath = [candidateStatePaths objectAtIndex: i];
      if ([manager fileExistsAtPath: statePath])
        {
          return [self checkWithID: @"managed.install.integrity"
                             title: @"Inspect managed install integrity"
                            status: @"ok"
                          severity: @"warning"
                           message: [NSString stringWithFormat: @"Managed install state was found at %@.", statePath]
                         interface: @"full"
                    executionTier: @"full_only"
                           details: [NSDictionary dictionaryWithObjectsAndKeys:
                                                    statePath, @"state_path",
                                                    candidateStatePaths, @"candidate_state_paths",
                                                    nil]];
        }
    }
  return [self checkWithID: @"managed.install.integrity"
                     title: @"Inspect managed install integrity"
                    status: @"not_run"
                  severity: @"warning"
                   message: @"No managed install state was detected on this host."
                 interface: @"full"
            executionTier: @"full_only"
                   details: [NSDictionary dictionaryWithObjectsAndKeys:
                                            [NSNumber numberWithBool: NO], @"managed_install_detected",
                                            candidateStatePaths, @"candidate_state_paths",
                                            nil]];
}

- (NSDictionary *)nativeToolchainAssessmentForEnvironment:(NSDictionary *)environment compatibility:(NSDictionary *)compatibility
{
  NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
  NSString *distributionID = [environment objectForKey: @"distribution_id"];
  NSString *compilerFamily = [toolchain objectForKey: @"compiler_family"];
  NSString *objcRuntime = [toolchain objectForKey: @"objc_runtime"];
  NSString *objcABI = [toolchain objectForKey: @"objc_abi"];
  NSDictionary *probe = [toolchain objectForKey: @"probe"];
  BOOL activeProbeDeferred = [self isDeferredProbe: probe];
  BOOL modernClang = [compilerFamily isEqualToString: @"clang"] &&
                     [objcRuntime isEqualToString: @"libobjc2"] &&
                     [objcABI isEqualToString: @"modern"];

  if ([[toolchain objectForKey: @"present"] boolValue] == NO)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"unavailable", @"assessment",
                            @"managed", @"preference",
                            @"No native GNUstep toolchain was detected.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"native_toolchain_missing", @"code",
                                                     @"No GNUstep toolchain was detected on the host.", @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  if (activeProbeDeferred == NO &&
      ([[toolchain objectForKey: @"can_compile"] boolValue] == NO ||
       [[toolchain objectForKey: @"can_link"] boolValue] == NO ||
       [[toolchain objectForKey: @"can_run"] boolValue] == NO))
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"broken", @"assessment",
                            @"managed", @"preference",
                            @"A native GNUstep toolchain was detected, but it does not pass functional validation.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"native_toolchain_broken", @"code",
                                                     @"The detected toolchain cannot compile, link, and run correctly.", @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  if ([[environment objectForKey: @"os"] isEqualToString: @"openbsd"] && modernClang)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"preferred", @"assessment",
                            @"native", @"preference",
                            @"The packaged OpenBSD GNUstep environment is a preferred native toolchain candidate.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"openbsd_packaged_candidate", @"code",
                                                     @"OpenBSD packaged GNUstep should be preferred when it satisfies the CLI requirements.", @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  if ([distributionID isEqualToString: @"fedora"] && modernClang)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"supported", @"assessment",
                            @"native", @"preference",
                            @"The detected Fedora GNUstep environment is a supported native toolchain candidate.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"fedora_packaged_candidate", @"code",
                                                     @"Fedora appears to provide a compatible native GNUstep stack.", @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  if ([distributionID isEqualToString: @"arch"] && modernClang)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"supported", @"assessment",
                            @"native", @"preference",
                            @"The detected Arch GNUstep environment is a supported native toolchain candidate.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"arch_packaged_candidate", @"code",
                                                     @"Arch appears to provide a compatible native GNUstep stack.", @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  if (([distributionID isEqualToString: @"debian"] ||
       [distributionID isEqualToString: @"arch"] ||
       [distributionID isEqualToString: @"fedora"]) &&
      [compilerFamily isEqualToString: @"gcc"])
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"interoperability_only", @"assessment",
                            @"managed", @"preference",
                            @"The detected packaged GNUstep environment is suitable for interoperability validation, but it is not the preferred runtime model.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"gcc_interop_only", @"code",
                                                     [NSString stringWithFormat: @"%@ currently looks like a GCC-oriented packaged GNUstep environment.", distributionID], @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  if (modernClang && [[compatibility objectForKey: @"compatible"] boolValue])
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            @"supported", @"assessment",
                            @"native", @"preference",
                            @"The detected native GNUstep environment satisfies the managed runtime expectations.", @"message",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"native_toolchain_supported", @"code",
                                                     @"The detected native toolchain matches the required runtime and capability model.", @"message",
                                                     nil]], @"reasons",
                            nil];
    }
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        @"incompatible", @"assessment",
                        @"managed", @"preference",
                        @"A native GNUstep toolchain was detected, but it does not match the preferred runtime model for this workflow.", @"message",
                        [NSArray arrayWithObject:
                                 [NSDictionary dictionaryWithObjectsAndKeys:
                                                 @"native_toolchain_incompatible", @"code",
                                                 @"Use the managed toolchain unless a workflow explicitly supports this native environment.", @"message",
                                                 nil]], @"reasons",
                        nil];
}

- (NSDictionary *)evaluateCompatibilityForEnvironment:(NSDictionary *)environment artifact:(NSDictionary *)artifact
{
  NSMutableArray *reasons = [NSMutableArray array];
  NSMutableArray *warnings = [NSMutableArray array];
  NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
  NSString *detectedCompiler = [toolchain objectForKey: @"compiler_family"];
  NSDictionary *featureFlags = [toolchain objectForKey: @"feature_flags"];
  NSArray *requiredFeatures = artifact ? [artifact objectForKey: @"required_features"] : nil;
  NSArray *comparisonFields = [NSArray arrayWithObjects:
                                         [NSArray arrayWithObjects: @"toolchain_flavor", @"toolchain flavor", nil],
                                         [NSArray arrayWithObjects: @"objc_runtime", @"Objective-C runtime", nil],
                                         [NSArray arrayWithObjects: @"objc_abi", @"Objective-C ABI", nil],
                                         nil];
  NSUInteger i = 0;

  if (artifact == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithBool: NO], @"compatible",
                            [NSNull null], @"target_kind",
                            [NSNull null], @"target_id",
                            [NSArray arrayWithObject:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"unsupported_os", @"code",
                                                     @"No managed artifact matched the detected operating system and architecture.", @"message",
                                                     nil]], @"reasons",
                            [NSArray array], @"warnings",
                            nil];
    }

  if ([[environment objectForKey: @"os"] isEqualToString: [artifact objectForKey: @"os"]] == NO)
    {
      [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"unsupported_os", @"code",
                                           @"Detected OS does not match the selected artifact OS.", @"message",
                                           nil]];
    }
  if ([[environment objectForKey: @"arch"] isEqualToString: [artifact objectForKey: @"arch"]] == NO)
    {
      [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"unsupported_arch", @"code",
                                           @"Detected architecture does not match the selected artifact architecture.", @"message",
                                           nil]];
    }
  NSArray *supportedDistributions = [artifact objectForKey: @"supported_distributions"];
  NSArray *supportedOSVersions = [artifact objectForKey: @"supported_os_versions"];
  BOOL hasSupportedDistributions = (supportedDistributions != nil &&
                                    (id)supportedDistributions != (id)[NSNull null] &&
                                    [supportedDistributions isKindOfClass: [NSArray class]] &&
                                    [supportedDistributions count] > 0);
  BOOL hasSupportedOSVersions = (supportedOSVersions != nil &&
                                 (id)supportedOSVersions != (id)[NSNull null] &&
                                 [supportedOSVersions isKindOfClass: [NSArray class]] &&
                                 [supportedOSVersions count] > 0);
  if ([[environment objectForKey: @"os"] isEqualToString: @"linux"] &&
      hasSupportedDistributions &&
      [supportedDistributions containsObject: [environment objectForKey: @"distribution_id"]] == NO)
    {
      [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"unsupported_distribution", @"code",
                                           @"Detected Linux distribution is not in the artifact's supported distributions.", @"message",
                                           nil]];
    }
  if ([[environment objectForKey: @"os"] isEqualToString: @"linux"] &&
      hasSupportedOSVersions &&
      [supportedOSVersions containsObject: [environment objectForKey: @"os_version"]] == NO)
    {
      [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                           @"unsupported_os_version", @"code",
                                           @"Detected Linux OS version is not in the artifact's supported OS versions.", @"message",
                                           nil]];
    }
  if ([[toolchain objectForKey: @"present"] boolValue])
    {
      if (detectedCompiler != nil &&
          [detectedCompiler isEqualToString: [artifact objectForKey: @"compiler_family"]] == NO)
        {
          [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                               @"compiler_family_mismatch", @"code",
                                               [NSString stringWithFormat: @"Detected compiler family is %@, but the selected managed artifact requires %@.",
                                                 detectedCompiler,
                                                 [artifact objectForKey: @"compiler_family"]], @"message",
                                               nil]];
        }
      for (i = 0; i < [comparisonFields count]; i++)
        {
          NSArray *entry = [comparisonFields objectAtIndex: i];
          NSString *field = [entry objectAtIndex: 0];
          NSString *label = [entry objectAtIndex: 1];
          NSString *expected = [artifact objectForKey: field];
          NSString *detected = [toolchain objectForKey: field];
          if (expected != nil &&
              detected != nil &&
              [expected isEqualToString: @"unknown"] == NO &&
              [detected isEqualToString: @"unknown"] == NO &&
              [detected isEqualToString: expected] == NO)
            {
              [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                   [NSString stringWithFormat: @"%@_mismatch", field], @"code",
                                                   [NSString stringWithFormat: @"Detected %@ is %@, but the selected managed artifact requires %@.",
                                                     label,
                                                     detected,
                                                     expected], @"message",
                                                   nil]];
            }
        }
      for (i = 0; i < [requiredFeatures count]; i++)
        {
          NSString *feature = [requiredFeatures objectAtIndex: i];
          if ([[featureFlags objectForKey: feature] boolValue] == NO)
            {
              [reasons addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                   @"missing_required_feature", @"code",
                                                   [NSString stringWithFormat: @"The detected toolchain does not support required feature '%@'.", feature], @"message",
                                                   nil]];
            }
        }
      if ([detectedCompiler isEqualToString: @"gcc"])
        {
          [warnings addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                @"gcc_toolchain_detected", @"code",
                                                @"A GCC-based GNUstep environment is installed. Some modern Objective-C features require a Clang-based toolchain.", @"message",
                                                nil]];
        }
    }
  else
    {
      [warnings addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                            @"toolchain_not_present", @"code",
                                            @"No preexisting GNUstep toolchain was detected; a managed install will be required.", @"message",
                                            nil]];
    }

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithBool: ([reasons count] == 0)], @"compatible",
                        [artifact objectForKey: @"kind"], @"target_kind",
                        [artifact objectForKey: @"id"], @"target_id",
                        reasons, @"reasons",
                        warnings, @"warnings",
                        nil];
}

- (NSString *)classifyEnvironment:(NSDictionary *)environment compatibility:(NSDictionary *)compatibility
{
  NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
  NSDictionary *probe = [toolchain objectForKey: @"probe"];
  BOOL activeProbeDeferred = [self isDeferredProbe: probe];
  if ([[toolchain objectForKey: @"present"] boolValue] == NO)
    {
      return @"no_toolchain";
    }
  if (activeProbeDeferred == NO &&
      ([[toolchain objectForKey: @"can_compile"] boolValue] == NO ||
       [[toolchain objectForKey: @"can_link"] boolValue] == NO ||
       [[toolchain objectForKey: @"can_run"] boolValue] == NO))
    {
      return @"toolchain_broken";
    }
  if ([[compatibility objectForKey: @"compatible"] boolValue] == NO)
    {
      return @"toolchain_incompatible";
    }
  return @"toolchain_compatible";
}

- (NSDictionary *)buildDoctorPayloadWithInterface:(NSString *)interface manifestPath:(NSString *)manifestPath
{
  return [self buildDoctorPayloadWithInterface: interface manifestPath: manifestPath quick: NO];
}

- (NSDictionary *)buildDoctorPayloadWithInterface:(NSString *)interface manifestPath:(NSString *)manifestPath quick:(BOOL)quick
{
  NSString *osVersion = [self readOSReleaseIdentifier];
  NSString *distributionID = nil;
  NSString *osName = [self normalizeOSName];
  NSString *arch = [self normalizeArchName];
  NSDictionary *toolchain = [self toolchainFactsForInterface: interface quick: quick];
  NSMutableDictionary *environment = [NSMutableDictionary dictionary];
  NSDictionary *manifest = nil;
  NSDictionary *release = nil;
  NSDictionary *artifact = nil;
  NSDictionary *compatibility = nil;
  NSDictionary *nativeToolchain = nil;
  NSString *classification = nil;
  NSString *status = @"ok";
  NSMutableArray *checks = [NSMutableArray array];
  NSMutableArray *actions = [NSMutableArray array];
  NSArray *selectionErrors = [NSArray array];
  NSString *summary = nil;
  NSString *manifestError = nil;
  BOOL powershellDownloader = NO;
  BOOL downloaderAvailable = NO;

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  powershellDownloader = YES;
#endif

  [self appendInstallTrace: @"doctor.build.start"];

  if (osVersion != nil)
    {
      NSRange dash = [osVersion rangeOfString: @"-"];
      distributionID = dash.location == NSNotFound ? osVersion : [osVersion substringToIndex: dash.location];
    }
  [environment setObject: osName forKey: @"os"];
  if (osVersion != nil)
    {
      [environment setObject: osVersion forKey: @"os_version"];
    }
  if (distributionID != nil)
    {
      [environment setObject: distributionID forKey: @"distribution_id"];
    }
  [environment setObject: arch forKey: @"arch"];
  [environment setObject: @"posix" forKey: @"shell_family"];
  [environment setObject: @"user" forKey: @"install_scope"];
  [environment setObject: toolchain forKey: @"toolchain"];
  downloaderAvailable = ([self firstAvailableExecutable: [NSArray arrayWithObjects: @"curl", nil]] != nil ||
                         [self firstAvailableExecutable: [NSArray arrayWithObjects: @"wget", nil]] != nil ||
                         powershellDownloader);
  [environment setObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                          [NSNumber numberWithBool: ([self firstAvailableExecutable: [NSArray arrayWithObjects: @"curl", nil]] != nil)], @"curl",
                                          [NSNumber numberWithBool: ([self firstAvailableExecutable: [NSArray arrayWithObjects: @"wget", nil]] != nil)], @"wget",
                                          [NSNumber numberWithBool: powershellDownloader], @"powershell",
                                          [NSNumber numberWithBool: downloaderAvailable], @"available",
                                          nil]
                 forKey: @"bootstrap_prerequisites"];
  [environment setObject: [NSArray array] forKey: @"detected_layouts"];
  [environment setObject: [NSArray array] forKey: @"install_prefixes"];
  [self appendInstallTrace: @"doctor.environment.ready"];

  if (manifestPath != nil)
    {
      [self appendInstallTrace: @"doctor.manifest.load.start"];
      manifest = [self validateAndLoadManifest: manifestPath error: &manifestError];
      [self appendInstallTrace: @"doctor.manifest.load.complete"];
      if (manifest != nil)
        {
          NSArray *selected = nil;
          NSUInteger i = 0;
          release = [self selectReleaseFromManifest: manifest];
          selected = [self selectedArtifactsForRelease: release
                                           environment: environment
                                       selectionErrors: &selectionErrors];
          for (i = 0; i < [selected count]; i++)
            {
              NSDictionary *candidate = [selected objectAtIndex: i];
              if ([[candidate objectForKey: @"kind"] isEqualToString: @"toolchain"])
                {
                  artifact = candidate;
                  break;
                }
            }
        }
    }

  [self appendInstallTrace: @"doctor.compatibility.start"];
  compatibility = [self evaluateCompatibilityForEnvironment: environment artifact: artifact];
  if (manifestError != nil && artifact == nil)
    {
      compatibility = [NSDictionary dictionaryWithObjectsAndKeys:
                                       [NSNumber numberWithBool: YES], @"compatible",
                                       [NSNull null], @"target_kind",
                                       [NSNull null], @"target_id",
                                       [NSArray array], @"reasons",
                                       [NSArray arrayWithObject:
                                                [NSDictionary dictionaryWithObjectsAndKeys:
                                                                @"manifest_unavailable", @"code",
                                                                manifestError, @"message",
                                                                nil]], @"warnings",
                                       nil];
    }
  [self appendInstallTrace: @"doctor.native-assessment.start"];
  nativeToolchain = [self nativeToolchainAssessmentForEnvironment: environment compatibility: compatibility];
  [environment setObject: nativeToolchain forKey: @"native_toolchain"];
  classification = [self classifyEnvironment: environment compatibility: compatibility];
  [self appendInstallTrace: @"doctor.classification.complete"];

  if ([classification isEqualToString: @"toolchain_incompatible"] ||
      [classification isEqualToString: @"toolchain_broken"])
    {
      status = @"error";
    }
  else if ([classification isEqualToString: @"no_toolchain"])
    {
      status = @"warning";
    }

  [self appendInstallTrace: @"doctor.checks.host.start"];
  [checks addObject: [self checkWithID: @"host.identity"
                                 title: @"Determine host identity"
                                status: @"ok"
                              severity: @"info"
                               message: [NSString stringWithFormat: @"Detected %@ on %@.", osName, arch]
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_required"
                               details: [NSDictionary dictionaryWithObjectsAndKeys:
                                                        osVersion ? osVersion : [NSNull null], @"os_version",
                                                        distributionID ? distributionID : [NSNull null], @"distribution_id",
                                                        nil]]];
  [checks addObject: [self checkWithID: @"bootstrap.downloader"
                                 title: @"Check for downloader"
                                status: [[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"available"] boolValue] ? @"ok" : @"error"
                              severity: @"error"
                               message: [[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"available"] boolValue] ? @"Found a downloader." : @"No downloader is available."
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_required"
                               details: nil]];
  [checks addObject: [self checkWithID: @"toolchain.detect"
                                 title: @"Detect GNUstep toolchain"
                                status: [[toolchain objectForKey: @"present"] boolValue] ? @"ok" : @"warning"
                              severity: @"error"
                               message: [[toolchain objectForKey: @"present"] boolValue] ?
                                 [NSString stringWithFormat: @"Detected a %@-based GNUstep toolchain.", [toolchain objectForKey: @"compiler_family"]] :
                                 @"No GNUstep toolchain detected."
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_optional"
                               details: nil]];
  [checks addObject: [self checkWithID: @"native-toolchain.assess"
                                 title: @"Assess native packaged toolchain path"
                                status: ([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"preferred"] ||
                                         [[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"supported"]) ? @"ok" :
                                         (([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"interoperability_only"] ||
                                           [[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"unavailable"]) ? @"warning" : @"error")
                              severity: (([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"preferred"] ||
                                          [[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"supported"] ||
                                          [[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"interoperability_only"] ||
                                          [[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"unavailable"]) ? @"warning" : @"error")
                               message: [nativeToolchain objectForKey: @"message"]
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_optional"
                               details: [NSDictionary dictionaryWithObjectsAndKeys:
                                                        [nativeToolchain objectForKey: @"assessment"], @"assessment",
                                                        [nativeToolchain objectForKey: @"preference"], @"preference",
                                                        [nativeToolchain objectForKey: @"reasons"], @"reasons",
                                                        nil]]];

  if ([interface isEqualToString: @"full"])
    {
      BOOL probeDeferred = [self isDeferredProbe: [toolchain objectForKey: @"probe"]];
      [checks addObject: [self checkWithID: @"toolchain.probe"
                                     title: @"Compile/link/run probe"
                                    status: probeDeferred ? @"not_run" : (([[toolchain objectForKey: @"can_compile"] boolValue] &&
                                             [[toolchain objectForKey: @"can_link"] boolValue] &&
                                             [[toolchain objectForKey: @"can_run"] boolValue]) ? @"ok" : @"warning")
                                  severity: @"error"
                                   message: probeDeferred ? @"Active compiler validation was skipped for this doctor run." : (([[toolchain objectForKey: @"can_compile"] boolValue] &&
                                             [[toolchain objectForKey: @"can_link"] boolValue] &&
                                             [[toolchain objectForKey: @"can_run"] boolValue]) ?
                                     @"The compiler can compile, link, and run a minimal Objective-C probe." :
                                     @"A compiler probe did not fully succeed.")
                                 interface: @"full"
                            executionTier: @"full_only"
                                   details: [NSDictionary dictionaryWithObjectsAndKeys:
                                                          [toolchain objectForKey: @"can_compile"], @"can_compile",
                                                          [toolchain objectForKey: @"can_link"], @"can_link",
                                                          [toolchain objectForKey: @"can_run"], @"can_run",
                                                          [toolchain objectForKey: @"gnustep_make_compiler"] ? [toolchain objectForKey: @"gnustep_make_compiler"] : [NSNull null], @"compiler",
                                                          [[toolchain objectForKey: @"probe"] objectForKey: @"reason"] ? [[toolchain objectForKey: @"probe"] objectForKey: @"reason"] : [NSNull null], @"reason",
                                                          nil]]];
    }
  else
    {
      [checks addObject: [self checkWithID: @"toolchain.probe"
                                     title: @"Compile/link/run probe"
                                    status: @"not_run"
                                  severity: @"error"
                                   message: @"This check is available in the full CLI only."
                                 interface: @"full"
                            executionTier: @"full_only"
                                   details: [NSDictionary dictionaryWithObject: [NSNumber numberWithBool: YES]
                                                                        forKey: @"unavailable_in_bootstrap"]]];
    }

  [self appendInstallTrace: @"doctor.checks.managed-integrity.start"];
  [checks addObject: [self managedInstallIntegrityCheckForEnvironment: environment interface: interface]];
  [self appendInstallTrace: @"doctor.checks.compatibility.start"];

  [checks addObject: [self checkWithID: @"toolchain.compatibility"
                                 title: @"Evaluate managed artifact compatibility"
                                status: artifact ? ([[compatibility objectForKey: @"compatible"] boolValue] ? @"ok" : @"error") : @"warning"
                              severity: @"error"
                               message: artifact ?
                                 ([[compatibility objectForKey: @"compatible"] boolValue] ?
                                  [NSString stringWithFormat: @"The environment is compatible with artifact %@.", [artifact objectForKey: @"id"]] :
                                  [NSString stringWithFormat: @"The environment is not compatible with artifact %@.", [artifact objectForKey: @"id"]]) :
                                 ([selectionErrors count] > 0 ? [selectionErrors objectAtIndex: 0] : @"No matching managed artifact was found for this host.")
                             interface: ([interface isEqualToString: @"bootstrap"] ? @"bootstrap" : @"both")
                        executionTier: @"bootstrap_optional"
                               details: nil]];

  [self appendInstallTrace: @"doctor.actions.start"];
  if ([[[environment objectForKey: @"bootstrap_prerequisites"] objectForKey: @"available"] boolValue] == NO)
    {
      [actions addObject: [self actionWithKind: @"install_downloader"
                                       message: @"Install curl, wget, or a supported platform downloader, then rerun setup."
                                      priority: 1]];
    }
  if ([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"preferred"])
    {
      [actions addObject: [self actionWithKind: @"use_existing_toolchain"
                                       message: @"Use the packaged native GNUstep toolchain; it is the preferred path on this host."
                                      priority: 1]];
    }
  else if ([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"supported"])
    {
      [actions addObject: [self actionWithKind: @"use_existing_toolchain"
                                       message: @"Use the detected native GNUstep toolchain or choose a managed install explicitly."
                                      priority: 1]];
    }
  else if ([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"interoperability_only"])
    {
      [actions addObject: [self actionWithKind: @"use_existing_toolchain"
                                       message: @"The detected native GNUstep toolchain is suitable for interoperability validation, but the managed toolchain remains the preferred path."
                                      priority: 2]];
      [actions addObject: [self actionWithKind: @"install_managed_toolchain"
                                       message: @"Install the supported managed GNUstep toolchain for the preferred runtime model."
                                      priority: 1]];
    }
  else if ([classification isEqualToString: @"no_toolchain"])
    {
      [actions addObject: [self actionWithKind: @"install_managed_toolchain"
                                       message: @"Install the supported managed GNUstep toolchain."
                                      priority: 1]];
    }
  else if ([classification isEqualToString: @"toolchain_incompatible"])
    {
      [actions addObject: [self actionWithKind: @"install_managed_toolchain"
                                       message: @"Install the supported Clang-based managed toolchain."
                                      priority: 1]];
    }
  else if ([classification isEqualToString: @"toolchain_broken"])
    {
      [actions addObject: [self actionWithKind: @"repair_or_replace_toolchain"
                                       message: @"Repair the detected toolchain or install a managed one."
                                      priority: 1]];
    }
  else
    {
      [actions addObject: [self actionWithKind: @"use_existing_toolchain"
                                       message: @"You can continue with the detected toolchain or install a managed one explicitly."
                                      priority: 1]];
    }

  [self appendInstallTrace: @"doctor.summary.start"];
  if ([classification isEqualToString: @"no_toolchain"])
    {
      summary = @"No preexisting GNUstep toolchain was detected.";
    }
  else if ([classification isEqualToString: @"toolchain_compatible"])
    {
      summary = @"A compatible GNUstep toolchain was detected.";
    }
  else if ([classification isEqualToString: @"toolchain_incompatible"])
    {
      summary = @"A GNUstep toolchain was detected, but it is incompatible with the selected managed artifacts.";
    }
  else
    {
      summary = @"A GNUstep toolchain was detected, but it does not appear to be working correctly.";
    }

  [self appendInstallTrace: @"doctor.payload.return"];
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"doctor", @"command",
                        @"0.1.0-dev", @"cli_version",
                        interface, @"interface",
                        quick ? @"quick" : ([interface isEqualToString: @"bootstrap"] ? @"installer" : @"full"), @"diagnostic_depth",
                        [NSNumber numberWithBool: ![status isEqualToString: @"error"]], @"ok",
                        status, @"status",
                        classification, @"environment_classification",
                        [nativeToolchain objectForKey: @"assessment"], @"native_toolchain_assessment",
                        summary, @"summary",
                        environment, @"environment",
                        compatibility, @"compatibility",
                        checks, @"checks",
                        actions, @"actions",
                        nil];
}

- (NSDictionary *)currentEnvironmentForInterface:(NSString *)interface
{
  NSString *osVersion = [self readOSReleaseIdentifier];
  NSString *distributionID = nil;
  NSString *osName = [self normalizeOSName];
  NSString *arch = [self normalizeArchName];
  NSDictionary *toolchain = [self toolchainFactsForInterface: interface];
  NSMutableDictionary *environment = [NSMutableDictionary dictionaryWithObjectsAndKeys:
                                                          osName, @"os",
                                                          arch, @"arch",
                                                          toolchain, @"toolchain",
                                                          nil];

  if (osVersion != nil)
    {
      NSRange dash = [osVersion rangeOfString: @"-"];
      if (dash.location != NSNotFound)
        {
          distributionID = [osVersion substringToIndex: dash.location];
        }
      [environment setObject: osVersion forKey: @"os_version"];
    }
  if (distributionID != nil)
    {
      [environment setObject: distributionID forKey: @"distribution_id"];
    }
  return environment;
}

- (NSString *)setupTransactionStatePathForInstallRoot:(NSString *)installRoot
{
  NSString *parent = [installRoot stringByDeletingLastPathComponent];
  NSString *name = [installRoot lastPathComponent];
  NSString *transactionRoot = [parent stringByAppendingPathComponent:
                                        [NSString stringWithFormat: @".%@.setup-transaction", name]];
  return [[transactionRoot stringByAppendingPathComponent: @"setup"] stringByAppendingPathComponent: @"transaction.json"];
}

- (NSString *)setupBackupPathForInstallRoot:(NSString *)installRoot
{
  NSString *parent = [installRoot stringByDeletingLastPathComponent];
  NSString *name = [installRoot lastPathComponent];
  return [parent stringByAppendingPathComponent:
                    [NSString stringWithFormat: @".%@.setup-backup-%@", name, [[NSUUID UUID] UUIDString]]];
}

- (void)recoverSetupTransactionForInstallRoot:(NSString *)installRoot
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *statePath = [self setupTransactionStatePathForInstallRoot: installRoot];
  NSDictionary *transaction = [self readJSONFile: statePath error: NULL];
  NSString *backupPath = [transaction objectForKey: @"backup_root"];
  NSString *transactionRoot = [[statePath stringByDeletingLastPathComponent] stringByDeletingLastPathComponent];

  if (transaction == nil)
    {
      return;
    }
  if (backupPath != nil && [manager fileExistsAtPath: backupPath])
    {
      [manager removeItemAtPath: installRoot error: NULL];
      [manager moveItemAtPath: backupPath toPath: installRoot error: NULL];
    }
  [manager removeItemAtPath: transactionRoot error: NULL];
}

- (BOOL)beginSetupTransactionForInstallRoot:(NSString *)installRoot
                                    release:(NSString *)releaseVersion
                                  artifacts:(NSArray *)artifactIDs
                                  backupPath:(NSString **)backupPath
                                       error:(NSString **)errorMessage
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *expandedInstallRoot = [installRoot stringByExpandingTildeInPath];
  NSString *statePath = [self setupTransactionStatePathForInstallRoot: expandedInstallRoot];
  NSString *transactionDir = [statePath stringByDeletingLastPathComponent];
  NSString *createdBackup = nil;

  [self recoverSetupTransactionForInstallRoot: expandedInstallRoot];
  [manager createDirectoryAtPath: transactionDir withIntermediateDirectories: YES attributes: nil error: NULL];

  if ([manager fileExistsAtPath: expandedInstallRoot] &&
      [[manager contentsOfDirectoryAtPath: expandedInstallRoot error: NULL] count] > 0)
    {
      createdBackup = [self setupBackupPathForInstallRoot: expandedInstallRoot];
      if ([manager moveItemAtPath: expandedInstallRoot toPath: createdBackup error: NULL] == NO)
        {
          if (errorMessage != NULL)
            {
              *errorMessage = @"Failed to snapshot the existing managed installation before setup.";
            }
          return NO;
        }
    }

  if ([self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                   [NSNumber numberWithInt: 1], @"schema_version",
                                                   @"in_progress", @"status",
                                                   expandedInstallRoot, @"install_root",
                                                   releaseVersion ? releaseVersion : [NSNull null], @"release_version",
                                                   artifactIDs ? artifactIDs : [NSArray array], @"artifacts",
                                                   createdBackup ? createdBackup : [NSNull null], @"backup_root",
                                                   nil]
                            toPath: statePath
                             error: errorMessage] == NO)
    {
      if (createdBackup != nil)
        {
          [manager moveItemAtPath: createdBackup toPath: expandedInstallRoot error: NULL];
        }
      return NO;
    }

  if (backupPath != NULL)
    {
      *backupPath = createdBackup;
    }
  return YES;
}

- (void)finishSetupTransactionForInstallRoot:(NSString *)installRoot
                                  backupPath:(NSString *)backupPath
                                     success:(BOOL)success
{
  [self finishSetupTransactionForInstallRoot: installRoot
                                  backupPath: backupPath
                                     success: success
                              preserveBackup: NO];
}

- (void)finishSetupTransactionForInstallRoot:(NSString *)installRoot
                                  backupPath:(NSString *)backupPath
                                     success:(BOOL)success
                              preserveBackup:(BOOL)preserveBackup
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *expandedInstallRoot = [installRoot stringByExpandingTildeInPath];
  NSString *statePath = [self setupTransactionStatePathForInstallRoot: expandedInstallRoot];
  NSString *transactionRoot = [[statePath stringByDeletingLastPathComponent] stringByDeletingLastPathComponent];

  if (!success && backupPath != nil && [manager fileExistsAtPath: backupPath])
    {
      [manager removeItemAtPath: expandedInstallRoot error: NULL];
      [manager moveItemAtPath: backupPath toPath: expandedInstallRoot error: NULL];
    }
  else if (success && backupPath != nil && preserveBackup == NO)
    {
      [manager removeItemAtPath: backupPath error: NULL];
    }

  [manager removeItemAtPath: transactionRoot error: NULL];
}

- (NSDictionary *)installedLifecycleStateForInstallRoot:(NSString *)installRoot
{
  NSString *root = [installRoot stringByExpandingTildeInPath];
  NSString *statePath = [[root stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSDictionary *state = [self readJSONFile: statePath error: NULL];
  if ([state isKindOfClass: [NSDictionary class]])
    {
      return state;
    }
  return [NSDictionary dictionary];
}

- (BOOL)dictionaryArray:(NSArray *)values containsString:(NSString *)candidate
{
  if ([values isKindOfClass: [NSArray class]] == NO || candidate == nil)
    {
      return NO;
    }
  return [values containsObject: candidate];
}

- (BOOL)packageRequirements:(NSDictionary *)requirements matchEnvironment:(NSDictionary *)environment reason:(NSString **)reason
{
  NSDictionary *toolchain = nil;
  NSDictionary *featureFlags = nil;
  NSArray *requiredFeatures = nil;
  NSArray *forbiddenFeatures = nil;
  NSUInteger i = 0;

  [self appendInstallTrace: @"requirements entry"];
  if (requirements == nil)
    {
      [self appendInstallTrace: @"requirements absent"];
      return YES;
    }
  if ([requirements isKindOfClass: [NSDictionary class]] == NO)
    {
      if (reason != NULL)
        {
          *reason = @"Package requirements are malformed.";
        }
      return NO;
    }

  toolchain = [environment objectForKey: @"toolchain"];
  if ([toolchain isKindOfClass: [NSDictionary class]] == NO)
    {
      if (reason != NULL)
        {
          *reason = @"Detected toolchain facts are malformed.";
        }
      return NO;
    }
  featureFlags = [toolchain objectForKey: @"feature_flags"];
  if (featureFlags != nil && (id)featureFlags != (id)[NSNull null] &&
      [featureFlags isKindOfClass: [NSDictionary class]] == NO)
    {
      if (reason != NULL)
        {
          *reason = @"Detected Objective-C feature flags are malformed.";
        }
      return NO;
    }
  requiredFeatures = [requirements objectForKey: @"required_features"];
  forbiddenFeatures = [requirements objectForKey: @"forbidden_features"];
  if (requiredFeatures != nil && (id)requiredFeatures != (id)[NSNull null] &&
      [requiredFeatures isKindOfClass: [NSArray class]] == NO)
    {
      if (reason != NULL)
        {
          *reason = @"Package required_features must be an array.";
        }
      return NO;
    }
  if (forbiddenFeatures != nil && (id)forbiddenFeatures != (id)[NSNull null] &&
      [forbiddenFeatures isKindOfClass: [NSArray class]] == NO)
    {
      if (reason != NULL)
        {
          *reason = @"Package forbidden_features must be an array.";
        }
      return NO;
    }
  [self appendInstallTrace: @"requirements shape ok"];
  if ([requirements objectForKey: @"supported_os"] != nil &&
      ![self dictionaryArray: [requirements objectForKey: @"supported_os"] containsString: [environment objectForKey: @"os"]])
    {
      if (reason != NULL)
        {
          *reason = @"Package does not support the detected operating system.";
        }
      return NO;
    }
  if ([requirements objectForKey: @"supported_arch"] != nil &&
      ![self dictionaryArray: [requirements objectForKey: @"supported_arch"] containsString: [environment objectForKey: @"arch"]])
    {
      if (reason != NULL)
        {
          *reason = @"Package does not support the detected architecture.";
        }
      return NO;
    }
  if ([requirements objectForKey: @"supported_compiler_families"] != nil &&
      ![self dictionaryArray: [requirements objectForKey: @"supported_compiler_families"] containsString: [toolchain objectForKey: @"compiler_family"]])
    {
      if (reason != NULL)
        {
          *reason = @"Package does not support the detected compiler family.";
        }
      return NO;
    }
  if ([requirements objectForKey: @"supported_objc_runtimes"] != nil &&
      ![self dictionaryArray: [requirements objectForKey: @"supported_objc_runtimes"] containsString: [toolchain objectForKey: @"objc_runtime"]])
    {
      if (reason != NULL)
        {
          *reason = @"Package does not support the detected Objective-C runtime.";
        }
      return NO;
    }
  if ([requirements objectForKey: @"supported_objc_abi"] != nil &&
      ![self dictionaryArray: [requirements objectForKey: @"supported_objc_abi"] containsString: [toolchain objectForKey: @"objc_abi"]])
    {
      if (reason != NULL)
        {
          *reason = @"Package does not support the detected Objective-C ABI.";
        }
      return NO;
    }
  for (i = 0; i < [requiredFeatures count]; i++)
    {
      NSString *feature = [requiredFeatures objectAtIndex: i];
      if ([[featureFlags objectForKey: feature] boolValue] == NO)
        {
          if (reason != NULL)
            {
              *reason = [NSString stringWithFormat: @"Package requires Objective-C feature '%@'.", feature];
            }
          return NO;
        }
    }
  for (i = 0; i < [forbiddenFeatures count]; i++)
    {
      NSString *feature = [forbiddenFeatures objectAtIndex: i];
      if ([[featureFlags objectForKey: feature] boolValue])
        {
          if (reason != NULL)
            {
              *reason = [NSString stringWithFormat: @"Package forbids Objective-C feature '%@'.", feature];
            }
          return NO;
        }
    }
  [self appendInstallTrace: @"requirements ok"];
  return YES;
}

- (BOOL)packageArtifact:(NSDictionary *)artifact matchesEnvironment:(NSDictionary *)environment
{
  return [self artifact: artifact
           matchesHostOS: [environment objectForKey: @"os"]
                   arch: [environment objectForKey: @"arch"]] &&
         [self artifact: artifact matchesDistributionForEnvironment: environment] &&
         [self artifact: artifact matchesToolchain: [environment objectForKey: @"toolchain"]];
}

- (NSDictionary *)selectedPackageArtifactForPackage:(NSDictionary *)packageRecord
                                        environment:(NSDictionary *)environment
                                     selectionError:(NSString **)selectionError
{
  NSArray *artifacts = [packageRecord objectForKey: @"artifacts"];
  NSMutableArray *candidates = [NSMutableArray array];
  NSMutableArray *matching = [NSMutableArray array];
  NSUInteger i = 0;

  for (i = 0; i < [artifacts count]; i++)
    {
      NSDictionary *artifact = [artifacts objectAtIndex: i];
      if ([self artifact: artifact
            matchesHostOS: [environment objectForKey: @"os"]
                    arch: [environment objectForKey: @"arch"]] &&
          [self artifact: artifact matchesDistributionForEnvironment: environment])
        {
          [candidates addObject: artifact];
        }
    }
  if ([candidates count] == 0)
    {
      if (selectionError != NULL)
        {
          *selectionError = @"No package artifact matched the detected operating system and architecture.";
        }
      return nil;
    }
  if ([candidates count] == 1)
    {
      return [candidates objectAtIndex: 0];
    }
  for (i = 0; i < [candidates count]; i++)
    {
      NSDictionary *artifact = [candidates objectAtIndex: i];
      if ([self packageArtifact: artifact matchesEnvironment: environment])
        {
          [matching addObject: artifact];
        }
    }
  if ([matching count] == 1)
    {
      return [matching objectAtIndex: 0];
    }
  if (selectionError != NULL)
    {
      *selectionError = [matching count] > 1 ?
        @"Multiple package artifacts match the detected host and toolchain; selection is ambiguous." :
        @"Multiple package artifacts match the detected host, but the current environment does not identify a unique target.";
    }
  return nil;
}

- (NSDictionary *)packageRecordFromIndexPath:(NSString *)indexPath packageID:(NSString *)packageID error:(NSString **)errorMessage
{
  NSDictionary *index = [self readJSONFile: indexPath error: errorMessage];
  NSArray *packages = nil;
  NSUInteger i = 0;

  if (index == nil)
    {
      return nil;
    }
  if ([[index objectForKey: @"schema_version"] intValue] != 1)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Unsupported package index schema version.";
        }
      return nil;
    }
  packages = [index objectForKey: @"packages"];
  if ([packages isKindOfClass: [NSArray class]] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Package index does not define a packages list.";
        }
      return nil;
    }
  for (i = 0; i < [packages count]; i++)
    {
      NSDictionary *record = [packages objectAtIndex: i];
      if ([[record objectForKey: @"id"] isEqualToString: packageID])
        {
          return record;
        }
    }
  if (errorMessage != NULL)
    {
      *errorMessage = [NSString stringWithFormat: @"Package '%@' was not found in the package index.", packageID];
    }
  return nil;
}

- (NSDictionary *)executeDoctorForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *manifestPath = nil;
  NSString *interface = @"full";
  BOOL quick = YES;
  NSUInteger i = 0;
  const char *quickEnv = getenv("GNUSTEP_CLI_DOCTOR_QUICK");

  if (quickEnv != NULL)
    {
      NSString *quickValue = [[NSString stringWithUTF8String: quickEnv] lowercaseString];
      if ([quickValue isEqualToString: @"0"] ||
          [quickValue isEqualToString: @"false"] ||
          [quickValue isEqualToString: @"no"])
        {
          quick = NO;
        }
      else if ([quickValue isEqualToString: @"1"] ||
               [quickValue isEqualToString: @"true"] ||
               [quickValue isEqualToString: @"yes"])
        {
          quick = YES;
        }
    }

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--manifest"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: @"--manifest requires a value." data: nil];
            }
          manifestPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--interface"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: @"--interface requires a value." data: nil];
            }
          interface = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--quick"])
        {
          quick = YES;
        }
      else if ([argument isEqualToString: @"--full"] || [argument isEqualToString: @"--deep"])
        {
          quick = NO;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown doctor option: %@", argument] data: nil];
        }
    }

  if (manifestPath == nil)
    {
      manifestPath = [self defaultManifestPath];
    }
  if (manifestPath == nil)
    {
      *exitCode = 5;
      return [self payloadWithCommand: @"doctor" ok: NO status: @"error" summary: @"No release manifest could be resolved." data: nil];
    }

  {
    NSDictionary *payload = [self buildDoctorPayloadWithInterface: interface manifestPath: manifestPath quick: quick];
    *exitCode = [[payload objectForKey: @"ok"] boolValue] ? 0 : 3;
    return payload;
  }
}

- (NSDictionary *)buildSetupPayloadForScope:(NSString *)scope
                                 manifest:(NSString *)manifestPath
                               installRoot:(NSString *)installRoot
                                  execute:(BOOL)execute
                                  exitCode:(int *)exitCode
{
  NSString *resolvedManifest = manifestPath ? manifestPath : [self defaultManifestPath];
  NSDictionary *doctor = nil;
  NSDictionary *manifest = nil;
  NSDictionary *release = nil;
  NSArray *selectedArtifacts = nil;
  NSArray *selectionErrors = [NSArray array];
  NSString *osName = [self normalizeOSName];
  NSString *selectedRoot = installRoot ? installRoot : ([scope isEqualToString: @"system"] ? @"/opt/gnustep-cli" : [self defaultManagedRoot]);
  NSString *installMode = @"managed";
  NSString *installDisposition = @"install_managed";
  NSMutableArray *actions = [NSMutableArray array];
  NSString *summary = @"Managed installation plan created.";
  NSString *status = @"ok";
  BOOL ok = YES;
  NSString *errorMessage = nil;
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  BOOL isRoot = NO;
#else
  BOOL isRoot = (geteuid() == 0);
#endif
  BOOL rootWritable = YES;
  NSDictionary *nativeToolchain = nil;

  if (resolvedManifest == nil)
    {
      *exitCode = 5;
      return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"No release manifest could be resolved." data: nil];
    }

  doctor = [self buildDoctorPayloadWithInterface: @"full" manifestPath: resolvedManifest];
  nativeToolchain = [[doctor objectForKey: @"environment"] objectForKey: @"native_toolchain"];
  manifest = [self validateAndLoadManifest: resolvedManifest error: &errorMessage];
  if (manifest != nil)
    {
      release = [self selectReleaseFromManifest: manifest];
      selectedArtifacts = [self selectedArtifactsForRelease: release
                                                environment: [doctor objectForKey: @"environment"]
                                            selectionErrors: &selectionErrors];
    }
  else
    {
      selectedArtifacts = [NSArray array];
    }

  {
    NSFileManager *fileManager = [NSFileManager defaultManager];
    NSString *expandedRoot = [selectedRoot stringByExpandingTildeInPath];
    NSString *writableProbe = expandedRoot;
    BOOL isDirectory = NO;

    if (![fileManager fileExistsAtPath: writableProbe isDirectory: &isDirectory])
      {
        writableProbe = [expandedRoot stringByDeletingLastPathComponent];
        if ([writableProbe length] == 0)
          {
            writableProbe = expandedRoot;
          }
      }

    rootWritable = [fileManager isWritableFileAtPath: writableProbe];
  }

  if (manifest == nil)
    {
      ok = NO;
      status = @"error";
      summary = @"Release manifest validation failed.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         errorMessage, @"message",
                                         nil]];
      *exitCode = 2;
    }
  else if ([scope isEqualToString: @"system"] && !isRoot)
    {
      ok = NO;
      status = @"error";
      summary = @"System-wide installation requires elevated privileges.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"rerun_with_elevated_privileges", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"Re-run this command with sudo.", @"message",
                                         nil]];
      *exitCode = 3;
    }
  else if (installRoot != nil && !rootWritable)
    {
      ok = NO;
      status = @"error";
      summary = @"The selected install root is not writable.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"rerun_with_elevated_privileges", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"Choose a writable install root or rerun with sufficient privileges.", @"message",
                                         nil]];
      *exitCode = 3;
    }
  else if ([[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"preferred"] ||
           [[nativeToolchain objectForKey: @"assessment"] isEqualToString: @"supported"])
    {
      installMode = @"native";
      installDisposition = @"use_existing_toolchain";
      summary = @"Using the detected native GNUstep toolchain; managed installation is not required.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"use_existing_toolchain", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         [nativeToolchain objectForKey: @"message"], @"message",
                                         nil]];
      *exitCode = 0;
    }
  else if ([selectionErrors count] > 0)
    {
      ok = NO;
      status = @"error";
      summary = @"Managed artifact selection failed.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         [selectionErrors objectAtIndex: 0], @"message",
                                         nil]];
      *exitCode = 4;
    }
  else if ([selectedArtifacts count] == 0)
    {
      ok = NO;
      status = @"error";
      summary = @"No managed artifacts were found for this host.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"No compatible managed artifacts are available for this host yet.", @"message",
                                         nil]];
      *exitCode = 4;
    }
  else if ([selectedArtifacts count] < 2)
    {
      status = @"warning";
      summary = @"Managed installation plan created, but the manifest does not yet contain a complete artifact set.";
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"report_bug", @"kind",
                                         [NSNumber numberWithInt: 2], @"priority",
                                         @"The current manifest is missing either the CLI or toolchain artifact for this host.", @"message",
                                         nil]];
      *exitCode = 0;
    }
  else
    {
      [actions addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         execute ? @"apply_install_plan" : @"apply_install_plan", @"kind",
                                         [NSNumber numberWithInt: 1], @"priority",
                                         @"Proceed with artifact download, verification, and managed installation.", @"message",
                                         nil]];
      *exitCode = 0;
    }

  {
    NSMutableArray *artifactIds = [NSMutableArray array];
    NSUInteger i = 0;
    for (i = 0; i < [selectedArtifacts count]; i++)
      {
        [artifactIds addObject: [[selectedArtifacts objectAtIndex: i] objectForKey: @"id"]];
      }
    return [NSDictionary dictionaryWithObjectsAndKeys:
                          [NSNumber numberWithInt: 1], @"schema_version",
                          @"setup", @"command",
                          @"0.1.0-dev", @"cli_version",
                          [NSNumber numberWithBool: ok], @"ok",
                          status, @"status",
                          summary, @"summary",
                          [NSDictionary dictionaryWithObjectsAndKeys:
                                          [doctor objectForKey: @"status"], @"status",
                                          [doctor objectForKey: @"environment_classification"], @"environment_classification",
                                          [doctor objectForKey: @"summary"], @"summary",
                                          osName, @"os",
                                          nil], @"doctor",
                          [NSDictionary dictionaryWithObjectsAndKeys:
                                          scope, @"scope",
                                          installMode, @"install_mode",
                                          installDisposition, @"disposition",
                                          selectedRoot, @"install_root",
                                          @"stable", @"channel",
                                          resolvedManifest, @"manifest_path",
                                          release ? [release objectForKey: @"version"] : [NSNull null], @"selected_release",
                                          [doctor objectForKey: @"native_toolchain_assessment"], @"native_toolchain_assessment",
                                          artifactIds, @"selected_artifacts",
                                          [NSNumber numberWithBool: ([scope isEqualToString: @"system"] ? isRoot : YES)], @"system_privileges_ok",
                                          manifest ? [NSArray array] : [NSArray arrayWithObject: errorMessage], @"manifest_validation_errors",
                                          selectionErrors, @"selection_errors",
                                          nil], @"plan",
                          actions, @"actions",
                          nil];
  }
}

- (BOOL)downloadURLString:(NSString *)urlString toPath:(NSString *)destination error:(NSString **)errorMessage
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSURL *url = [NSURL URLWithString: urlString];
  NSData *data = nil;
  NSString *localPath = [self resolvedArtifactPathFromURLString: urlString];

  if (localPath != nil && [manager fileExistsAtPath: localPath])
    {
      [manager removeItemAtPath: destination error: NULL];
      return [manager copyItemAtPath: localPath toPath: destination error: NULL];
    }

  if (url == nil || [url scheme] == nil)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Artifact URL could not be resolved.";
        }
      return NO;
    }
  data = [NSData dataWithContentsOfURL: url];
  if (data == nil || [data writeToFile: destination atomically: YES] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = [NSString stringWithFormat: @"Failed to download %@", urlString];
        }
      return NO;
    }
  return YES;
}

- (BOOL)relocateManagedToolchainForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSDirectoryEnumerator *enumerator = [manager enumeratorAtPath: installRoot];
  NSString *relative = nil;
  NSString *placeholder = @"__GNUSTEP_CLI_INSTALL_ROOT__";

  while ((relative = [enumerator nextObject]) != nil)
    {
      NSString *path = [installRoot stringByAppendingPathComponent: relative];
      BOOL isDir = NO;
      NSData *data = nil;
      NSString *content = nil;
      NSString *updated = nil;

      if ([manager fileExistsAtPath: path isDirectory: &isDir] == NO || isDir)
        {
          continue;
        }

      data = [NSData dataWithContentsOfFile: path];
      if (data == nil)
        {
          continue;
        }
      if ([data rangeOfData: [NSData dataWithBytes: "\0" length: 1]
                    options: 0
                      range: NSMakeRange(0, [data length])].location != NSNotFound)
        {
          continue;
        }
      content = [[NSString alloc] initWithData: data encoding: NSUTF8StringEncoding];
      if (content == nil)
        {
          continue;
        }
      updated = [content stringByReplacingOccurrencesOfString: placeholder withString: installRoot];
      if ([updated isEqualToString: content] == NO && [self writeString: updated toPath: path] == NO)
        {
          if (errorMessage != NULL)
            {
              *errorMessage = [NSString stringWithFormat: @"Failed to relocate managed toolchain file %@", relative];
            }
          return NO;
        }
    }

  return YES;
}

- (BOOL)installManagedLauncherForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  return YES;
#else
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *binPath = [[installRoot stringByAppendingPathComponent: @"bin"] stringByAppendingPathComponent: @"gnustep"];
  NSString *realDir = [[installRoot stringByAppendingPathComponent: @"libexec/gnustep-cli"] stringByAppendingPathComponent: @"bin"];
  NSString *realPath = [realDir stringByAppendingPathComponent: @"gnustep-real"];
  NSString *script = nil;

  if ([manager fileExistsAtPath: binPath] == NO)
    {
      return YES;
    }

  if ([manager fileExistsAtPath: [realDir stringByAppendingPathComponent: @"gnustep"]])
    {
      chmod([binPath fileSystemRepresentation], 0755);
      chmod([[realDir stringByAppendingPathComponent: @"gnustep"] fileSystemRepresentation], 0755);
      return YES;
    }

  [manager createDirectoryAtPath: realDir withIntermediateDirectories: YES attributes: nil error: NULL];
  [manager removeItemAtPath: realPath error: NULL];
  if ([manager moveItemAtPath: binPath toPath: realPath error: NULL] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Failed to stage managed CLI runtime binary.";
        }
      return NO;
    }

  script = @"#!/bin/sh\n"
           @"ROOT=$(cd \"$(dirname \"$0\")/..\" && pwd)\n"
           @"export LD_LIBRARY_PATH=\"$ROOT/lib:$ROOT/lib64:$ROOT/Local/Library/Libraries:$ROOT/System/Library/Libraries${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"\n"
           @"exec \"$ROOT/libexec/gnustep-cli/bin/gnustep-real\" \"$@\"\n";

  if ([self writeString: script toPath: binPath] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Failed to write managed CLI launcher.";
        }
      return NO;
    }
  chmod([binPath fileSystemRepresentation], 0755);
  chmod([realPath fileSystemRepresentation], 0755);
  return YES;
#endif
}




- (BOOL)smokeVersionedReleaseAtPath:(NSString *)releaseRoot error:(NSString **)errorMessage
{
  NSString *launcher = [[releaseRoot stringByAppendingPathComponent: @"bin"] stringByAppendingPathComponent: @"gnustep"];
  NSDictionary *result = nil;

  if ([[NSFileManager defaultManager] fileExistsAtPath: launcher] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Candidate release does not contain bin/gnustep.";
        }
      return NO;
    }

  result = [self runCommand: [NSArray arrayWithObjects: launcher, @"--version", nil] currentDirectory: nil];
  if ([[result objectForKey: @"exit_status"] intValue] != 0)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Candidate release failed post-upgrade smoke validation.";
        }
      return NO;
    }
  return YES;
}

- (BOOL)installCurrentPointerLauncherForInstallRoot:(NSString *)installRoot error:(NSString **)errorMessage
{
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  return YES;
#else
  NSString *binDir = [installRoot stringByAppendingPathComponent: @"bin"];
  NSString *binPath = [binDir stringByAppendingPathComponent: @"gnustep"];
  NSString *script = @"#!/bin/sh\n"
                    @"ROOT=$(cd \"$(dirname \"$0\")/..\" && pwd)\n"
                    @"exec \"$ROOT/current/bin/gnustep\" \"$@\"\n";
  [[NSFileManager defaultManager] createDirectoryAtPath: binDir withIntermediateDirectories: YES attributes: nil error: NULL];
  if ([self writeString: script toPath: binPath] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Failed to write current-pointer launcher.";
        }
      return NO;
    }
  chmod([binPath fileSystemRepresentation], 0755);
  return YES;
#endif
}

- (NSString *)materializeVersionedReleaseForInstallRoot:(NSString *)installRoot version:(NSString *)version error:(NSString **)errorMessage
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *safeVersion = version ? version : @"unknown";
  NSString *releasesRoot = [installRoot stringByAppendingPathComponent: @"releases"];
  NSString *releaseRoot = [releasesRoot stringByAppendingPathComponent: safeVersion];
  NSString *currentPath = [installRoot stringByAppendingPathComponent: @"current"];
  NSArray *skipNames = [NSArray arrayWithObjects:
                                  @"releases",
                                  @"current",
                                  @"state",
                                  @"packages",
                                  @".staging",
                                  @".transactions",
                                  nil];
  NSArray *children = nil;
  NSUInteger i = 0;

  [manager createDirectoryAtPath: releasesRoot withIntermediateDirectories: YES attributes: nil error: NULL];
  [manager removeItemAtPath: releaseRoot error: NULL];
  [manager createDirectoryAtPath: releaseRoot withIntermediateDirectories: YES attributes: nil error: NULL];

  children = [manager contentsOfDirectoryAtPath: installRoot error: NULL];
  for (i = 0; i < [children count]; i++)
    {
      NSString *name = [children objectAtIndex: i];
      NSString *source = [installRoot stringByAppendingPathComponent: name];
      NSString *destination = [releaseRoot stringByAppendingPathComponent: name];
      if ([skipNames containsObject: name])
        {
          continue;
        }
      [manager removeItemAtPath: destination error: NULL];
      if ([manager copyItemAtPath: source toPath: destination error: NULL] == NO)
        {
          if (errorMessage != NULL)
            {
              *errorMessage = [NSString stringWithFormat: @"Failed to snapshot managed release item %@.", name];
            }
          return nil;
        }
    }

  if ([self smokeVersionedReleaseAtPath: releaseRoot error: errorMessage] == NO)
    {
      return nil;
    }

  [manager removeItemAtPath: currentPath error: NULL];
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  [manager createDirectoryAtPath: currentPath withIntermediateDirectories: YES attributes: nil error: NULL];
#else
  if ([manager createSymbolicLinkAtPath: currentPath withDestinationPath: releaseRoot error: NULL] == NO)
    {
      if (errorMessage != NULL)
        {
          *errorMessage = @"Failed to activate managed release pointer.";
        }
      return nil;
    }
#endif
  if ([self installCurrentPointerLauncherForInstallRoot: installRoot error: errorMessage] == NO)
    {
      return nil;
    }
  return releaseRoot;
}

- (NSDictionary *)rollbackManagedInstallRoot:(NSString *)installRoot exitCode:(int *)exitCode
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *root = [installRoot stringByExpandingTildeInPath];
  NSDictionary *state = [self installedLifecycleStateForInstallRoot: root];
  NSString *previous = [state objectForKey: @"previous_release_path"];
  NSString *statePath = [[root stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"cli-state.json"];
  NSMutableDictionary *rolledBackState = nil;

  if ([previous isKindOfClass: [NSString class]] == NO || [manager fileExistsAtPath: previous] == NO)
    {
      *exitCode = 3;
      return [self payloadWithCommand: @"setup"
                                   ok: NO
                               status: @"error"
                              summary: @"No previous managed release is available for rollback."
                                 data: [NSDictionary dictionaryWithObjectsAndKeys: root, @"install_root", state, @"installed_state", nil]];
    }

  [manager removeItemAtPath: root error: NULL];
  if ([manager moveItemAtPath: previous toPath: root error: NULL] == NO)
    {
      *exitCode = 1;
      return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"Failed to restore previous managed release." data: nil];
    }

  rolledBackState = [[[self installedLifecycleStateForInstallRoot: root] mutableCopy] autorelease];
  if (rolledBackState == nil)
    {
      rolledBackState = [NSMutableDictionary dictionary];
      [rolledBackState setObject: [NSNumber numberWithInt: 1] forKey: @"schema_version"];
    }
  [rolledBackState setObject: @"rollback" forKey: @"last_action"];
  [rolledBackState setObject: @"healthy" forKey: @"status"];
  [rolledBackState setObject: [NSNull null] forKey: @"previous_release_path"];
  [self writeJSONStringObject: rolledBackState toPath: statePath error: NULL];
  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"setup", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Managed rollback completed.", @"summary",
                        @"rollback", @"operation",
                        root, @"install_root",
                        previous, @"restored_from",
                        nil];
}

- (NSDictionary *)repairManagedInstallRoot:(NSString *)installRoot
{
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *root = [installRoot stringByExpandingTildeInPath];
  NSString *stateDir = [root stringByAppendingPathComponent: @"state"];
  NSString *packagesDir = [root stringByAppendingPathComponent: @"packages"];
  NSString *staging = [root stringByAppendingPathComponent: @".staging"];
  NSString *transactions = [root stringByAppendingPathComponent: @".transactions"];
  NSString *setupTransaction = [stateDir stringByAppendingPathComponent: @"setup-transaction.json"];
  NSString *statePath = [stateDir stringByAppendingPathComponent: @"cli-state.json"];
  NSMutableArray *issues = [NSMutableArray array];
  NSMutableArray *repairs = [NSMutableArray array];
  NSMutableDictionary *state = nil;

  if ([manager fileExistsAtPath: stateDir] == NO)
    {
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"missing_directory", @"code", @"Missing state directory.", @"message", nil]];
      [manager createDirectoryAtPath: stateDir withIntermediateDirectories: YES attributes: nil error: NULL];
      [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"create_directory", @"kind", stateDir, @"path", nil]];
    }
  if ([manager fileExistsAtPath: packagesDir] == NO)
    {
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"missing_directory", @"code", @"Missing packages directory.", @"message", nil]];
      [manager createDirectoryAtPath: packagesDir withIntermediateDirectories: YES attributes: nil error: NULL];
      [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"create_directory", @"kind", packagesDir, @"path", nil]];
    }
  if ([manager fileExistsAtPath: staging])
    {
      [manager removeItemAtPath: staging error: NULL];
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"stale_staging", @"code", @"Stale staging directory was present.", @"message", nil]];
      [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"clear_staging", @"kind", staging, @"path", nil]];
    }
  if ([manager fileExistsAtPath: transactions])
    {
      [manager removeItemAtPath: transactions error: NULL];
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"stale_transactions", @"code", @"Stale transaction directory was present.", @"message", nil]];
      [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"clear_transactions", @"kind", transactions, @"path", nil]];
    }
  if ([manager fileExistsAtPath: setupTransaction])
    {
      [manager removeItemAtPath: setupTransaction error: NULL];
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"stale_setup_transaction", @"code", @"Stale setup transaction was present.", @"message", nil]];
      [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"clear_setup_transaction", @"kind", setupTransaction, @"path", nil]];
    }

  if ([manager fileExistsAtPath: statePath])
    {
      NSDictionary *loaded = [self readJSONFile: statePath error: NULL];
      state = loaded != nil ? [[loaded mutableCopy] autorelease] : [NSMutableDictionary dictionary];
    }
  else
    {
      state = [NSMutableDictionary dictionary];
      [state setObject: [NSNumber numberWithInt: 1] forKey: @"schema_version"];
      [state setObject: [NSNull null] forKey: @"cli_version"];
      [state setObject: [NSNull null] forKey: @"toolchain_version"];
      [state setObject: [NSNumber numberWithInt: 1] forKey: @"packages_version"];
      [state setObject: [NSNull null] forKey: @"last_action"];
      [state setObject: @"unknown" forKey: @"status"];
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"missing_state", @"code", @"CLI state file was missing.", @"message", nil]];
    }

  if ([[state objectForKey: @"status"] isEqualToString: @"installing"] ||
      [[state objectForKey: @"status"] isEqualToString: @"upgrading"] ||
      [[state objectForKey: @"status"] isEqualToString: @"repairing"])
    {
      [state setObject: @"needs_repair" forKey: @"status"];
      [issues addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"interrupted_lifecycle_action", @"code", @"Managed lifecycle action was interrupted.", @"message", nil]];
      [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"mark_needs_repair", @"kind", @"Marked interrupted managed environment for explicit repair validation.", @"message", nil]];
    }
  [self writeJSONStringObject: state toPath: statePath error: NULL];
  [repairs addObject: [NSDictionary dictionaryWithObjectsAndKeys: @"normalize_state", @"kind", statePath, @"path", nil]];

  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"setup", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Managed environment repair scan completed.", @"summary",
                        root, @"install_root",
                        issues, @"issues",
                        repairs, @"repairs",
                        nil];
}

- (NSDictionary *)buildUpdatePlanForScope:(NSString *)scope
                                  manifest:(NSString *)manifestPath
                               installRoot:(NSString *)installRoot
                                  exitCode:(int *)exitCode
{
  NSString *root = (installRoot != nil ? installRoot : ([scope isEqualToString: @"system"] ? @"/opt/gnustep-cli" : [self defaultManagedRoot]));
  NSString *expandedRoot = [root stringByExpandingTildeInPath];
  NSString *resolvedManifest = manifestPath ? manifestPath : [self defaultManifestPath];
  NSDictionary *installedState = [self installedLifecycleStateForInstallRoot: expandedRoot];
  NSDictionary *manifest = nil;
  NSDictionary *release = nil;
  NSDictionary *doctor = nil;
  NSArray *artifacts = nil;
  NSArray *selectionErrors = nil;
  NSMutableArray *effectiveSelectionErrors = [NSMutableArray array];
  NSMutableArray *artifactIDs = [NSMutableArray array];
  NSMutableArray *layers = [NSMutableArray array];
  NSString *policyError = nil;
  BOOL downgradeDetected = NO;
  NSString *manifestError = nil;
  NSString *installedVersion = [installedState objectForKey: @"cli_version"];
  NSString *latestVersion = nil;
  NSString *installedCliSHA256 = [installedState objectForKey: @"cli_artifact_sha256"];
  NSString *installedToolchainSHA256 = [installedState objectForKey: @"toolchain_artifact_sha256"];
  NSDictionary *cliArtifact = nil;
  NSDictionary *toolchainArtifact = nil;
  BOOL cliLayerChanged = NO;
  BOOL toolchainLayerChanged = NO;
  unsigned long long plannedDownloadSize = 0;
  NSString *layerUpdateKind = @"none";
  BOOL updateAvailable = NO;
  NSUInteger i = 0;

  if ([[installedState objectForKey: @"status"] isEqualToString: @"needs_repair"])
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"setup", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Managed install state requires repair before checking for updates.", @"summary",
                            expandedRoot, @"install_root",
                            installedState, @"installed_state",
                            nil];
    }

  if (resolvedManifest == nil)
    {
      *exitCode = 5;
      return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"No release manifest could be resolved." data: nil];
    }

  manifest = [self validateAndLoadManifest: resolvedManifest error: &manifestError];
  if (manifest != nil)
    {
      release = [self selectReleaseFromManifest: manifest];
      latestVersion = [release objectForKey: @"version"];
    }
  doctor = [self buildDoctorPayloadWithInterface: @"full" manifestPath: resolvedManifest];
  if (release != nil)
    {
      artifacts = [self selectedArtifactsForRelease: release
                                        environment: [doctor objectForKey: @"environment"]
                                    selectionErrors: &selectionErrors];
    }
  else
    {
      artifacts = [NSArray array];
      selectionErrors = [NSArray arrayWithObject: (manifestError ? manifestError : @"No release could be selected.")];
    }

  for (i = 0; i < [artifacts count]; i++)
    {
      NSDictionary *artifact = [artifacts objectAtIndex: i];
      [artifactIDs addObject: [artifact objectForKey: @"id"]];
      if ([[artifact objectForKey: @"kind"] isEqualToString: @"cli"])
        {
          cliArtifact = artifact;
        }
      else if ([[artifact objectForKey: @"kind"] isEqualToString: @"toolchain"])
        {
          toolchainArtifact = artifact;
        }
    }
  if (selectionErrors != nil)
    {
      [effectiveSelectionErrors addObjectsFromArray: selectionErrors];
    }
  if (manifest != nil && artifacts != nil && [self manifest: manifest revokesArtifacts: artifacts error: &policyError])
    {
      [effectiveSelectionErrors addObject: policyError];
    }
  if (manifest != nil && [self manifest: manifest isOlderThanInstalledState: installedState error: &policyError])
    {
      [effectiveSelectionErrors addObject: policyError];
    }
  downgradeDetected = (installedVersion != nil && latestVersion != nil && [self compareVersionString: latestVersion toVersionString: installedVersion] == NSOrderedAscending);
  if (downgradeDetected)
    {
      [effectiveSelectionErrors addObject: @"Selected release is older than the installed CLI version."];
    }
  updateAvailable = (latestVersion != nil && downgradeDetected == NO && (installedVersion == nil || [installedVersion isEqualToString: latestVersion] == NO));
  if (cliArtifact != nil)
    {
      NSString *artifactSHA256 = [cliArtifact objectForKey: @"sha256"];
      NSNumber *size = [cliArtifact objectForKey: @"size"];
      if (installedCliSHA256 != nil && artifactSHA256 != nil && (id)installedCliSHA256 != [NSNull null])
        {
          cliLayerChanged = [installedCliSHA256 isEqualToString: artifactSHA256] == NO;
        }
      else
        {
          cliLayerChanged = updateAvailable;
        }
      if (cliLayerChanged && size != nil && (id)size != [NSNull null])
        {
          plannedDownloadSize += [size unsignedLongLongValue];
        }
      [layers addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"cli", @"name",
                                         [cliArtifact objectForKey: @"id"] ? [cliArtifact objectForKey: @"id"] : [NSNull null], @"artifact_id",
                                         artifactSHA256 ? artifactSHA256 : [NSNull null], @"sha256",
                                         installedCliSHA256 ? installedCliSHA256 : [NSNull null], @"current_sha256",
                                         cliLayerChanged ? @"update" : @"reuse", @"action",
                                         [NSNumber numberWithBool: cliLayerChanged], @"download_required",
                                         size ? size : [NSNull null], @"size",
                                         nil]];
    }
  if (toolchainArtifact != nil)
    {
      NSString *artifactSHA256 = [toolchainArtifact objectForKey: @"sha256"];
      NSNumber *size = [toolchainArtifact objectForKey: @"size"];
      BOOL reusedReference = [[toolchainArtifact objectForKey: @"reused"] boolValue];
      if (installedToolchainSHA256 != nil && artifactSHA256 != nil && (id)installedToolchainSHA256 != [NSNull null])
        {
          toolchainLayerChanged = [installedToolchainSHA256 isEqualToString: artifactSHA256] == NO;
        }
      else
        {
          toolchainLayerChanged = updateAvailable && reusedReference == NO;
        }
      if (toolchainLayerChanged && reusedReference == NO && size != nil && (id)size != [NSNull null])
        {
          plannedDownloadSize += [size unsignedLongLongValue];
        }
      [layers addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         @"toolchain", @"name",
                                         [toolchainArtifact objectForKey: @"id"] ? [toolchainArtifact objectForKey: @"id"] : [NSNull null], @"artifact_id",
                                         artifactSHA256 ? artifactSHA256 : [NSNull null], @"sha256",
                                         installedToolchainSHA256 ? installedToolchainSHA256 : [NSNull null], @"current_sha256",
                                         toolchainLayerChanged ? @"update" : @"reuse", @"action",
                                         [NSNumber numberWithBool: (toolchainLayerChanged && reusedReference == NO)], @"download_required",
                                         [NSNumber numberWithBool: reusedReference], @"reused_manifest_reference",
                                         size ? size : [NSNull null], @"size",
                                         nil]];
    }
  if (cliLayerChanged && toolchainLayerChanged == NO)
    {
      layerUpdateKind = @"cli_only";
    }
  else if (toolchainLayerChanged)
    {
      layerUpdateKind = @"toolchain_required";
    }

  *exitCode = (manifest != nil && [effectiveSelectionErrors count] == 0) ? 0 : 3;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"setup", @"command",
                        [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                        (*exitCode == 0 ? @"ok" : @"error"), @"status",
                        (downgradeDetected ? @"The selected release manifest is older than the installed CLI." : (updateAvailable ? @"A compatible update is available." : @"The managed install is already current.")), @"summary",
                        @"check_updates", @"operation",
                        expandedRoot, @"install_root",
                        resolvedManifest, @"manifest_path",
                        installedState, @"installed_state",
                        [NSDictionary dictionaryWithObjectsAndKeys:
                                      (installedVersion ? installedVersion : [NSNull null]), @"installed_version",
                                      (latestVersion ? latestVersion : [NSNull null]), @"latest_compatible_version",
                                      [NSNumber numberWithBool: updateAvailable], @"update_available",
                                      [NSNumber numberWithBool: downgradeDetected], @"downgrade_detected",
                                      artifactIDs, @"selected_artifacts",
                                      layerUpdateKind, @"layer_update_kind",
                                      [NSNumber numberWithUnsignedLongLong: plannedDownloadSize], @"planned_download_size",
                                      layers, @"layers",
                                      effectiveSelectionErrors, @"selection_errors",
                                      nil], @"update_plan",
                        nil];
}

- (NSDictionary *)executeSetupForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *scope = @"user";
  NSString *manifestPath = nil;
  NSString *installRoot = nil;
  BOOL repairMode = NO;
  BOOL checkUpdatesMode = NO;
  BOOL upgradeMode = NO;
  BOOL rollbackMode = NO;
  NSUInteger i = 0;
  NSDictionary *payload = nil;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--system"])
        {
          scope = @"system";
        }
      else if ([argument isEqualToString: @"--user"])
        {
          scope = @"user";
        }
      else if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          installRoot = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--repair"])
        {
          repairMode = YES;
        }
      else if ([argument isEqualToString: @"--check-updates"])
        {
          checkUpdatesMode = YES;
        }
      else if ([argument isEqualToString: @"--upgrade"])
        {
          upgradeMode = YES;
        }
      else if ([argument isEqualToString: @"--rollback"])
        {
          rollbackMode = YES;
        }
      else if ([argument isEqualToString: @"--manifest"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"--manifest requires a value." data: nil];
            }
          manifestPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown setup option: %@", argument] data: nil];
        }
    }

  if ((repairMode && checkUpdatesMode) || (repairMode && upgradeMode) || (repairMode && rollbackMode) ||
      (checkUpdatesMode && upgradeMode) || (checkUpdatesMode && rollbackMode) || (upgradeMode && rollbackMode))
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"--repair, --check-updates, --upgrade, and --rollback are mutually exclusive." data: nil];
    }

  if (repairMode)
    {
      NSString *repairRoot = installRoot != nil ? installRoot : ([scope isEqualToString: @"system"] ? @"/opt/gnustep-cli" : [self defaultManagedRoot]);
      *exitCode = 0;
      return [self repairManagedInstallRoot: repairRoot];
    }

  if (checkUpdatesMode)
    {
      return [self buildUpdatePlanForScope: scope manifest: manifestPath installRoot: installRoot exitCode: exitCode];
    }

  if (rollbackMode)
    {
      NSString *rollbackRoot = installRoot != nil ? installRoot : ([scope isEqualToString: @"system"] ? @"/opt/gnustep-cli" : [self defaultManagedRoot]);
      return [self rollbackManagedInstallRoot: rollbackRoot exitCode: exitCode];
    }

  if (upgradeMode)
    {
      NSString *upgradeRoot = (installRoot != nil ? installRoot : ([scope isEqualToString: @"system"] ? @"/opt/gnustep-cli" : [self defaultManagedRoot]));
      NSDictionary *state = [self installedLifecycleStateForInstallRoot: upgradeRoot];
      if ([[state objectForKey: @"status"] isEqualToString: @"needs_repair"])
        {
          *exitCode = 3;
          return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"Managed install state requires repair before upgrade." data: [NSDictionary dictionaryWithObjectsAndKeys: state, @"installed_state", nil]];
        }
    }

  payload = [self buildSetupPayloadForScope: scope manifest: manifestPath installRoot: installRoot execute: YES exitCode: exitCode];
  if ([[payload objectForKey: @"ok"] boolValue] == NO || [[payload objectForKey: @"status"] isEqualToString: @"warning"])
    {
      return payload;
    }
  if (upgradeMode == NO && [[[payload objectForKey: @"plan"] objectForKey: @"install_mode"] isEqualToString: @"native"])
    {
      *exitCode = 0;
      return payload;
    }

  {
    NSDictionary *manifest = [self validateAndLoadManifest: [[payload objectForKey: @"plan"] objectForKey: @"manifest_path"] error: NULL];
    NSDictionary *release = [self selectReleaseFromManifest: manifest];
    NSDictionary *doctorPayload = [self buildDoctorPayloadWithInterface: @"full"
                                                           manifestPath: [[payload objectForKey: @"plan"] objectForKey: @"manifest_path"]];
    NSArray *artifacts = [self selectedArtifactsForRelease: release
                                               environment: [doctorPayload objectForKey: @"environment"]
                                           selectionErrors: NULL];
    NSString *installPath = [[[payload objectForKey: @"plan"] objectForKey: @"install_root"] stringByExpandingTildeInPath];
    NSString *staging = [installPath stringByAppendingPathComponent: @".staging/setup"];
    NSString *downloads = [staging stringByAppendingPathComponent: @"downloads"];
    NSString *extracts = [staging stringByAppendingPathComponent: @"extracts"];
    NSMutableArray *installedArtifacts = [NSMutableArray array];
    NSFileManager *manager = [NSFileManager defaultManager];
    NSString *errorMessage = nil;
    NSString *transactionError = nil;
    NSString *backupPath = nil;
    NSString *policyError = nil;
    NSString *activeReleasePath = nil;
    NSDictionary *cliArtifact = nil;
    NSDictionary *toolchainArtifact = nil;
    NSUInteger j = 0;

    if ([self manifest: manifest revokesArtifacts: artifacts error: &policyError])
      {
        *exitCode = 3;
        return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: policyError data: nil];
      }

    if (upgradeMode)
      {
        NSDictionary *installedState = [self installedLifecycleStateForInstallRoot: installPath];
        NSString *installedVersion = [installedState objectForKey: @"cli_version"];
        NSString *targetVersion = [release objectForKey: @"version"];
        if ([self manifest: manifest isOlderThanInstalledState: installedState error: &policyError])
          {
            *exitCode = 3;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: policyError data: [NSDictionary dictionaryWithObjectsAndKeys: installedState, @"installed_state", targetVersion, @"target_version", nil]];
          }
        if (installedVersion != nil && targetVersion != nil && [self compareVersionString: targetVersion toVersionString: installedVersion] == NSOrderedAscending)
          {
            *exitCode = 3;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: @"Refusing to downgrade the managed CLI through setup --upgrade." data: [NSDictionary dictionaryWithObjectsAndKeys: installedState, @"installed_state", targetVersion, @"target_version", nil]];
          }
      }

    if ([self beginSetupTransactionForInstallRoot: installPath
                                          release: [release objectForKey: @"version"]
                                        artifacts: [[payload objectForKey: @"plan"] objectForKey: @"selected_artifacts"]
                                        backupPath: &backupPath
                                             error: &transactionError] == NO)
      {
        *exitCode = 1;
        return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: transactionError data: nil];
      }

    [manager createDirectoryAtPath: downloads withIntermediateDirectories: YES attributes: nil error: NULL];
    [manager createDirectoryAtPath: extracts withIntermediateDirectories: YES attributes: nil error: NULL];
    [manager createDirectoryAtPath: installPath withIntermediateDirectories: YES attributes: nil error: NULL];

    for (j = 0; j < [artifacts count]; j++)
      {
        NSDictionary *artifact = [artifacts objectAtIndex: j];
        NSString *sourcePath = nil;
        NSString *localCandidate = [[[payload objectForKey: @"plan"] objectForKey: @"manifest_path"] stringByDeletingLastPathComponent];
        NSString *downloadPath = [downloads stringByAppendingPathComponent: [[artifact objectForKey: @"url"] lastPathComponent]];
        NSString *extractPath = [extracts stringByAppendingPathComponent: [artifact objectForKey: @"id"]];
        NSString *copyError = nil;
        NSString *checksum = nil;
        NSString *sourceRoot = nil;

        if ([[artifact objectForKey: @"kind"] isEqualToString: @"cli"])
          {
            cliArtifact = artifact;
          }
        else if ([[artifact objectForKey: @"kind"] isEqualToString: @"toolchain"])
          {
            toolchainArtifact = artifact;
          }

        if ([artifact objectForKey: @"filename"] != nil)
          {
            localCandidate = [localCandidate stringByAppendingPathComponent: [artifact objectForKey: @"filename"]];
          }
        else
          {
            localCandidate = [localCandidate stringByAppendingPathComponent: [[artifact objectForKey: @"url"] lastPathComponent]];
          }

        if ([manager fileExistsAtPath: localCandidate])
          {
            [manager removeItemAtPath: downloadPath error: NULL];
            [manager copyItemAtPath: localCandidate toPath: downloadPath error: NULL];
          }
        else if ([self downloadURLString: [artifact objectForKey: @"url"] toPath: downloadPath error: &errorMessage] == NO)
          {
            [manager removeItemAtPath: staging error: NULL];
            [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
          }

        sourcePath = downloadPath;
        checksum = [self sha256ForFile: sourcePath];
        if (checksum == nil || [checksum isEqualToString: [artifact objectForKey: @"sha256"]] == NO)
          {
            [manager removeItemAtPath: staging error: NULL];
            [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: [NSString stringWithFormat: @"checksum mismatch for %@", [artifact objectForKey: @"id"]] data: nil];
          }

        if ([self extractArchive: sourcePath toDirectory: extractPath error: &errorMessage] == NO)
          {
            [manager removeItemAtPath: staging error: NULL];
            [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
          }

        sourceRoot = [self singleChildDirectoryOrSelf: extractPath];
        if ([self copyTreeContentsFrom: sourceRoot to: installPath error: &copyError] == NO)
          {
            [manager removeItemAtPath: staging error: NULL];
            [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
            *exitCode = 1;
            return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: copyError data: nil];
          }
        [installedArtifacts addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                        [artifact objectForKey: @"id"], @"artifact_id",
                                                        [NSArray arrayWithObject: installPath], @"paths",
                                                        nil]];
      }

    if ([self relocateManagedToolchainForInstallRoot: installPath error: &errorMessage] == NO)
      {
        [manager removeItemAtPath: staging error: NULL];
        [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
        *exitCode = 1;
        return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
      }

    if ([self installManagedLauncherForInstallRoot: installPath error: &errorMessage] == NO)
      {
        [manager removeItemAtPath: staging error: NULL];
        [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
        *exitCode = 1;
        return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
      }

    activeReleasePath = [self materializeVersionedReleaseForInstallRoot: installPath
                                                                version: [release objectForKey: @"version"]
                                                                  error: &errorMessage];
    if (activeReleasePath == nil)
      {
        [manager removeItemAtPath: staging error: NULL];
        [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: NO];
        *exitCode = 1;
        return [self payloadWithCommand: @"setup" ok: NO status: @"error" summary: errorMessage data: nil];
      }

    {
      NSString *stateDir = [installPath stringByAppendingPathComponent: @"state"];
      NSString *statePath = [stateDir stringByAppendingPathComponent: @"cli-state.json"];
      NSString *writeError = nil;
      [manager createDirectoryAtPath: stateDir withIntermediateDirectories: YES attributes: nil error: NULL];
      [self writeJSONStringObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                   [NSNumber numberWithInt: 1], @"schema_version",
                                                   [release objectForKey: @"version"], @"cli_version",
                                                   [release objectForKey: @"version"], @"toolchain_version",
                                                   (cliArtifact && [cliArtifact objectForKey: @"id"]) ? [cliArtifact objectForKey: @"id"] : [NSNull null], @"cli_artifact_id",
                                                   (cliArtifact && [cliArtifact objectForKey: @"sha256"]) ? [cliArtifact objectForKey: @"sha256"] : [NSNull null], @"cli_artifact_sha256",
                                                   (toolchainArtifact && [toolchainArtifact objectForKey: @"id"]) ? [toolchainArtifact objectForKey: @"id"] : [NSNull null], @"toolchain_artifact_id",
                                                   (toolchainArtifact && [toolchainArtifact objectForKey: @"sha256"]) ? [toolchainArtifact objectForKey: @"sha256"] : [NSNull null], @"toolchain_artifact_sha256",
                                                   [NSNumber numberWithInt: 1], @"packages_version",
                                                   [release objectForKey: @"version"], @"active_release",
                                                   activeReleasePath ? activeReleasePath : installPath, @"active_release_path",
                                                   backupPath ? backupPath : [NSNull null], @"previous_release_path",
                                                   @"stable", @"channel",
                                                   [[payload objectForKey: @"plan"] objectForKey: @"manifest_path"], @"manifest_path",
                                                   [manifest objectForKey: @"metadata_version"] ? [manifest objectForKey: @"metadata_version"] : [NSNull null], @"last_manifest_metadata_version",
                                                   [manifest objectForKey: @"generated_at"] ? [manifest objectForKey: @"generated_at"] : [NSNull null], @"last_manifest_generated_at",
                                                   [manifest objectForKey: @"expires_at"] ? [manifest objectForKey: @"expires_at"] : [NSNull null], @"last_manifest_expires_at",
                                                   [[payload objectForKey: @"plan"] objectForKey: @"selected_artifacts"], @"selected_artifacts",
                                                   upgradeMode ? @"upgrade" : @"setup", @"last_action",
                                                   @"healthy", @"status",
                                                   nil]
                            toPath: statePath
                             error: &writeError];
    }

    [manager removeItemAtPath: staging error: NULL];
    [self finishSetupTransactionForInstallRoot: installPath backupPath: backupPath success: YES preserveBackup: upgradeMode];
    *exitCode = 0;
    return [NSDictionary dictionaryWithObjectsAndKeys:
                          [NSNumber numberWithInt: 1], @"schema_version",
                          @"setup", @"command",
                          @"0.1.0-dev", @"cli_version",
                          [NSNumber numberWithBool: YES], @"ok",
                          @"ok", @"status",
                          (upgradeMode ? @"Managed upgrade completed." : @"Managed installation completed."), @"summary",
                          [payload objectForKey: @"doctor"], @"doctor",
                          [payload objectForKey: @"plan"], @"plan",
                          upgradeMode ? @"upgrade" : @"install", @"operation",
                          [NSArray arrayWithObjects:
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"add_path", @"kind",
                                                     [NSNumber numberWithInt: 1], @"priority",
                                                     [NSString stringWithFormat: @"Add %@/bin, %@/Tools, and %@/System/Tools to PATH for future shells; the gnustep launcher sets managed runtime library paths automatically.", installPath, installPath, installPath], @"message",
                                                     nil],
                                     [NSDictionary dictionaryWithObjectsAndKeys:
                                                     @"delete_bootstrap", @"kind",
                                                     [NSNumber numberWithInt: 2], @"priority",
                                                     @"The bootstrap script is no longer required and may be deleted.", @"message",
                                                     nil],
                                     nil], @"actions",
                          [NSDictionary dictionaryWithObjectsAndKeys:
                                          installedArtifacts, @"installed_artifacts",
                                          [NSString stringWithFormat: @"export PATH=\"%@/bin:%@/Tools:%@/System/Tools:$PATH\"", installPath, installPath, installPath], @"path_hint",
                                          installPath, @"install_root",
                                          activeReleasePath ? activeReleasePath : installPath, @"active_release_path",
                                          backupPath ? backupPath : [NSNull null], @"previous_release_path",
                                          nil], @"install",
                          nil];
  }
}


- (NSDictionary *)updatePayloadFromSetupPayload:(NSDictionary *)setupPayload
                                          scope:(NSString *)scope
                                           mode:(NSString *)mode
                                      operation:(NSString *)operation
                                        summary:(NSString *)summary
{
  NSMutableDictionary *payload = [[setupPayload mutableCopy] autorelease];
  NSDictionary *updatePlan = [setupPayload objectForKey: @"update_plan"];
  [payload setObject: @"update" forKey: @"command"];
  [payload setObject: scope forKey: @"scope"];
  [payload setObject: mode forKey: @"mode"];
  [payload setObject: operation forKey: @"operation"];
  if (summary != nil)
    {
      [payload setObject: summary forKey: @"summary"];
    }
  if (updatePlan != nil)
    {
      [payload setObject: [NSDictionary dictionaryWithObjectsAndKeys: updatePlan, @"cli", nil] forKey: @"plan"];
    }
  return payload;
}

- (NSDictionary *)buildPackageUpdatePlanForRoot:(NSString *)root
                                      indexPath:(NSString *)indexPath
                                       exitCode:(int *)exitCode
{
  NSString *managedRoot = (root != nil ? root : [self defaultManagedRoot]);
  NSDictionary *state = [self loadInstalledPackagesState: managedRoot];
  NSDictionary *installedPackages = [state objectForKey: @"packages"] ? [state objectForKey: @"packages"] : [NSDictionary dictionary];
  NSDictionary *environment = [self currentEnvironmentForInterface: @"full"];
  NSMutableArray *packageUpdates = [NSMutableArray array];
  NSArray *packageIDs = [[installedPackages allKeys] sortedArrayUsingSelector: @selector(compare:)];
  BOOL anyUpdate = NO;
  NSUInteger i = 0;

  for (i = 0; i < [packageIDs count]; i++)
    {
      NSString *packageID = [packageIDs objectAtIndex: i];
      NSDictionary *installedRecord = [installedPackages objectForKey: packageID];
      NSString *sourceIndex = indexPath;
      NSString *installedVersion = [installedRecord objectForKey: @"version"];
      NSMutableDictionary *entry = [NSMutableDictionary dictionary];
      NSString *errorMessage = nil;
      NSDictionary *packageRecord = nil;
      NSDictionary *artifact = nil;
      NSString *selectionError = nil;
      NSString *requirementsError = nil;
      NSString *availableVersion = nil;
      BOOL updateAvailable = NO;
      BOOL blocked = NO;

      if (sourceIndex == nil || sourceIndex == (id)[NSNull null])
        {
          sourceIndex = [installedRecord objectForKey: @"index_path"];
        }
      if (installedVersion == (id)[NSNull null])
        {
          installedVersion = nil;
        }

      [entry setObject: packageID forKey: @"id"];
      [entry setObject: installedVersion ? installedVersion : (id)[NSNull null] forKey: @"current_version"];
      [entry setObject: sourceIndex ? sourceIndex : (id)[NSNull null] forKey: @"index_path"];

      if (sourceIndex == nil || sourceIndex == (id)[NSNull null] || [sourceIndex length] == 0)
        {
          blocked = YES;
          [entry setObject: @"package_index_missing" forKey: @"blocker"];
          [entry setObject: @"Installed package does not record a package index; pass --index to check updates." forKey: @"message"];
        }
      else
        {
          packageRecord = [self packageRecordFromIndexPath: sourceIndex packageID: packageID error: &errorMessage];
          if (packageRecord == nil)
            {
              blocked = YES;
              [entry setObject: @"package_not_found_in_index" forKey: @"blocker"];
              [entry setObject: errorMessage ? errorMessage : @"Package was not found in the package index." forKey: @"message"];
            }
          else
            {
              availableVersion = [packageRecord objectForKey: @"version"];
              if (availableVersion == (id)[NSNull null])
                {
                  availableVersion = nil;
                }
              if ([self packageRequirements: [packageRecord objectForKey: @"requirements"]
                           matchEnvironment: environment
                                     reason: &requirementsError] == NO)
                {
                  blocked = YES;
                  [entry setObject: @"requirements_not_satisfied" forKey: @"blocker"];
                  [entry setObject: requirementsError ? requirementsError : @"Package requirements are not satisfied by this environment." forKey: @"message"];
                }
              artifact = [self selectedPackageArtifactForPackage: packageRecord environment: environment selectionError: &selectionError];
              if (artifact == nil)
                {
                  blocked = YES;
                  [entry setObject: @"artifact_not_compatible" forKey: @"blocker"];
                  [entry setObject: selectionError ? selectionError : @"No compatible package artifact was found." forKey: @"message"];
                }
              if (availableVersion != nil && installedVersion != nil && [self compareVersionString: availableVersion toVersionString: installedVersion] == NSOrderedDescending)
                {
                  updateAvailable = YES;
                }
              else if (availableVersion != nil && installedVersion == nil)
                {
                  updateAvailable = YES;
                }
              if (blocked)
                {
                  updateAvailable = NO;
                }
              [entry setObject: availableVersion ? availableVersion : (id)[NSNull null] forKey: @"available_version"];
              [entry setObject: artifact ? [artifact objectForKey: @"id"] : (id)[NSNull null] forKey: @"selected_artifact"];
            }
        }

      [entry setObject: [NSNumber numberWithBool: updateAvailable] forKey: @"update_available"];
      [entry setObject: blocked ? @"blocked" : (updateAvailable ? @"upgrade" : @"none") forKey: @"action"];
      if (updateAvailable)
        {
          anyUpdate = YES;
        }
      [packageUpdates addObject: entry];
    }

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"update", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        anyUpdate ? @"Package updates are available." : @"Installed packages are already current.", @"summary",
                        @"packages", @"scope",
                        @"check", @"mode",
                        managedRoot, @"managed_root",
                        [NSNumber numberWithBool: anyUpdate], @"update_available",
                        [NSDictionary dictionaryWithObjectsAndKeys: packageUpdates, @"packages", nil], @"plan",
                        packageUpdates, @"package_updates",
                        nil];
}

- (NSDictionary *)applyPackageUpdatePlan:(NSDictionary *)planPayload
                                    root:(NSString *)root
                                exitCode:(int *)exitCode
{
  NSString *managedRoot = (root != nil ? root : [self defaultManagedRoot]);
  NSArray *updates = [planPayload objectForKey: @"package_updates"] ? [planPayload objectForKey: @"package_updates"] : [[planPayload objectForKey: @"plan"] objectForKey: @"packages"];
  NSMutableArray *results = [NSMutableArray array];
  NSFileManager *manager = [NSFileManager defaultManager];
  NSUInteger i = 0;

  for (i = 0; i < [updates count]; i++)
    {
      NSDictionary *entry = [updates objectAtIndex: i];
      if ([[entry objectForKey: @"update_available"] boolValue] == NO)
        {
          continue;
        }
      {
        NSString *packageID = [entry objectForKey: @"id"];
        NSString *indexPath = [entry objectForKey: @"index_path"];
        NSMutableDictionary *state = [[self loadInstalledPackagesState: managedRoot] mutableCopy];
        NSMutableDictionary *packages = [[[state objectForKey: @"packages"] mutableCopy] autorelease];
        NSDictionary *oldRecord = [packages objectForKey: packageID];
        NSString *oldRoot = [oldRecord objectForKey: @"install_root"];
        NSString *backupRoot = [[[managedRoot stringByAppendingPathComponent: @".transactions/package-update-backups"] stringByAppendingPathComponent: packageID] stringByStandardizingPath];
        GSCommandContext *installContext = nil;
        NSDictionary *installPayload = nil;
        int installExit = 0;

        if (indexPath == nil || indexPath == (id)[NSNull null] || oldRecord == nil)
          {
            [results addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                packageID, @"id",
                                                [NSNumber numberWithBool: NO], @"ok",
                                                @"Package update is missing installed state or package index.", @"summary",
                                                nil]];
            [state release];
            continue;
          }

        [manager createDirectoryAtPath: [backupRoot stringByDeletingLastPathComponent] withIntermediateDirectories: YES attributes: nil error: NULL];
        [manager removeItemAtPath: backupRoot error: NULL];
        if (oldRoot != nil && oldRoot != (id)[NSNull null] && [manager fileExistsAtPath: oldRoot])
          {
            [manager moveItemAtPath: oldRoot toPath: backupRoot error: NULL];
          }
        [packages removeObjectForKey: packageID];
        [state setObject: packages forKey: @"packages"];
        [self saveInstalledPackagesState: state managedRoot: managedRoot];

        installContext = [GSCommandContext contextWithArguments:
                                            [NSArray arrayWithObjects:
                                                       @"install",
                                                       @"--root",
                                                       managedRoot,
                                                       @"--index",
                                                       indexPath,
                                                       packageID,
                                                       nil]];
        installPayload = [self executeInstallForContext: installContext exitCode: &installExit];
        if (installExit != 0 || [[installPayload objectForKey: @"ok"] boolValue] == NO)
          {
            if (oldRoot != nil && oldRoot != (id)[NSNull null])
              {
                [manager removeItemAtPath: oldRoot error: NULL];
              }
            if ([manager fileExistsAtPath: backupRoot])
              {
                [manager moveItemAtPath: backupRoot toPath: oldRoot error: NULL];
              }
            [packages setObject: oldRecord forKey: packageID];
            [state setObject: packages forKey: @"packages"];
            [self saveInstalledPackagesState: state managedRoot: managedRoot];
            [results addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                                packageID, @"id",
                                                [NSNumber numberWithBool: NO], @"ok",
                                                [installPayload objectForKey: @"summary"] ? [installPayload objectForKey: @"summary"] : @"Package update failed and was rolled back.", @"summary",
                                                nil]];
            [state release];
            *exitCode = 1;
            return [NSDictionary dictionaryWithObjectsAndKeys:
                                  [NSNumber numberWithInt: 1], @"schema_version",
                                  @"update", @"command",
                                  [NSNumber numberWithBool: NO], @"ok",
                                  @"error", @"status",
                                  @"Package update failed and was rolled back.", @"summary",
                                  @"packages", @"scope",
                                  @"apply", @"mode",
                                  managedRoot, @"managed_root",
                                  results, @"package_updates",
                                  nil];
          }
        [manager removeItemAtPath: backupRoot error: NULL];
        [results addObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                            packageID, @"id",
                                            [NSNumber numberWithBool: YES], @"ok",
                                            [installPayload objectForKey: @"summary"], @"summary",
                                            [installPayload objectForKey: @"selected_artifact"] ? [installPayload objectForKey: @"selected_artifact"] : (id)[NSNull null], @"selected_artifact",
                                            nil]];
        [state release];
      }
    }

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"update", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        [results count] > 0 ? @"Package updates completed." : @"No package updates were applied.", @"summary",
                        @"packages", @"scope",
                        @"apply", @"mode",
                        managedRoot, @"managed_root",
                        results, @"package_updates",
                        nil];
}

- (NSDictionary *)executeUpdateForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *scope = @"all";
  NSString *manifestPath = nil;
  NSString *installRoot = nil;
  NSString *indexPath = nil;
  BOOL checkMode = NO;
  BOOL yesMode = [context yes];
  NSUInteger i = 0;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"all"] || [argument isEqualToString: @"cli"] || [argument isEqualToString: @"packages"])
        {
          scope = argument;
        }
      else if ([argument isEqualToString: @"--check"])
        {
          checkMode = YES;
        }
      else if ([argument isEqualToString: @"--yes"])
        {
          yesMode = YES;
        }
      else if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"update" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          installRoot = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--manifest"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"update" ok: NO status: @"error" summary: @"--manifest requires a value." data: nil];
            }
          manifestPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--index"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"update" ok: NO status: @"error" summary: @"--index requires a value." data: nil];
            }
          indexPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"update" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown update option: %@", argument] data: nil];
        }
      else
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"update" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown update scope: %@", argument] data: nil];
        }
    }

  if ([scope isEqualToString: @"cli"])
    {
      if (checkMode || yesMode == NO)
        {
          NSDictionary *setupPlan = [self buildUpdatePlanForScope: @"user" manifest: manifestPath installRoot: installRoot exitCode: exitCode];
          return [self updatePayloadFromSetupPayload: setupPlan
                                               scope: @"cli"
                                                mode: checkMode ? @"check" : @"plan"
                                           operation: @"check_cli_updates"
                                             summary: [setupPlan objectForKey: @"summary"]];
        }
      else
        {
          NSMutableArray *setupArguments = [NSMutableArray arrayWithObjects: @"setup", @"--upgrade", nil];
          NSDictionary *setupPayload = nil;
          if (installRoot != nil)
            {
              [setupArguments addObjectsFromArray: [NSArray arrayWithObjects: @"--root", installRoot, nil]];
            }
          if (manifestPath != nil)
            {
              [setupArguments addObjectsFromArray: [NSArray arrayWithObjects: @"--manifest", manifestPath, nil]];
            }
          setupPayload = [self executeSetupForContext: [GSCommandContext contextWithArguments: setupArguments] exitCode: exitCode];
          return [self updatePayloadFromSetupPayload: setupPayload
                                               scope: @"cli"
                                                mode: @"apply"
                                           operation: @"update_cli"
                                             summary: [[setupPayload objectForKey: @"ok"] boolValue] ? @"CLI and toolchain update completed." : [setupPayload objectForKey: @"summary"]];
        }
    }

  if ([scope isEqualToString: @"packages"])
    {
      NSDictionary *packagePlan = [self buildPackageUpdatePlanForRoot: installRoot indexPath: indexPath exitCode: exitCode];
      if (checkMode || yesMode == NO)
        {
          if (checkMode == NO)
            {
              NSMutableDictionary *payload = [[packagePlan mutableCopy] autorelease];
              [payload setObject: @"plan" forKey: @"mode"];
              [payload setObject: @"Package update plan created. Re-run with --yes to apply." forKey: @"summary"];
              return payload;
            }
          return packagePlan;
        }
      return [self applyPackageUpdatePlan: packagePlan root: installRoot exitCode: exitCode];
    }

  {
    int cliExit = 0;
    int packageExit = 0;
    NSDictionary *cliPlanPayload = [self buildUpdatePlanForScope: @"user" manifest: manifestPath installRoot: installRoot exitCode: &cliExit];
    NSDictionary *packagePlanPayload = [self buildPackageUpdatePlanForRoot: installRoot indexPath: indexPath exitCode: &packageExit];
    NSDictionary *cliPlan = [cliPlanPayload objectForKey: @"update_plan"] ? [cliPlanPayload objectForKey: @"update_plan"] : [NSDictionary dictionary];
    NSArray *packagePlan = [packagePlanPayload objectForKey: @"package_updates"] ? [packagePlanPayload objectForKey: @"package_updates"] : [NSArray array];
    BOOL updateAvailable = [[cliPlan objectForKey: @"update_available"] boolValue] || [[packagePlanPayload objectForKey: @"update_available"] boolValue];

    if (checkMode || yesMode == NO)
      {
        *exitCode = (cliExit == 0 && packageExit == 0) ? 0 : (cliExit != 0 ? cliExit : packageExit);
        return [NSDictionary dictionaryWithObjectsAndKeys:
                              [NSNumber numberWithInt: 1], @"schema_version",
                              @"update", @"command",
                              [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                              (*exitCode == 0 ? @"ok" : @"error"), @"status",
                              (yesMode == NO && checkMode == NO) ? @"Update plan created. Re-run with --yes to apply." : (updateAvailable ? @"Updates are available." : @"Everything is already current."), @"summary",
                              @"all", @"scope",
                              checkMode ? @"check" : @"plan", @"mode",
                              [NSDictionary dictionaryWithObjectsAndKeys: cliPlan, @"cli", packagePlan, @"packages", nil], @"plan",
                              [NSNumber numberWithBool: updateAvailable], @"update_available",
                              nil];
      }
    else
      {
        NSDictionary *cliApply = nil;
        NSDictionary *packageApply = nil;
        int applyExit = 0;
        if ([[cliPlan objectForKey: @"update_available"] boolValue])
          {
            NSMutableArray *cliArguments = [NSMutableArray arrayWithObjects: @"update", @"cli", @"--yes", nil];
            if (installRoot != nil)
              {
                [cliArguments addObjectsFromArray: [NSArray arrayWithObjects: @"--root", installRoot, nil]];
              }
            if (manifestPath != nil)
              {
                [cliArguments addObjectsFromArray: [NSArray arrayWithObjects: @"--manifest", manifestPath, nil]];
              }
            cliApply = [self executeUpdateForContext: [GSCommandContext contextWithArguments: cliArguments] exitCode: &applyExit];
            if (applyExit != 0)
              {
                *exitCode = applyExit;
                return cliApply;
              }
          }
        packageApply = [self applyPackageUpdatePlan: packagePlanPayload root: installRoot exitCode: &applyExit];
        *exitCode = applyExit;
        return [NSDictionary dictionaryWithObjectsAndKeys:
                              [NSNumber numberWithInt: 1], @"schema_version",
                              @"update", @"command",
                              [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                              (*exitCode == 0 ? @"ok" : @"error"), @"status",
                              (*exitCode == 0 ? @"All updates completed." : @"One or more updates failed."), @"summary",
                              @"all", @"scope",
                              @"apply", @"mode",
                              cliApply ? cliApply : [NSNull null], @"cli",
                              packageApply ? packageApply : [NSNull null], @"packages",
                              nil];
      }
  }
}

- (NSDictionary *)executeBuildForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *projectPath = [self projectPathFromCommandArguments: arguments];
  NSString *requestedBuildSystem = [self buildSystemFromCommandArguments: arguments];
  NSDictionary *project = [self detectProjectAtPath: projectPath];
  NSString *backend = [project objectForKey: @"build_system"];
  NSArray *buildInvocation = [NSArray arrayWithObjects: @"make", nil];
  NSArray *cleanInvocation = [NSArray arrayWithObjects: @"make", @"distclean", nil];
  NSDictionary *cleanPhase = nil;
  NSDictionary *buildPhase = nil;
  NSMutableArray *phases = nil;
  BOOL cleanFirst = [self arguments: arguments containOption: @"--clean"];
  BOOL streamOutput = ([context jsonOutput] == NO && [context quiet] == NO);

  if ([[project objectForKey: @"supported"] boolValue] == NO)
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"build", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"The current directory is not a supported GNUstep project.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  if (([requestedBuildSystem isEqualToString: @"auto"] == NO)
      && ([requestedBuildSystem isEqualToString: backend] == NO))
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"build", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            [NSString stringWithFormat: @"The requested build system '%@' is not available for this project.", requestedBuildSystem], @"summary",
                            project, @"project",
                            backend, @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  if (cleanFirst)
    {
      phases = [NSMutableArray array];
      cleanPhase = [self projectOperationPhaseWithName: @"clean"
                                               backend: backend
                                            invocation: cleanInvocation
                                               project: project
                                          streamOutput: streamOutput];
      [phases addObject: cleanPhase];
      if ([[cleanPhase objectForKey: @"ok"] boolValue] == NO)
        {
          *exitCode = 1;
          return [NSDictionary dictionaryWithObjectsAndKeys:
                                [NSNumber numberWithInt: 1], @"schema_version",
                                @"build", @"command",
                                [NSNumber numberWithBool: NO], @"ok",
                                @"error", @"status",
                                @"GNUstep project clean failed.", @"summary",
                                project, @"project",
                                backend, @"backend",
                                @"clean_build", @"operation",
                                phases, @"phases",
                                [NSNull null], @"invocation",
                                [cleanPhase objectForKey: @"stdout"], @"stdout",
                                [cleanPhase objectForKey: @"stderr"], @"stderr",
                                [cleanPhase objectForKey: @"exit_status"], @"exit_status",
                                nil];
        }
      buildPhase = [self projectOperationPhaseWithName: @"build"
                                               backend: backend
                                            invocation: buildInvocation
                                               project: project
                                          streamOutput: streamOutput];
      [phases addObject: buildPhase];
      *exitCode = [[buildPhase objectForKey: @"ok"] boolValue] ? 0 : 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"build", @"command",
                            [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                            (*exitCode == 0) ? @"ok" : @"error", @"status",
                            (*exitCode == 0) ? @"GNUstep project clean build completed." : @"GNUstep project build failed.", @"summary",
                            project, @"project",
                            backend, @"backend",
                            @"clean_build", @"operation",
                            phases, @"phases",
                            [NSNull null], @"invocation",
                            [buildPhase objectForKey: @"stdout"], @"stdout",
                            [buildPhase objectForKey: @"stderr"], @"stderr",
                            [buildPhase objectForKey: @"exit_status"], @"exit_status",
                            nil];
    }

  buildPhase = [self projectOperationPhaseWithName: @"build"
                                           backend: backend
                                        invocation: buildInvocation
                                           project: project
                                      streamOutput: streamOutput];
  *exitCode = [[buildPhase objectForKey: @"ok"] boolValue] ? 0 : 1;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"build", @"command",
                        [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                        (*exitCode == 0) ? @"ok" : @"error", @"status",
                        (*exitCode == 0) ? @"GNUstep project build completed." : @"GNUstep project build failed.", @"summary",
                        project, @"project",
                        backend, @"backend",
                        @"build", @"operation",
                        buildInvocation, @"invocation",
                        [buildPhase objectForKey: @"stdout"], @"stdout",
                        [buildPhase objectForKey: @"stderr"], @"stderr",
                        [buildPhase objectForKey: @"exit_status"], @"exit_status",
                        nil];
}

- (NSDictionary *)executeCleanForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *projectPath = [self projectPathFromCommandArguments: arguments];
  NSString *requestedBuildSystem = [self buildSystemFromCommandArguments: arguments];
  NSDictionary *project = [self detectProjectAtPath: projectPath];
  NSString *backend = [project objectForKey: @"build_system"];
  NSArray *invocation = [NSArray arrayWithObjects: @"make", @"distclean", nil];
  NSDictionary *phase = nil;
  BOOL streamOutput = ([context jsonOutput] == NO && [context quiet] == NO);

  if ([[project objectForKey: @"supported"] boolValue] == NO)
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"clean", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"The current directory is not a supported GNUstep project.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  if (([requestedBuildSystem isEqualToString: @"auto"] == NO)
      && ([requestedBuildSystem isEqualToString: backend] == NO))
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"clean", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            [NSString stringWithFormat: @"The requested build system '%@' is not available for this project.", requestedBuildSystem], @"summary",
                            project, @"project",
                            backend, @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  phase = [self projectOperationPhaseWithName: @"clean"
                                      backend: backend
                                   invocation: invocation
                                      project: project
                                 streamOutput: streamOutput];
  *exitCode = [[phase objectForKey: @"ok"] boolValue] ? 0 : 1;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"clean", @"command",
                        [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                        (*exitCode == 0) ? @"ok" : @"error", @"status",
                        (*exitCode == 0) ? @"GNUstep project clean completed." : @"GNUstep project clean failed.", @"summary",
                        project, @"project",
                        backend, @"backend",
                        @"clean", @"operation",
                        invocation, @"invocation",
                        [phase objectForKey: @"stdout"], @"stdout",
                        [phase objectForKey: @"stderr"], @"stderr",
                        [phase objectForKey: @"exit_status"], @"exit_status",
                        nil];
}

- (NSDictionary *)executeRunForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *projectPath = [self projectPathFromCommandArguments: arguments];
  NSDictionary *project = [self detectProjectAtPath: projectPath];
  NSDictionary *runProject = nil;
  NSArray *invocation = nil;
  NSString *backend = nil;
  NSDictionary *result = nil;
  BOOL launchOnly = NO;

  if ([[project objectForKey: @"supported"] boolValue] == NO)
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"The current directory is not a supported GNUstep project.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  runProject = [self runnableProjectForProject: project];
  if (runProject == nil)
    {
      NSArray *candidates = [self runnableProjectsUnderPath: [project objectForKey: @"project_dir"]];
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            ([candidates count] > 1) ? @"Multiple runnable targets were detected. Run from a specific app or tool directory." : @"This GNUstep project can be built, but no runnable target was detected.", @"summary",
                            project, @"project",
                            candidates, @"runnable_targets",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  if ([[runProject objectForKey: @"project_type"] isEqualToString: @"tool"])
    {
      invocation = [NSArray arrayWithObjects: [NSString stringWithFormat: @"./obj/%@", [runProject objectForKey: @"target_name"]], nil];
      backend = @"direct-exec";
    }
  else if ([[runProject objectForKey: @"project_type"] isEqualToString: @"app"])
    {
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
      NSArray *runtimePathEntries = [self projectRuntimePathEntriesUnderPath: [project objectForKey: @"project_dir"]];
      NSString *binaryPath = [[[NSProcessInfo processInfo] arguments] objectAtIndex: 0];
      NSString *resolvedPath = [binaryPath stringByResolvingSymlinksInPath];
      NSString *binDir = [resolvedPath stringByDeletingLastPathComponent];
      NSString *installRoot = [binDir stringByDeletingLastPathComponent];
      NSString *bash = [[installRoot stringByAppendingPathComponent: @"usr"] stringByAppendingPathComponent: @"bin\\bash.exe"];
      NSString *bashCommand = [self windowsOpenAppLaunchCommandForProject: runProject runtimePathEntries: runtimePathEntries];
      NSString *scriptPath = [self writeWindowsOpenAppLaunchScriptForCommand: bashCommand];
      if (scriptPath == nil)
        {
          *exitCode = 1;
          return [NSDictionary dictionaryWithObjectsAndKeys:
                                [NSNumber numberWithInt: 1], @"schema_version",
                                @"run", @"command",
                                [NSNumber numberWithBool: NO], @"ok",
                                @"error", @"status",
                                @"Run launcher failed: could not create a temporary launch script.", @"summary",
                                project, @"project",
                                runProject, @"run_project",
                                @"openapp", @"backend",
                                [NSNull null], @"invocation",
                                @"", @"stdout",
                                @"could not create a temporary launch script", @"stderr",
                                [NSNumber numberWithInt: 1], @"exit_status",
                                nil];
        }
      invocation = [NSArray arrayWithObjects:
                              @"powershell.exe",
                              @"-NoProfile",
                              @"-Command",
                              [self windowsStartBashScriptCommandForBash: bash scriptPath: scriptPath],
                              nil];
      backend = @"openapp";
#else
      invocation = [NSArray arrayWithObjects: @"openapp", [NSString stringWithFormat: @"%@.app", [runProject objectForKey: @"target_name"]], nil];
      backend = @"openapp";
#endif
      launchOnly = YES;
    }
  else
    {
      *exitCode = 3;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"This GNUstep project can be built, but no runnable target was detected.", @"summary",
                            project, @"project",
                            [NSNull null], @"backend",
                            [NSNull null], @"invocation",
                            nil];
    }

  if (launchOnly)
    {
      result = [self runCommand: invocation
               currentDirectory: [runProject objectForKey: @"project_dir"]
                        timeout: 15.0
          additionalPathEntries: [self projectRuntimePathEntriesUnderPath: [project objectForKey: @"project_dir"]]];
    }
  else
    {
      result = [self runCommand: invocation currentDirectory: [runProject objectForKey: @"project_dir"]];
    }
  if ([[result objectForKey: @"launched"] boolValue] == NO)
    {
      NSString *errorSummary = [[result objectForKey: @"stderr"] length] > 0 ?
        [NSString stringWithFormat: @"Run launcher failed: %@", [result objectForKey: @"stderr"]] :
        @"Run launcher failed.";
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"run", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            errorSummary, @"summary",
                            project, @"project",
                            runProject, @"run_project",
                            backend, @"backend",
                            invocation, @"invocation",
                            @"", @"stdout",
                            [result objectForKey: @"stderr"], @"stderr",
                            [NSNumber numberWithInt: 1], @"exit_status",
                            nil];
    }

  *exitCode = [[result objectForKey: @"exit_status"] intValue] == 0 ? 0 : 1;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"run", @"command",
                        [NSNumber numberWithBool: ([[result objectForKey: @"exit_status"] intValue] == 0)], @"ok",
                        ([[result objectForKey: @"exit_status"] intValue] == 0) ? @"ok" : @"error", @"status",
                        launchOnly ? @"Run launched." : (([[result objectForKey: @"exit_status"] intValue] == 0) ? @"Run completed." : @"Run failed."), @"summary",
                        project, @"project",
                        runProject, @"run_project",
                        backend, @"backend",
                        invocation, @"invocation",
                        [result objectForKey: @"stdout"], @"stdout",
                        [result objectForKey: @"stderr"], @"stderr",
                        [result objectForKey: @"exit_status"], @"exit_status",
                        nil];
}

- (NSDictionary *)executeShellForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSUInteger i = 0;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--print-command"])
        {
          continue;
        }
      if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"shell"
                                       ok: NO
                                   status: @"error"
                                  summary: [NSString stringWithFormat: @"Unknown shell option: %@", argument]
                                     data: nil];
        }
      *exitCode = 2;
      return [self payloadWithCommand: @"shell"
                                   ok: NO
                               status: @"error"
                              summary: @"shell does not accept positional arguments yet."
                                 data: nil];
    }

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
  {
    BOOL printCommand = [self arguments: arguments containOption: @"--print-command"];
    NSString *binaryPath = [[[NSProcessInfo processInfo] arguments] objectAtIndex: 0];
    NSString *resolvedPath = [binaryPath stringByResolvingSymlinksInPath];
    NSString *binDir = [resolvedPath stringByDeletingLastPathComponent];
    NSString *installRoot = [binDir stringByDeletingLastPathComponent];
    NSString *bash = [[installRoot stringByAppendingPathComponent: @"usr"] stringByAppendingPathComponent: @"bin\\bash.exe"];
    NSString *bashCommand = @"if [ -r /clang64/share/GNUstep/Makefiles/GNUstep.sh ]; then . /clang64/share/GNUstep/Makefiles/GNUstep.sh; fi; exec bash --noprofile -i";
    NSArray *invocation = [NSArray arrayWithObjects: bash, @"-c", bashCommand, nil];
    NSDictionary *environment = [self managedChildProcessEnvironment];
    NSFileManager *manager = [NSFileManager defaultManager];
    NSString *systemCommand = nil;
    NSEnumerator *environmentKeyEnumerator = nil;
    NSString *environmentKey = nil;
    int shellExit = 0;

    if ([manager fileExistsAtPath: bash] == NO)
      {
        *exitCode = 3;
        return [NSDictionary dictionaryWithObjectsAndKeys:
                              [NSNumber numberWithInt: 1], @"schema_version",
                              @"shell", @"command",
                              [NSNumber numberWithBool: NO], @"ok",
                              @"error", @"status",
                              @"The managed MSYS2 shell was not found. Reinstall or repair the managed GNUstep environment.", @"summary",
                              @"windows", @"platform",
                              installRoot, @"install_root",
                              invocation, @"invocation",
                              nil];
      }

    if (printCommand)
      {
        *exitCode = 0;
        return [NSDictionary dictionaryWithObjectsAndKeys:
                              [NSNumber numberWithInt: 1], @"schema_version",
                              @"shell", @"command",
                              [NSNumber numberWithBool: YES], @"ok",
                              @"ok", @"status",
                              @"Managed MSYS2 CLANG64 shell command prepared.", @"summary",
                              @"windows", @"platform",
                              @"msys2-clang64", @"toolchain_flavor",
                              installRoot, @"install_root",
                              invocation, @"invocation",
                              [environment objectForKey: @"MSYSTEM"] ? [environment objectForKey: @"MSYSTEM"] : @"CLANG64", @"msystem",
                              [environment objectForKey: @"GNUSTEP_MAKEFILES"] ? [environment objectForKey: @"GNUSTEP_MAKEFILES"] : @"", @"gnustep_makefiles",
                              nil];
      }

    environmentKeyEnumerator = [environment keyEnumerator];
    while ((environmentKey = [environmentKeyEnumerator nextObject]) != nil)
      {
        NSString *environmentValue = [environment objectForKey: environmentKey];
        if ([environmentValue isKindOfClass: [NSString class]])
          {
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
            _putenv_s([environmentKey UTF8String], [environmentValue UTF8String]);
#else
            setenv([environmentKey UTF8String], [environmentValue UTF8String], 1);
#endif
          }
      }

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
    systemCommand = [NSString stringWithFormat: @"\"\"%@\" -c \"%@\"\"", bash, bashCommand];
#else
    systemCommand = [NSString stringWithFormat: @"\"%@\" -c \"%@\"", bash, bashCommand];
#endif
    shellExit = system([systemCommand UTF8String]);
    *exitCode = (shellExit == 0) ? 0 : 1;
    return [NSDictionary dictionaryWithObjectsAndKeys:
                          [NSNumber numberWithInt: 1], @"schema_version",
                          @"shell", @"command",
                          [NSNumber numberWithBool: (*exitCode == 0)], @"ok",
                          (*exitCode == 0) ? @"ok" : @"error", @"status",
                          (*exitCode == 0) ? @"Managed MSYS2 CLANG64 shell exited." : @"Managed MSYS2 CLANG64 shell failed.",
                          @"summary",
                          @"windows", @"platform",
                          @"msys2-clang64", @"toolchain_flavor",
                          installRoot, @"install_root",
                          invocation, @"invocation",
                          [NSNumber numberWithInt: shellExit], @"exit_status",
                          @"", @"stderr",
                          nil];
  }
#else
  *exitCode = 3;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"shell", @"command",
                        [NSNumber numberWithBool: NO], @"ok",
                        @"error", @"status",
                        @"gnustep shell is currently only supported on Windows managed MSYS2 CLANG64 installs.", @"summary",
                        @"unsupported", @"platform",
                        nil];
#endif
}

- (NSString *)managedGNUmakefileFlags
{
  return @"GNUSTEP_PREFIX := $(GNUSTEP_MAKEFILES)/../../..\n"
         @"GNUSTEP_LOCAL_LIB_DIR := $(GNUSTEP_PREFIX)/Local/Library/Libraries\n"
         @"GNUSTEP_SYSTEM_LIB_DIR := $(GNUSTEP_PREFIX)/System/Library/Libraries\n"
         @"GNUSTEP_RUNTIME_LIB_DIR := $(GNUSTEP_PREFIX)/lib\n"
         @"ADDITIONAL_OBJCFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include\n"
         @"ADDITIONAL_CPPFLAGS += -I$(GNUSTEP_MAKEFILES)/../../../include\n"
         @"ADDITIONAL_LDFLAGS += -L$(GNUSTEP_MAKEFILES)/../../../lib -L$(GNUSTEP_MAKEFILES)/../../../lib64\n"
         @"ifneq ($(OS),Windows_NT)\n"
         @"ADDITIONAL_LDFLAGS += -Wl,-rpath,$(GNUSTEP_LOCAL_LIB_DIR)\n"
         @"ADDITIONAL_LDFLAGS += -Wl,-rpath,$(GNUSTEP_SYSTEM_LIB_DIR)\n"
         @"ADDITIONAL_LDFLAGS += -Wl,-rpath,$(GNUSTEP_RUNTIME_LIB_DIR)\n"
         @"endif\n"
         @"GNUSTEP_CLI_DISPATCH_LIB := $(firstword $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib/libdispatch.so) $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib64/libdispatch.so) $(wildcard /usr/local/lib/libdispatch.so) $(wildcard /usr/lib/x86_64-linux-gnu/libdispatch.so) $(wildcard /usr/lib/libdispatch.so))\n"
         @"GNUSTEP_CLI_BLOCKS_RUNTIME_LIB := $(firstword $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib/libBlocksRuntime.so) $(wildcard $(GNUSTEP_MAKEFILES)/../../../lib64/libBlocksRuntime.so) $(wildcard /usr/local/lib/libBlocksRuntime.so) $(wildcard /usr/lib/x86_64-linux-gnu/libBlocksRuntime.so) $(wildcard /usr/lib/libBlocksRuntime.so))\n"
         @"ifneq ($(GNUSTEP_CLI_DISPATCH_LIB),)\n"
         @"ADDITIONAL_TOOL_LIBS += -ldispatch\n"
         @"endif\n"
         @"ifneq ($(GNUSTEP_CLI_BLOCKS_RUNTIME_LIB),)\n"
         @"ADDITIONAL_TOOL_LIBS += -lBlocksRuntime\n"
         @"endif\n\n";
}

- (BOOL)writeString:(NSString *)content toPath:(NSString *)path
{
  [[NSFileManager defaultManager] createDirectoryAtPath: [path stringByDeletingLastPathComponent]
                            withIntermediateDirectories: YES
                                             attributes: nil
                                                  error: NULL];
  return [content writeToFile: path atomically: YES encoding: NSUTF8StringEncoding error: NULL];
}

- (NSDictionary *)executeNewForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  BOOL listTemplates = NO;
  NSString *templateName = nil;
  NSString *destination = nil;
  NSString *name = nil;
  NSUInteger i = 0;
  NSFileManager *manager = [NSFileManager defaultManager];
  NSString *destPath = nil;
  NSMutableArray *createdFiles = [NSMutableArray array];

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--list-templates"])
        {
          listTemplates = YES;
        }
      else if ([argument isEqualToString: @"--name"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"new" ok: NO status: @"error" summary: @"--name requires a value." data: nil];
            }
          name = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"new" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown new option: %@", argument] data: nil];
        }
      else if (templateName == nil)
        {
          templateName = argument;
        }
      else if (destination == nil)
        {
          destination = argument;
        }
    }

  if (listTemplates)
    {
      *exitCode = 0;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"new", @"command",
                            [NSNumber numberWithBool: YES], @"ok",
                            @"ok", @"status",
                            [NSArray arrayWithObjects: @"gui-app", @"cli-tool", @"library", nil], @"templates",
                            nil];
    }

  if (templateName == nil || destination == nil)
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"new" ok: NO status: @"error" summary: @"template and destination are required" data: nil];
    }

  destPath = [[destination stringByResolvingSymlinksInPath] length] > 0 ? [destination stringByResolvingSymlinksInPath] : destination;
  if ([manager fileExistsAtPath: destPath] && [[[manager contentsOfDirectoryAtPath: destPath error: NULL] copy] autorelease] != nil &&
      [[manager contentsOfDirectoryAtPath: destPath error: NULL] count] > 0)
    {
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"new", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Destination directory is not empty.", @"summary",
                            templateName, @"template",
                            destPath, @"destination",
                            [NSArray array], @"created_files",
                            nil];
    }

  if (name == nil)
    {
      name = [destPath lastPathComponent];
    }

  if ([templateName isEqualToString: @"cli-tool"])
    {
      [self writeString: [NSString stringWithFormat: @"include $(GNUSTEP_MAKEFILES)/common.make\n\nTOOL_NAME = %@\n%@_OBJC_FILES = main.m\n\n%@include $(GNUSTEP_MAKEFILES)/tool.make\n",
                           name, name, [self managedGNUmakefileFlags]]
              toPath: [destPath stringByAppendingPathComponent: @"GNUmakefile"]];
      [self writeString: @"#import <Foundation/Foundation.h>\n\nint main(void)\n{\n  printf(\"Hello from CLI tool\\n\");\n  return 0;\n}\n"
              toPath: [destPath stringByAppendingPathComponent: @"main.m"]];
      [self writeString: [NSString stringWithFormat: @"{\n  \"schema_version\": 1,\n  \"id\": \"org.example.%@\",\n  \"name\": \"%@\",\n  \"kind\": \"cli-tool\"\n}\n",
                           [name lowercaseString], name]
              toPath: [destPath stringByAppendingPathComponent: @"package.json"]];
      [createdFiles addObject: @"GNUmakefile"];
      [createdFiles addObject: @"main.m"];
      [createdFiles addObject: @"package.json"];
    }
  else if ([templateName isEqualToString: @"gui-app"])
    {
      [self writeString: [NSString stringWithFormat: @"include $(GNUSTEP_MAKEFILES)/common.make\n\nAPP_NAME = %@\n%@_OBJC_FILES = main.m AppController.m\n%@_RESOURCE_FILES = Resources/Info-gnustep.plist\n\n%@include $(GNUSTEP_MAKEFILES)/application.make\n",
                           name, name, name, [self managedGNUmakefileFlags]]
              toPath: [destPath stringByAppendingPathComponent: @"GNUmakefile"]];
      [self writeString: @"#import <AppKit/AppKit.h>\n\nint main(int argc, char **argv)\n{\n  return NSApplicationMain(argc, (const char **)argv);\n}\n"
              toPath: [destPath stringByAppendingPathComponent: @"main.m"]];
      [self writeString: @"#import <AppKit/AppKit.h>\n\n@interface AppController : NSObject\n@end\n\n@implementation AppController\n@end\n"
              toPath: [destPath stringByAppendingPathComponent: @"AppController.m"]];
      [self writeString: @"{\n}\n"
              toPath: [[destPath stringByAppendingPathComponent: @"Resources"] stringByAppendingPathComponent: @"Info-gnustep.plist"]];
      [self writeString: [NSString stringWithFormat: @"{\n  \"schema_version\": 1,\n  \"id\": \"org.example.%@\",\n  \"name\": \"%@\",\n  \"kind\": \"gui-app\"\n}\n",
                           [name lowercaseString], name]
              toPath: [destPath stringByAppendingPathComponent: @"package.json"]];
      [createdFiles addObject: @"GNUmakefile"];
      [createdFiles addObject: @"main.m"];
      [createdFiles addObject: @"AppController.m"];
      [createdFiles addObject: @"Resources/Info-gnustep.plist"];
      [createdFiles addObject: @"package.json"];
    }
  else if ([templateName isEqualToString: @"library"])
    {
      [self writeString: [NSString stringWithFormat: @"include $(GNUSTEP_MAKEFILES)/common.make\n\nLIBRARY_NAME = %@\n%@_OBJC_FILES = %@.m\n%@_HEADER_FILES = %@.h\n\n%@include $(GNUSTEP_MAKEFILES)/library.make\n",
                           name, name, name, name, name, [self managedGNUmakefileFlags]]
              toPath: [destPath stringByAppendingPathComponent: @"GNUmakefile"]];
      [self writeString: [NSString stringWithFormat: @"#import <Foundation/Foundation.h>\n\n@interface %@ : NSObject\n@end\n", name]
              toPath: [destPath stringByAppendingPathComponent: [NSString stringWithFormat: @"%@.h", name]]];
      [self writeString: [NSString stringWithFormat: @"#import \"%@.h\"\n\n@implementation %@\n@end\n", name, name]
              toPath: [destPath stringByAppendingPathComponent: [NSString stringWithFormat: @"%@.m", name]]];
      [self writeString: [NSString stringWithFormat: @"{\n  \"schema_version\": 1,\n  \"id\": \"org.example.%@\",\n  \"name\": \"%@\",\n  \"kind\": \"library\"\n}\n",
                           [name lowercaseString], name]
              toPath: [destPath stringByAppendingPathComponent: @"package.json"]];
      [createdFiles addObject: @"GNUmakefile"];
      [createdFiles addObject: [NSString stringWithFormat: @"%@.h", name]];
      [createdFiles addObject: [NSString stringWithFormat: @"%@.m", name]];
      [createdFiles addObject: @"package.json"];
    }
  else
    {
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"new", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            [NSString stringWithFormat: @"Unknown template: %@", templateName], @"summary",
                            templateName, @"template",
                            destPath, @"destination",
                            [NSArray array], @"created_files",
                            nil];
    }

  [self appendInstallTrace: @"install complete"];
  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"new", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Project template created.", @"summary",
                        templateName, @"template",
                        destPath, @"destination",
                        name, @"name",
                        createdFiles, @"created_files",
                        nil];
}

- (NSDictionary *)loadInstalledPackagesState:(NSString *)managedRoot
{
  NSString *statePath = [[managedRoot stringByAppendingPathComponent: @"state"] stringByAppendingPathComponent: @"installed-packages.json"];
  NSDictionary *state = [self readJSONFile: statePath error: NULL];
  if (state == nil)
    {
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            [NSDictionary dictionary], @"packages",
                            nil];
    }
  return state;
}

- (BOOL)saveInstalledPackagesState:(NSDictionary *)state managedRoot:(NSString *)managedRoot
{
  NSString *stateDir = [managedRoot stringByAppendingPathComponent: @"state"];
  NSString *statePath = [stateDir stringByAppendingPathComponent: @"installed-packages.json"];
  [[NSFileManager defaultManager] createDirectoryAtPath: stateDir withIntermediateDirectories: YES attributes: nil error: NULL];
  return [self writeJSONStringObject: state toPath: statePath error: NULL];
}

- (NSString *)resolvedArtifactPathFromURLString:(NSString *)urlString
{
  if (urlString == nil || [urlString length] == 0)
    {
      return nil;
    }
  if ([urlString hasPrefix: @"file://"])
    {
      NSURL *url = [NSURL URLWithString: urlString];
      NSString *path = [url path];
      if (path == nil || [path length] == 0)
        {
          path = [urlString substringFromIndex: 7];
        }
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
      if ([path length] >= 3 && [path characterAtIndex: 0] == '/' &&
          [[NSCharacterSet letterCharacterSet] characterIsMember: [path characterAtIndex: 1]] &&
          [path characterAtIndex: 2] == ':')
        {
          path = [path substringFromIndex: 1];
        }
      path = [path stringByReplacingOccurrencesOfString: @"/" withString: @"\\"];
#endif
      return [path stringByResolvingSymlinksInPath];
    }
  return [urlString stringByResolvingSymlinksInPath];
}

- (NSDictionary *)executeInstallForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *root = [self defaultManagedRoot];
  NSString *manifestPath = nil;
  NSString *indexPath = nil;
  NSString *packageSpecifier = nil;
  NSUInteger i = 0;
  NSDictionary *packageRecord = nil;
  NSMutableDictionary *state = nil;
  NSString *packageID = nil;
  NSDictionary *artifact = nil;
  NSString *artifactPath = nil;
  NSString *downloadPath = nil;
  NSString *staging = nil;
  NSString *extractRoot = nil;
  NSString *finalRoot = nil;
  NSString *selectionError = nil;
  NSString *requirementsError = nil;
  NSString *downloadError = nil;
  NSString *extractError = nil;
  NSFileManager *manager = [NSFileManager defaultManager];
  NSMutableArray *installedFiles = [NSMutableArray array];
  NSArray *dependencies = [NSArray array];
  NSArray *conflicts = [NSArray array];
  NSDictionary *environment = nil;
  NSDictionary *packages = nil;

  @try
    {
      [self appendInstallTrace: @"enter install"];
      for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          root = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument isEqualToString: @"--index"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"--index requires a value." data: nil];
            }
          indexPath = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown install option: %@", argument] data: nil];
        }
      else
        {
          packageSpecifier = argument;
        }
    }

  [self appendInstallTrace: @"parsed arguments"];

  if (packageSpecifier == nil)
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"A package ID or package manifest path is required." data: nil];
    }

  [self appendInstallTrace: @"loading package record"];
  if (indexPath != nil)
    {
      packageRecord = [self packageRecordFromIndexPath: indexPath packageID: packageSpecifier error: &selectionError];
      if (packageRecord == nil)
        {
          *exitCode = 1;
          return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: selectionError data: nil];
        }
    }
  else
    {
      manifestPath = packageSpecifier;
      packageRecord = [self readJSONFile: manifestPath error: NULL];
    }

  if (packageRecord == nil)
    {
      *exitCode = 1;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: @"Package manifest not found." data: nil];
    }

  [self appendInstallTrace: @"loading install state"];
  state = [[self loadInstalledPackagesState: root] mutableCopy];
  packageID = [packageRecord objectForKey: @"id"];
  [self appendInstallTrace: [NSString stringWithFormat: @"package id %@", packageID]];
  if ([[state objectForKey: @"packages"] objectForKey: packageID] != nil)
    {
      NSDictionary *existingRecord = [[state objectForKey: @"packages"] objectForKey: packageID];
      *exitCode = 0;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"install", @"command",
                            [NSNumber numberWithBool: YES], @"ok",
                            @"ok", @"status",
                            @"Package is already installed.", @"summary",
                            packageID, @"package_id",
                            root, @"managed_root",
                            [existingRecord objectForKey: @"install_root"], @"install_root",
                            [existingRecord objectForKey: @"selected_artifact"] ? [existingRecord objectForKey: @"selected_artifact"] : [NSNull null], @"selected_artifact",
                            [existingRecord objectForKey: @"version"] ? [existingRecord objectForKey: @"version"] : [NSNull null], @"version",
                            [existingRecord objectForKey: @"dependencies"] ? [existingRecord objectForKey: @"dependencies"] : [NSArray array], @"dependencies",
                            [existingRecord objectForKey: @"installed_files"], @"installed_files",
                            nil];
    }

  [self appendInstallTrace: @"detecting environment"];
  environment = [self currentEnvironmentForInterface: @"full"];
  [self appendInstallTrace: @"checking package requirements"];
  if ([self packageRequirements: [packageRecord objectForKey: @"requirements"]
               matchEnvironment: environment
                         reason: &requirementsError] == NO)
    {
      [state release];
      *exitCode = 4;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: requirementsError data: nil];
    }

  [self appendInstallTrace: @"checking dependencies"];
  packages = [state objectForKey: @"packages"];
  dependencies = [packageRecord objectForKey: @"dependencies"] ? [packageRecord objectForKey: @"dependencies"] : [NSArray array];
  for (i = 0; i < [dependencies count]; i++)
    {
      id entry = [dependencies objectAtIndex: i];
      NSString *dependencyID = [entry isKindOfClass: [NSDictionary class]] ? [entry objectForKey: @"id"] : entry;
      if (dependencyID != nil && [packages objectForKey: dependencyID] == nil)
        {
          [state release];
          *exitCode = 1;
          return [self payloadWithCommand: @"install"
                                       ok: NO
                                   status: @"error"
                                  summary: [NSString stringWithFormat: @"Package dependency '%@' is not installed.", dependencyID]
                                     data: nil];
        }
    }

  [self appendInstallTrace: @"checking conflicts"];
  conflicts = [packageRecord objectForKey: @"conflicts"] ? [packageRecord objectForKey: @"conflicts"] : [NSArray array];
  for (i = 0; i < [conflicts count]; i++)
    {
      id entry = [conflicts objectAtIndex: i];
      NSString *conflictID = [entry isKindOfClass: [NSDictionary class]] ? [entry objectForKey: @"id"] : entry;
      if (conflictID != nil && [packages objectForKey: conflictID] != nil)
        {
          [state release];
          *exitCode = 1;
          return [self payloadWithCommand: @"install"
                                       ok: NO
                                   status: @"error"
                                  summary: [NSString stringWithFormat: @"Package conflicts with installed package '%@'.", conflictID]
                                     data: [NSDictionary dictionaryWithObjectsAndKeys: packageID, @"package_id", conflictID, @"conflict", nil]];
        }
    }
  {
    NSArray *installedIDs = [packages allKeys];
    NSUInteger conflictIndex = 0;
    for (conflictIndex = 0; conflictIndex < [installedIDs count]; conflictIndex++)
      {
        NSString *installedID = [installedIDs objectAtIndex: conflictIndex];
        NSDictionary *installedRecord = [packages objectForKey: installedID];
        NSArray *installedConflicts = [installedRecord objectForKey: @"conflicts"] ? [installedRecord objectForKey: @"conflicts"] : [NSArray array];
        NSUInteger installedConflictIndex = 0;
        for (installedConflictIndex = 0; installedConflictIndex < [installedConflicts count]; installedConflictIndex++)
          {
            id entry = [installedConflicts objectAtIndex: installedConflictIndex];
            NSString *conflictID = [entry isKindOfClass: [NSDictionary class]] ? [entry objectForKey: @"id"] : entry;
            if ([conflictID isEqualToString: packageID])
              {
                [state release];
                *exitCode = 1;
                return [self payloadWithCommand: @"install"
                                             ok: NO
                                         status: @"error"
                                        summary: [NSString stringWithFormat: @"Installed package '%@' conflicts with this package.", installedID]
                                           data: [NSDictionary dictionaryWithObjectsAndKeys: packageID, @"package_id", installedID, @"conflict", nil]];
              }
          }
      }
  }

  [self appendInstallTrace: @"selecting artifact"];
  artifact = [self selectedPackageArtifactForPackage: packageRecord environment: environment selectionError: &selectionError];
  if (artifact != nil)
    {
      [self appendInstallTrace: [NSString stringWithFormat: @"selected artifact %@", [artifact objectForKey: @"id"]]];
    }
  if (artifact == nil)
    {
      [state release];
      *exitCode = 4;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: selectionError data: nil];
    }
  if ([artifact objectForKey: @"url"] == nil)
    {
      [state release];
      *exitCode = 1;
      return [self payloadWithCommand: @"install"
                                   ok: NO
                               status: @"error"
                              summary: @"Selected package artifact does not provide an installable URL."
                                 data: nil];
    }

  [self appendInstallTrace: @"resolving artifact path"];
  artifactPath = [self resolvedArtifactPathFromURLString: [artifact objectForKey: @"url"]];
  [self appendInstallTrace: [NSString stringWithFormat: @"artifact path %@", artifactPath]];
  if (artifactPath == nil || [artifactPath length] == 0)
    {
      [state release];
      *exitCode = 1;
      return [self payloadWithCommand: @"install"
                                   ok: NO
                               status: @"error"
                              summary: @"Selected package artifact URL could not be resolved to a local path."
                                 data: nil];
    }
  staging = [[[root stringByExpandingTildeInPath] stringByAppendingPathComponent: @".staging"] stringByAppendingPathComponent: packageID];
  downloadPath = [staging stringByAppendingPathComponent: [artifactPath lastPathComponent]];
  [self appendInstallTrace: [NSString stringWithFormat: @"download path %@", downloadPath]];
  extractRoot = [staging stringByAppendingPathComponent: @"payload"];
  finalRoot = [[[[root stringByExpandingTildeInPath] stringByAppendingPathComponent: @"packages"] stringByAppendingPathComponent: packageID] stringByResolvingSymlinksInPath];
  [self appendInstallTrace: @"preparing staging"];
  [manager removeItemAtPath: staging error: NULL];
  [manager createDirectoryAtPath: staging withIntermediateDirectories: YES attributes: nil error: NULL];

  [self appendInstallTrace: @"fetching artifact"];
  if ([manager fileExistsAtPath: artifactPath])
    {
      NSError *copyError = nil;
      if ([manager copyItemAtPath: artifactPath toPath: downloadPath error: &copyError] == NO)
        {
          [manager removeItemAtPath: staging error: NULL];
          [state release];
          *exitCode = 1;
          return [self payloadWithCommand: @"install"
                                       ok: NO
                                   status: @"error"
                                  summary: [NSString stringWithFormat: @"failed to stage package artifact: %@", [copyError localizedDescription]]
                                     data: nil];
        }
    }
  else if ([self downloadURLString: [artifact objectForKey: @"url"] toPath: downloadPath error: &downloadError] == NO)
    {
      [manager removeItemAtPath: staging error: NULL];
      [state release];
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"install", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            downloadError ? downloadError : @"Artifact not found.", @"summary",
                            packageID, @"package_id",
                            nil];
    }

  [self appendInstallTrace: @"verifying artifact"];
  if ([artifact objectForKey: @"sha256"] != nil)
    {
      NSString *actualSHA = [self sha256ForFile: downloadPath];
      [self appendInstallTrace: [NSString stringWithFormat: @"actual sha %@ expected %@", actualSHA, [artifact objectForKey: @"sha256"]]];
      if (actualSHA == nil || [actualSHA isEqualToString: [artifact objectForKey: @"sha256"]] == NO)
        {
          [manager removeItemAtPath: staging error: NULL];
          [state release];
          *exitCode = 1;
          return [self payloadWithCommand: @"install"
                                       ok: NO
                                   status: @"error"
                                  summary: [NSString stringWithFormat: @"checksum mismatch for %@", [artifact objectForKey: @"id"]]
                                     data: nil];
        }
    }

  [self appendInstallTrace: @"extracting artifact"];
  if ([self extractArchive: downloadPath toDirectory: extractRoot error: &extractError] == NO)
    {
      [manager removeItemAtPath: staging error: NULL];
      [state release];
      *exitCode = 1;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: extractError data: nil];
    }
  [self appendInstallTrace: @"copying payload"];
  [manager removeItemAtPath: finalRoot error: NULL];
  [manager createDirectoryAtPath: [finalRoot stringByDeletingLastPathComponent] withIntermediateDirectories: YES attributes: nil error: NULL];
  if ([self copyTreeContentsFrom: [self singleChildDirectoryOrSelf: extractRoot] to: finalRoot error: &extractError] == NO)
    {
      [manager removeItemAtPath: staging error: NULL];
      [state release];
      *exitCode = 1;
      return [self payloadWithCommand: @"install" ok: NO status: @"error" summary: extractError data: nil];
    }

  [self appendInstallTrace: @"recording installed files"];
  {
    NSDirectoryEnumerator *enumerator = [manager enumeratorAtPath: finalRoot];
    NSString *relative = nil;
    while ((relative = [enumerator nextObject]) != nil)
      {
        NSString *fullPath = [finalRoot stringByAppendingPathComponent: relative];
        BOOL isDir = NO;
        [manager fileExistsAtPath: fullPath isDirectory: &isDir];
        if (!isDir)
          {
            [installedFiles addObject: [[[@"packages" stringByAppendingPathComponent: packageID] stringByAppendingPathComponent: relative] stringByStandardizingPath]];
          }
      }

    NSMutableDictionary *packages = [[[state objectForKey: @"packages"] mutableCopy] autorelease];
    [packages setObject: [NSDictionary dictionaryWithObjectsAndKeys:
                                         manifestPath ? [manifestPath stringByResolvingSymlinksInPath] : [NSNull null], @"manifest_path",
                                         indexPath ? [indexPath stringByResolvingSymlinksInPath] : [NSNull null], @"index_path",
                                         finalRoot, @"install_root",
                                         [packageRecord objectForKey: @"version"] ? [packageRecord objectForKey: @"version"] : [NSNull null], @"version",
                                         [artifact objectForKey: @"id"], @"selected_artifact",
                                         dependencies, @"dependencies",
                                         conflicts, @"conflicts",
                                         installedFiles, @"installed_files",
                                         nil]
                 forKey: packageID];
    [state setObject: packages forKey: @"packages"];
    if (indexPath != nil)
      {
        NSDictionary *packageIndex = [self readJSONFile: indexPath error: NULL];
        if ([packageIndex isKindOfClass: [NSDictionary class]])
          {
            [state setObject: [indexPath stringByResolvingSymlinksInPath] forKey: @"last_package_index_path"];
            [state setObject: [packageIndex objectForKey: @"metadata_version"] ? [packageIndex objectForKey: @"metadata_version"] : [NSNull null] forKey: @"last_package_index_metadata_version"];
            [state setObject: [packageIndex objectForKey: @"generated_at"] ? [packageIndex objectForKey: @"generated_at"] : [NSNull null] forKey: @"last_package_index_generated_at"];
            [state setObject: [packageIndex objectForKey: @"expires_at"] ? [packageIndex objectForKey: @"expires_at"] : [NSNull null] forKey: @"last_package_index_expires_at"];
          }
      }
  }
  [self appendInstallTrace: @"saving install state"];
  [manager removeItemAtPath: staging error: NULL];
  [self saveInstalledPackagesState: state managedRoot: root];
  [state release];

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"install", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Package installed.", @"summary",
                        packageID, @"package_id",
                        root, @"managed_root",
                        finalRoot, @"install_root",
                        manifestPath ? [manifestPath stringByResolvingSymlinksInPath] : [NSNull null], @"manifest_path",
                        indexPath ? [indexPath stringByResolvingSymlinksInPath] : [NSNull null], @"index_path",
                        [packageRecord objectForKey: @"version"] ? [packageRecord objectForKey: @"version"] : [NSNull null], @"version",
                        [artifact objectForKey: @"id"], @"selected_artifact",
                        dependencies, @"dependencies",
                        conflicts, @"conflicts",
                        installedFiles, @"installed_files",
                        nil];
    }
  @catch (NSException *exception)
    {
      [manager removeItemAtPath: staging error: NULL];
      [state release];
      *exitCode = 5;
      return [self payloadWithCommand: @"install"
                                   ok: NO
                               status: @"error"
                              summary: [NSString stringWithFormat: @"Internal install error: %@", [exception reason]]
                                 data: nil];
    }
}

- (NSDictionary *)executeRemoveForContext:(GSCommandContext *)context exitCode:(int *)exitCode
{
  NSArray *arguments = [context commandArguments];
  NSString *root = [self defaultManagedRoot];
  NSString *packageID = nil;
  NSUInteger i = 0;
  NSMutableDictionary *state = nil;
  NSMutableDictionary *packages = nil;
  NSDictionary *record = nil;
  NSMutableArray *dependents = [NSMutableArray array];
  NSEnumerator *packageEnumerator = nil;
  NSString *installedID = nil;

  for (i = 0; i < [arguments count]; i++)
    {
      NSString *argument = [arguments objectAtIndex: i];
      if ([argument isEqualToString: @"--root"])
        {
          if (i + 1 >= [arguments count])
            {
              *exitCode = 2;
              return [self payloadWithCommand: @"remove" ok: NO status: @"error" summary: @"--root requires a value." data: nil];
            }
          root = [arguments objectAtIndex: i + 1];
          i++;
        }
      else if ([argument hasPrefix: @"--"])
        {
          *exitCode = 2;
          return [self payloadWithCommand: @"remove" ok: NO status: @"error" summary: [NSString stringWithFormat: @"Unknown remove option: %@", argument] data: nil];
        }
      else
        {
          packageID = argument;
        }
    }

  [self appendInstallTrace: @"remove parsed arguments"];

  if (packageID == nil)
    {
      *exitCode = 2;
      return [self payloadWithCommand: @"remove" ok: NO status: @"error" summary: @"package_id is required." data: nil];
    }

  [self appendInstallTrace: @"remove loading state"];
  state = [[self loadInstalledPackagesState: root] mutableCopy];
  packages = [[[state objectForKey: @"packages"] mutableCopy] autorelease];
  record = [packages objectForKey: packageID];
  [self appendInstallTrace: @"remove loaded package record"];
  if (record == nil)
    {
      [state release];
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"remove", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Package is not installed.", @"summary",
                            packageID, @"package_id",
                            root, @"managed_root",
                            nil];
    }

  [self appendInstallTrace: @"remove scanning dependents"];
  packageEnumerator = [packages keyEnumerator];
  while ((installedID = [packageEnumerator nextObject]) != nil)
    {
      NSDictionary *installedRecord = [packages objectForKey: installedID];
      NSArray *dependencies = [installedRecord objectForKey: @"dependencies"];
      NSUInteger j = 0;
      if ([installedID isEqualToString: packageID])
        {
          continue;
        }
      for (j = 0; j < [dependencies count]; j++)
        {
          id dependencyEntry = [dependencies objectAtIndex: j];
          NSString *dependencyID = [dependencyEntry isKindOfClass: [NSDictionary class]] ? [dependencyEntry objectForKey: @"id"] : dependencyEntry;
          if ([dependencyID isEqualToString: packageID])
            {
              [dependents addObject: installedID];
              break;
            }
        }
    }
  if ([dependents count] > 0)
    {
      [state release];
      *exitCode = 1;
      return [NSDictionary dictionaryWithObjectsAndKeys:
                            [NSNumber numberWithInt: 1], @"schema_version",
                            @"remove", @"command",
                            [NSNumber numberWithBool: NO], @"ok",
                            @"error", @"status",
                            @"Package is required by installed dependencies.", @"summary",
                            packageID, @"package_id",
                            root, @"managed_root",
                            dependents, @"dependents",
                            nil];
    }

  {
    NSArray *removedFiles = [record objectForKey: @"installed_files"] ? [record objectForKey: @"installed_files"] : [NSArray array];
    NSString *installRoot = [record objectForKey: @"install_root"];
  [self appendInstallTrace: @"remove deleting install root"];
  [[NSFileManager defaultManager] removeItemAtPath: [record objectForKey: @"install_root"] error: NULL];
  [self appendInstallTrace: @"remove deleted install root"];
  [packages removeObjectForKey: packageID];
  [state setObject: packages forKey: @"packages"];
  [self appendInstallTrace: @"remove saving state"];
  [self saveInstalledPackagesState: state managedRoot: root];
  [self appendInstallTrace: @"remove saved state"];
  [state release];

  *exitCode = 0;
  return [NSDictionary dictionaryWithObjectsAndKeys:
                        [NSNumber numberWithInt: 1], @"schema_version",
                        @"remove", @"command",
                        [NSNumber numberWithBool: YES], @"ok",
                        @"ok", @"status",
                        @"Package removed.", @"summary",
                        packageID, @"package_id",
                        root, @"managed_root",
                        installRoot ? installRoot : [NSNull null], @"removed_install_root",
                        removedFiles, @"removed_files",
                        nil];
  }
}

- (NSString *)renderHumanForPayload:(NSDictionary *)payload
{
  NSString *command = [payload objectForKey: @"command"];
  if ([command isEqualToString: @"doctor"])
    {
      NSDictionary *environment = [payload objectForKey: @"environment"];
      NSDictionary *toolchain = [environment objectForKey: @"toolchain"];
      NSMutableArray *lines = [NSMutableArray array];
      [lines addObject: [NSString stringWithFormat: @"doctor: %@", [payload objectForKey: @"summary"]]];
      [lines addObject: [NSString stringWithFormat: @"doctor: status=%@ classification=%@", [payload objectForKey: @"status"], [payload objectForKey: @"environment_classification"]]];
      [lines addObject: [NSString stringWithFormat: @"doctor: interface=%@ depth=%@", [payload objectForKey: @"interface"], [payload objectForKey: @"diagnostic_depth"]]];
      if ([[payload objectForKey: @"diagnostic_depth"] isEqualToString: @"quick"])
        {
          [lines addObject: @"doctor: lightweight mode skipped active compiler validation; run `gnustep doctor --full` for compile/link/run probes."];
        }
      [lines addObject: [NSString stringWithFormat: @"doctor: host=%@/%@", [environment objectForKey: @"os"], [environment objectForKey: @"arch"]]];
      if ([[toolchain objectForKey: @"present"] boolValue])
        {
          [lines addObject: [NSString stringWithFormat: @"doctor: toolchain=%@ runtime=%@ abi=%@",
                              [toolchain objectForKey: @"compiler_family"],
                              [toolchain objectForKey: @"objc_runtime"],
                              [toolchain objectForKey: @"objc_abi"]]];
        }
      else
        {
          [lines addObject: @"doctor: toolchain=not detected"];
        }
      {
        NSUInteger i = 0;
        NSArray *actions = [payload objectForKey: @"actions"];
        for (i = 0; i < [actions count]; i++)
          {
            [lines addObject: [NSString stringWithFormat: @"next: %@", [[actions objectAtIndex: i] objectForKey: @"message"]]];
          }
      }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"setup"])
    {
      NSDictionary *plan = [payload objectForKey: @"plan"];
      NSMutableArray *lines = [NSMutableArray array];
      [lines addObject: [NSString stringWithFormat: @"setup: %@", [payload objectForKey: @"summary"]]];
      [lines addObject: [NSString stringWithFormat: @"setup: scope=%@ root=%@", [plan objectForKey: @"scope"], [plan objectForKey: @"install_root"]]];
      [lines addObject: [NSString stringWithFormat: @"setup: selected release=%@", [plan objectForKey: @"selected_release"]]];
      if ([payload objectForKey: @"install"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"setup: path hint=%@", [[payload objectForKey: @"install"] objectForKey: @"path_hint"]]];
        }
      {
        NSUInteger i = 0;
        NSArray *actions = [payload objectForKey: @"actions"];
        for (i = 0; i < [actions count]; i++)
          {
            [lines addObject: [NSString stringWithFormat: @"next: %@", [[actions objectAtIndex: i] objectForKey: @"message"]]];
          }
      }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"build"])
    {
      NSMutableArray *lines = [NSMutableArray array];
      NSArray *phases = [payload objectForKey: @"phases"];
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [payload objectForKey: @"backend"] == [NSNull null])
        {
          return [payload objectForKey: @"summary"];
        }
      [lines addObject: [NSString stringWithFormat: @"build: %@", [payload objectForKey: @"summary"]]];
      [lines addObject: [NSString stringWithFormat: @"build: backend=%@", [payload objectForKey: @"backend"]]];
      [lines addObject: [NSString stringWithFormat: @"build: project_type=%@ target=%@",
                                  [[payload objectForKey: @"project"] objectForKey: @"project_type"],
                                  [[payload objectForKey: @"project"] objectForKey: @"target_name"]]];
      if ([payload objectForKey: @"operation"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"build: operation=%@", [payload objectForKey: @"operation"]]];
        }
      if (phases != nil && [phases count] > 0)
        {
          NSUInteger i = 0;
          for (i = 0; i < [phases count]; i++)
            {
              NSDictionary *phase = [phases objectAtIndex: i];
              [lines addObject: [NSString stringWithFormat: @"build: phase=%@ invocation=%@ exit_status=%@",
                                          [phase objectForKey: @"name"],
                                          [[phase objectForKey: @"invocation"] componentsJoinedByString: @" "],
                                          [phase objectForKey: @"exit_status"]]];
            }
        }
      else
        {
          [lines addObject: [NSString stringWithFormat: @"build: invocation=%@",
                                      [[payload objectForKey: @"invocation"] componentsJoinedByString: @" "]]];
        }
      if ([[payload objectForKey: @"ok"] boolValue] == NO)
        {
          [lines addObject: [NSString stringWithFormat: @"build: exit_status=%@", [payload objectForKey: @"exit_status"]]];
          if ([[payload objectForKey: @"stderr"] length] > 0)
            {
              [lines addObject: [NSString stringWithFormat: @"build: stderr=%@", [payload objectForKey: @"stderr"]]];
            }
          if ([[payload objectForKey: @"stdout"] length] > 0)
            {
              [lines addObject: [NSString stringWithFormat: @"build: stdout=%@", [payload objectForKey: @"stdout"]]];
            }
        }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"clean"])
    {
      NSMutableArray *lines = [NSMutableArray array];
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [payload objectForKey: @"backend"] == [NSNull null])
        {
          return [payload objectForKey: @"summary"];
        }
      [lines addObject: [NSString stringWithFormat: @"clean: %@", [payload objectForKey: @"summary"]]];
      [lines addObject: [NSString stringWithFormat: @"clean: backend=%@", [payload objectForKey: @"backend"]]];
      [lines addObject: [NSString stringWithFormat: @"clean: project_type=%@ target=%@",
                                  [[payload objectForKey: @"project"] objectForKey: @"project_type"],
                                  [[payload objectForKey: @"project"] objectForKey: @"target_name"]]];
      if ([payload objectForKey: @"operation"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"clean: operation=%@", [payload objectForKey: @"operation"]]];
        }
      [lines addObject: [NSString stringWithFormat: @"clean: invocation=%@",
                                  [[payload objectForKey: @"invocation"] componentsJoinedByString: @" "]]];
      if ([[payload objectForKey: @"ok"] boolValue] == NO)
        {
          [lines addObject: [NSString stringWithFormat: @"clean: exit_status=%@", [payload objectForKey: @"exit_status"]]];
          if ([[payload objectForKey: @"stderr"] length] > 0)
            {
              [lines addObject: [NSString stringWithFormat: @"clean: stderr=%@", [payload objectForKey: @"stderr"]]];
            }
          if ([[payload objectForKey: @"stdout"] length] > 0)
            {
              [lines addObject: [NSString stringWithFormat: @"clean: stdout=%@", [payload objectForKey: @"stdout"]]];
            }
        }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"run"])
    {
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [payload objectForKey: @"backend"] == [NSNull null])
        {
          NSMutableArray *lines = [NSMutableArray array];
          NSArray *targets = [payload objectForKey: @"runnable_targets"];
          NSUInteger i = 0;

          [lines addObject: [payload objectForKey: @"summary"]];
          for (i = 0; i < [targets count]; i++)
            {
              NSDictionary *target = [targets objectAtIndex: i];
              [lines addObject: [NSString stringWithFormat: @"run: target=%@ type=%@ path=%@",
                                          [target objectForKey: @"target_name"],
                                          [target objectForKey: @"project_type"],
                                          [target objectForKey: @"project_dir"]]];
            }
          return [lines componentsJoinedByString: @"\n"];
        }
      NSDictionary *runProject = [payload objectForKey: @"run_project"];
      NSString *invocation = [[payload objectForKey: @"invocation"] componentsJoinedByString: @" "];

      if ([[payload objectForKey: @"backend"] isEqualToString: @"openapp"]
          && [[runProject objectForKey: @"project_type"] isEqualToString: @"app"])
        {
          invocation = [NSString stringWithFormat: @"bash -lc openapp ./%@.app",
                                  [runProject objectForKey: @"target_name"]];
        }

      return [NSString stringWithFormat: @"run: %@\nrun: backend=%@\nrun: project_type=%@ target=%@\nrun: selected_project=%@\nrun: invocation=%@",
                [payload objectForKey: @"summary"],
                [payload objectForKey: @"backend"],
                [runProject objectForKey: @"project_type"],
                [runProject objectForKey: @"target_name"],
                [runProject objectForKey: @"project_dir"],
                invocation];
    }
  if ([command isEqualToString: @"shell"])
    {
      NSMutableArray *lines = [NSMutableArray array];
      [lines addObject: [NSString stringWithFormat: @"shell: %@", [payload objectForKey: @"summary"]]];
      if ([payload objectForKey: @"platform"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: platform=%@", [payload objectForKey: @"platform"]]];
        }
      if ([payload objectForKey: @"toolchain_flavor"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: toolchain=%@", [payload objectForKey: @"toolchain_flavor"]]];
        }
      if ([payload objectForKey: @"install_root"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: root=%@", [payload objectForKey: @"install_root"]]];
        }
      if ([payload objectForKey: @"msystem"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: msystem=%@", [payload objectForKey: @"msystem"]]];
        }
      if ([payload objectForKey: @"gnustep_makefiles"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: makefiles=%@", [payload objectForKey: @"gnustep_makefiles"]]];
        }
      if ([payload objectForKey: @"invocation"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: invocation=%@", [[payload objectForKey: @"invocation"] componentsJoinedByString: @" "]]];
        }
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [[payload objectForKey: @"stderr"] length] > 0)
        {
          [lines addObject: [NSString stringWithFormat: @"shell: stderr=%@", [payload objectForKey: @"stderr"]]];
        }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"new"])
    {
      if ([payload objectForKey: @"templates"] != nil)
        {
          return [[payload objectForKey: @"templates"] componentsJoinedByString: @"\n"];
        }
      return [payload objectForKey: @"summary"];
    }
  if ([command isEqualToString: @"install"])
    {
      NSMutableArray *lines = [NSMutableArray array];
      NSArray *dependencies = [payload objectForKey: @"dependencies"] ? [payload objectForKey: @"dependencies"] : [NSArray array];
      NSArray *installedFiles = [payload objectForKey: @"installed_files"] ? [payload objectForKey: @"installed_files"] : [NSArray array];
      [lines addObject: [NSString stringWithFormat: @"install: %@", [payload objectForKey: @"summary"]]];
      if ([payload objectForKey: @"package_id"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"install: package=%@", [payload objectForKey: @"package_id"]]];
        }
      if ([payload objectForKey: @"selected_artifact"] != nil && [payload objectForKey: @"selected_artifact"] != [NSNull null])
        {
          [lines addObject: [NSString stringWithFormat: @"install: artifact=%@", [payload objectForKey: @"selected_artifact"]]];
        }
      if ([payload objectForKey: @"install_root"] != nil && [payload objectForKey: @"install_root"] != [NSNull null])
        {
          [lines addObject: [NSString stringWithFormat: @"install: root=%@", [payload objectForKey: @"install_root"]]];
        }
      if ([payload objectForKey: @"managed_root"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"install: managed_root=%@", [payload objectForKey: @"managed_root"]]];
        }
      [lines addObject: [NSString stringWithFormat: @"install: dependencies=%lu files=%lu",
                          (unsigned long)[dependencies count],
                          (unsigned long)[installedFiles count]]];
      if ([[payload objectForKey: @"ok"] boolValue] == NO && [payload objectForKey: @"dependents"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"install: blocked_by=%@", [[payload objectForKey: @"dependents"] componentsJoinedByString: @", "]]];
        }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"remove"])
    {
      NSMutableArray *lines = [NSMutableArray array];
      NSArray *dependents = [payload objectForKey: @"dependents"] ? [payload objectForKey: @"dependents"] : [NSArray array];
      NSArray *removedFiles = [payload objectForKey: @"removed_files"] ? [payload objectForKey: @"removed_files"] : [NSArray array];
      [lines addObject: [NSString stringWithFormat: @"remove: %@", [payload objectForKey: @"summary"]]];
      if ([payload objectForKey: @"package_id"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"remove: package=%@", [payload objectForKey: @"package_id"]]];
        }
      if ([payload objectForKey: @"removed_install_root"] != nil && [payload objectForKey: @"removed_install_root"] != [NSNull null])
        {
          [lines addObject: [NSString stringWithFormat: @"remove: root=%@", [payload objectForKey: @"removed_install_root"]]];
        }
      if ([payload objectForKey: @"managed_root"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"remove: managed_root=%@", [payload objectForKey: @"managed_root"]]];
        }
      if ([dependents count] > 0)
        {
          [lines addObject: [NSString stringWithFormat: @"remove: blocked_by=%@", [dependents componentsJoinedByString: @", "]]];
        }
      else if ([[payload objectForKey: @"ok"] boolValue])
        {
          [lines addObject: [NSString stringWithFormat: @"remove: removed_files=%lu", (unsigned long)[removedFiles count]]];
        }
      return [lines componentsJoinedByString: @"\n"];
    }
  if ([command isEqualToString: @"update"])
    {
      NSMutableArray *lines = [NSMutableArray array];
      NSArray *packageUpdates = [payload objectForKey: @"package_updates"];
      NSDictionary *plan = [payload objectForKey: @"plan"];
      [lines addObject: [NSString stringWithFormat: @"update: %@", [payload objectForKey: @"summary"]]];
      if ([payload objectForKey: @"scope"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"update: scope=%@ mode=%@", [payload objectForKey: @"scope"], [payload objectForKey: @"mode"]]];
        }
      if ([payload objectForKey: @"update_available"] != nil)
        {
          [lines addObject: [NSString stringWithFormat: @"update: available=%@", [[payload objectForKey: @"update_available"] boolValue] ? @"yes" : @"no"]];
        }
      if (packageUpdates == nil && [plan isKindOfClass: [NSDictionary class]])
        {
          packageUpdates = [plan objectForKey: @"packages"];
        }
      if ([packageUpdates isKindOfClass: [NSArray class]])
        {
          NSUInteger i = 0;
          for (i = 0; i < [packageUpdates count]; i++)
            {
              NSDictionary *entry = [packageUpdates objectAtIndex: i];
              NSString *packageID = [entry objectForKey: @"id"];
              if (packageID != nil)
                {
                  [lines addObject: [NSString stringWithFormat: @"update: package=%@ action=%@ current=%@ available=%@", packageID, [entry objectForKey: @"action"] ? [entry objectForKey: @"action"] : ([[entry objectForKey: @"ok"] boolValue] ? @"updated" : @"failed"), [entry objectForKey: @"current_version"] ? [entry objectForKey: @"current_version"] : @"unknown", [entry objectForKey: @"available_version"] ? [entry objectForKey: @"available_version"] : @"unknown"]];
                }
            }
        }
      return [lines componentsJoinedByString: @"\n"];
    }
  return [payload objectForKey: @"summary"];
}

- (int)runNativeCommandForContext:(GSCommandContext *)context
{
  NSDictionary *payload = nil;
  int exitCode = 0;
  NSString *command = [context command];

  if ([command isEqualToString: @"doctor"])
    {
      payload = [self executeDoctorForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"setup"])
    {
      payload = [self executeSetupForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"build"])
    {
      payload = [self executeBuildForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"clean"])
    {
      payload = [self executeCleanForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"run"])
    {
      payload = [self executeRunForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"shell"])
    {
      payload = [self executeShellForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"new"])
    {
      payload = [self executeNewForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"install"])
    {
      payload = [self executeInstallForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"remove"])
    {
      payload = [self executeRemoveForContext: context exitCode: &exitCode];
    }
  else if ([command isEqualToString: @"update"])
    {
      payload = [self executeUpdateForContext: context exitCode: &exitCode];
    }
  else
    {
      payload = [self payloadWithCommand: command ok: NO status: @"error" summary: @"Unknown command." data: nil];
      exitCode = 2;
    }

  if ([context jsonOutput])
    {
      [self emitJSONPayload: payload];
    }
  else
    {
      printf("%s\n", [[self renderHumanForPayload: payload] UTF8String]);
    }
  return exitCode;
}

- (int)runWithArguments:(NSArray *)arguments
{
  GSCommandContext *context = [GSCommandContext contextWithArguments: arguments];
  NSString *command = nil;

  if ([context usageError] != nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: @"gnustep"
                                       ok: NO
                                   status: @"error"
                                  summary: [context usageError]
                                     data: nil]];
        }
      else
        {
          fprintf(stderr, "%s\n", [[context usageError] UTF8String]);
        }
      return 2;
    }

  if ([context showVersion] && [context command] == nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload: [self versionPayload]];
        }
      else
        {
          printf("0.1.0-dev\n");
        }
      return 0;
    }

  if ([context showHelp] && [context command] == nil)
    {
      [self printHelp];
      return 0;
    }

  if ([context command] == nil)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: @"gnustep"
                                       ok: NO
                                   status: @"error"
                                  summary: @"No command was provided."
                                     data: nil]];
        }
      else
        {
          [self printHelp];
        }
      return 2;
    }

  command = [context command];
  if ([self isKnownCommand: command] == NO)
    {
      if ([context jsonOutput])
        {
          [self emitJSONPayload:
                  [self payloadWithCommand: command
                                       ok: NO
                                   status: @"error"
                                  summary: @"Unknown command."
                                     data: nil]];
        }
      else
        {
          fprintf(stderr, "%s: unknown command\n", [command UTF8String]);
        }
      return 2;
    }

  if ([context showHelp])
    {
      [self printCommandHelp: command];
      return 0;
    }

  return [self runNativeCommandForContext: context];
}

@end
