#import <Foundation/Foundation.h>

@interface GSCommandRunner : NSObject
{
  // Set when a failed setup could not put the previous installation back.
  NSString *_lastRollbackFailure;
}

- (int)runWithArguments:(NSArray *)arguments;
- (NSArray *)knownCommands;
- (NSDictionary *)executeDoctorForContext:(id)context exitCode:(int *)exitCode;

@end
