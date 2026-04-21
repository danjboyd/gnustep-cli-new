#import <Foundation/Foundation.h>

@interface GSCommandRunner : NSObject

- (int)runWithArguments:(NSArray *)arguments;
- (NSArray *)knownCommands;
- (NSDictionary *)executeDoctorForContext:(id)context exitCode:(int *)exitCode;

@end
