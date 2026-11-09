/* Times Foundation work that runs through gnustep-base's switch-heavy code
   (formatting, parsing, scanning). Used to compare gnustep-base builds that
   differ only in compile flags; each line is "name milliseconds". */
#import <Foundation/Foundation.h>

static double now_ms(void) { return [NSDate timeIntervalSinceReferenceDate] * 1000.0; }

#define BENCH(name, ...) do { double t0 = now_ms(); NSAutoreleasePool *p = [NSAutoreleasePool new]; __VA_ARGS__; [p drain]; \
  printf("%s %.1f\n", name, now_ms() - t0); fflush(stdout); } while (0)

int main(void)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];
  NSMutableArray *items = [NSMutableArray array];
  NSUInteger i, j;
  for (i = 0; i < 2000; i++)
    {
      [items addObject: [NSDictionary dictionaryWithObjectsAndKeys:
        [NSNumber numberWithUnsignedInteger: i], @"id",
        [NSString stringWithFormat: @"item-%lu with some text", (unsigned long)i], @"name",
        [NSNumber numberWithDouble: i * 1.25], @"price",
        [NSArray arrayWithObjects: @"a", @"bb", @"ccc", nil], @"tags", nil]];
    }
  NSData *json = [NSJSONSerialization dataWithJSONObject: items options: 0 error: NULL];
  NSData *xml = [NSPropertyListSerialization dataWithPropertyList: items format: NSPropertyListXMLFormat_v1_0 options: 0 error: NULL];
  NSString *openstep = [items description];
  NSMutableString *numbers = [NSMutableString string];
  for (i = 0; i < 20000; i++) { [numbers appendFormat: @"%lu %f ", (unsigned long)i, i / 3.0]; }

  BENCH("format", for (i = 0; i < 200000; i++) { [NSString stringWithFormat: @"%d %@ %.3f %s %x", (int)i, @"obj", i / 7.0, "cstr", (unsigned)i]; });
  BENCH("json-parse", for (j = 0; j < 40; j++) { [NSJSONSerialization JSONObjectWithData: json options: 0 error: NULL]; });
  BENCH("json-write", for (j = 0; j < 40; j++) { [NSJSONSerialization dataWithJSONObject: items options: 0 error: NULL]; });
  BENCH("plist-xml-parse", for (j = 0; j < 10; j++) { [NSPropertyListSerialization propertyListWithData: xml options: 0 format: NULL error: NULL]; });
  BENCH("plist-openstep-parse", for (j = 0; j < 20; j++) { [openstep propertyList]; });
  BENCH("scanner", for (j = 0; j < 20; j++) { NSScanner *s = [NSScanner scannerWithString: numbers]; int v; double d;
        while (![s isAtEnd]) { [s scanInt: &v]; [s scanDouble: &d]; } });
  BENCH("string-ops", for (j = 0; j < 30; j++) { NSString *l = [openstep lowercaseString];
        [[l componentsSeparatedByString: @";"] count]; [l rangeOfString: @"item-1999"]; [l hash]; });
  BENCH("dictionary", { NSMutableDictionary *d = [NSMutableDictionary dictionary];
        for (i = 0; i < 300000; i++) { [d setObject: @"v" forKey: [NSNumber numberWithUnsignedInteger: i % 50000]]; [d objectForKey: [NSNumber numberWithUnsignedInteger: i % 777]]; } });
  BENCH("base64", for (j = 0; j < 50; j++) { [[NSData alloc] initWithBase64EncodedString: [xml base64EncodedStringWithOptions: 0] options: 0]; });
  [pool drain];
  return 0;
}
