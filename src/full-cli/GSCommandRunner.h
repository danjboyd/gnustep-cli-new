#import <Foundation/Foundation.h>

@interface GSCommandRunner : NSObject
{
  // Release manifests and their signatures fetched by URL in this invocation.
  // Discovery, planning and setup each read the same URL; reusing the first
  // fetch means the bytes whose signature was checked are the bytes planned and
  // applied, even if the remote "latest" moves mid-run. Every reader still
  // verifies and validates; only the download is shared.
  NSMutableDictionary *_releaseMetadataSnapshots;
}

- (int)runWithArguments:(NSArray *)arguments;
- (NSArray *)knownCommands;
- (NSDictionary *)executeDoctorForContext:(id)context exitCode:(int *)exitCode;

@end
